"""
Authentication API routes for user login and session management.

This module implements login-specific OAuth endpoints that are separate from
the integration OAuth endpoints for services like Calendar and Todoist.
"""

import os
import secrets
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from common.oauth_manager import get_google_config, GoogleOAuth, OAuthManager
from service.auth_service import auth_service, AuthenticationError, SessionExpiredError, InvalidSessionError
from service.oauth_service import OAuthService, get_oauth_service

# Request/Response Models
class LoginStartResponse(BaseModel):
    """Response for login start endpoint."""
    authorization_url: str
    state: str
    message: str


class LoginStatusResponse(BaseModel):
    """Response for login status endpoint."""
    authenticated: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    picture_url: Optional[str] = None


class LogoutResponse(BaseModel):
    """Response for logout endpoint."""
    success: bool
    message: str


# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])


def get_login_redirect_url() -> str:
    """Get the login redirect URL from environment or default."""
    return os.getenv("GOOGLE_LOGIN_REDIRECT_URI", "http://localhost:8080/api/auth/login/callback")


def get_streamlit_base_url() -> str:
    """Get the Streamlit base URL for redirects."""
    return os.getenv("STREAMLIT_URL", "http://localhost:8501")


@router.post("/login/start", response_model=LoginStartResponse)
async def start_login_flow() -> LoginStartResponse:
    """
    Start the Google OAuth login flow.
    
    Returns:
        Authorization URL and state for OAuth flow
        
    Raises:
        HTTPException: If Google configuration is missing
    """
    google_config = get_google_config()
    if not google_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured. Please check GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET."
        )
    
    # Override redirect URI for login flow
    login_config = google_config
    login_config.redirect_uri = get_login_redirect_url()
    
    oauth_manager = OAuthManager()
    google_oauth = GoogleOAuth(login_config, oauth_manager)
    
    state = secrets.token_urlsafe(32)
    auth_url, _ = google_oauth.get_authorization_url(state)
    
    return LoginStartResponse(
        authorization_url=auth_url,
        state=state,
        message="Redirect to Google for authentication"
    )


@router.get("/login/callback")
async def login_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for security verification"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    response: Response = None
):
    """
    Handle Google OAuth login callback.
    
    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        error: Error parameter if OAuth failed
        
    Returns:
        Redirect response to Streamlit with session token
    """
    streamlit_url = get_streamlit_base_url()
    
    # Handle OAuth errors
    if error:
        return RedirectResponse(
            url=f"{streamlit_url}?login_error={error}",
            status_code=302
        )
    
    try:
        # Get Google configuration
        google_config = get_google_config()
        if not google_config:
            return RedirectResponse(
                url=f"{streamlit_url}?login_error=Google OAuth not configured",
                status_code=302
            )
        
        # Override redirect URI for login flow
        login_config = google_config
        login_config.redirect_uri = get_login_redirect_url()
        
        # Exchange code for token
        oauth_manager = OAuthManager()
        google_oauth = GoogleOAuth(login_config, oauth_manager)
        
        oauth_token = google_oauth.exchange_code_for_token(code, state)
        if not oauth_token or not oauth_token.user_info:
            return RedirectResponse(
                url=f"{streamlit_url}?login_error=Failed to get user information from Google",
                status_code=302
            )
        
        # Check if this Google account is allowed to log in
        google_user_id = oauth_token.user_info.get("id") or oauth_token.user_info.get("sub")
        primary_account = auth_service.get_primary_login_account()
        
        if primary_account and primary_account.google_user_id != google_user_id:
            # Different Google account than the primary login account
            return RedirectResponse(
                url=f"{streamlit_url}?login_error=Please log in with {primary_account.email}",
                status_code=302
            )
        
        # Create login session
        session_token, user_account = auth_service.create_login_session(oauth_token.user_info)
        
        # Also store the OAuth token for Calendar integration
        # This allows the same login to be used for Calendar access
        from common.oauth_manager import oauth_manager
        oauth_manager.store_token("google", user_account.email, oauth_token)
        
        # Set session cookie and redirect to Streamlit with session token
        # For development: pass token in URL since cross-port cookies are complex
        redirect_response = RedirectResponse(
            url=f"{streamlit_url}?login_success=true&session_token={session_token}",
            status_code=302
        )
        
        # Also set HTTP-only cookie for API access (when ports align in production)
        redirect_response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            secure=os.getenv("ENVIRONMENT") == "production",  # HTTPS in production
            samesite="lax"
        )
        
        return redirect_response
        
    except AuthenticationError as e:
        return RedirectResponse(
            url=f"{streamlit_url}?login_error={str(e)}",
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{streamlit_url}?login_error=Unexpected error during login",
            status_code=302
        )


@router.get("/status", response_model=LoginStatusResponse)
async def get_login_status(request: Request) -> LoginStatusResponse:
    """
    Get current login status from session.
    
    Returns:
        Current authentication status and user info
    """
    session_token = request.cookies.get("session_token")
    
    # Also check for session token in query params (for development/testing)
    if not session_token:
        # This is a fallback for development when cookies might not work
        session_token = request.query_params.get("session_token")
    
    if not session_token:
        return LoginStatusResponse(authenticated=False)
    
    try:
        user_account = auth_service.get_user_from_session(session_token)
        if user_account:
            return LoginStatusResponse(
                authenticated=True,
                user_id=user_account.app_user_id,
                email=user_account.email,
                name=user_account.name,
                picture_url=user_account.picture_url
            )
        else:
            return LoginStatusResponse(authenticated=False)
            
    except (SessionExpiredError, InvalidSessionError):
        return LoginStatusResponse(authenticated=False)


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: Request, response: Response) -> LogoutResponse:
    """
    Logout the current user by invalidating their session.
    
    Returns:
        Logout status
    """
    session_token = request.cookies.get("session_token")
    
    if session_token:
        success = auth_service.logout_user(session_token)
        
        # Clear the session cookie
        response.delete_cookie(key="session_token")
        
        return LogoutResponse(
            success=success,
            message="Successfully logged out" if success else "Session not found"
        )
    else:
        return LogoutResponse(
            success=True,
            message="No active session found"
        )


@router.post("/logout/all", response_model=LogoutResponse)
async def logout_all_sessions(request: Request, response: Response) -> LogoutResponse:
    """
    Logout all sessions for the current user.
    
    Returns:
        Logout status
    """
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return LogoutResponse(
            success=True,
            message="No active session found"
        )
    
    try:
        user_info = auth_service.validate_session_token(session_token)
        success = auth_service.logout_all_user_sessions(user_info["app_user_id"])
        
        # Clear the session cookie
        response.delete_cookie(key="session_token")
        
        return LogoutResponse(
            success=success,
            message="Successfully logged out all sessions"
        )
        
    except (SessionExpiredError, InvalidSessionError):
        response.delete_cookie(key="session_token")
        return LogoutResponse(
            success=True,
            message="Session was already invalid"
        )


@router.get("/user", response_model=LoginStatusResponse)
async def get_current_user(request: Request) -> LoginStatusResponse:
    """
    Get current user information from session.
    Alias for /status endpoint with same functionality.
    
    Returns:
        Current user information if authenticated
    """
    return await get_login_status(request)


# Health check for authentication service
@router.get("/health")
async def auth_health_check() -> Dict[str, Any]:
    """Health check for authentication service."""
    try:
        # Clean up expired sessions as part of health check
        cleaned_count = auth_service.cleanup_expired_sessions()
        
        return {
            "status": "healthy",
            "expired_sessions_cleaned": cleaned_count,
            "auth_service": "active"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }