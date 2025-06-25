"""
OAuth API routes for Todoist and Google Calendar integration.

This module implements the OAuth API endpoints that replace the embedded OAuth
logic removed from the Streamlit frontend in Task 2.8.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import RedirectResponse

from service.oauth_service import (
    get_oauth_service,
    OAuthServiceError,
    OAuthConfigurationError,
    OAuthTokenError,
)
from schema.oauth_models import (
    OAuthStartResponse,
    OAuthStatus,
    OAuthStatusResponse,
    OAuthDisconnectResponse,
    OAuthRefreshResponse,
    CalendarsResponse,
    CalendarPreferencesRequest,
    CalendarPreferencesResponse,
)


# Models are now imported from schema.oauth_models


# Create router
router = APIRouter(prefix="/api/oauth", tags=["oauth"])


@router.post("/todoist/start", response_model=OAuthStartResponse)
async def start_todoist_oauth(user_id: str) -> OAuthStartResponse:
    """
    Initiate Todoist OAuth flow.

    Args:
        user_id: User identifier for OAuth association

    Returns:
        Authorization URL and state for OAuth flow

    Raises:
        HTTPException: If OAuth configuration is missing or invalid
    """
    oauth_service = get_oauth_service()
    try:
        result = oauth_service.start_todoist_oauth(user_id)
        return OAuthStartResponse(
            authorization_url=result["authorization_url"],
            state=result["state"],
            message=result["message"],
        )
    except OAuthConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OAuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/google/start", response_model=OAuthStartResponse)
async def start_google_oauth(user_id: str) -> OAuthStartResponse:
    """
    Initiate Google OAuth flow.

    Args:
        user_id: User identifier for OAuth association

    Returns:
        Authorization URL and state for OAuth flow

    Raises:
        HTTPException: If OAuth configuration is missing or invalid
    """
    oauth_service = get_oauth_service()
    try:
        result = oauth_service.start_google_oauth(user_id)
        return OAuthStartResponse(
            authorization_url=result["authorization_url"],
            state=result["state"],
            message=result["message"],
        )
    except OAuthConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OAuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/callback/{service}")
async def oauth_callback(
    service: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for security verification"),
    user_id: Optional[str] = Query(None, description="Optional user identifier"),
):
    """
    Handle OAuth callbacks for both Todoist and Google services.
    Redirects back to Streamlit with success or error message.

    Args:
        service: Service name ("todoist" or "google")
        code: Authorization code from OAuth provider
        state: State parameter for security verification
        user_id: Optional user identifier

    Returns:
        Redirect response to Streamlit with success/error message

    Raises:
        HTTPException: If service is unsupported or OAuth exchange fails
    """
    if service not in ["todoist", "google"]:
        # Redirect back to Streamlit with error
        return RedirectResponse(
            url=f"http://localhost:8501?oauth_error=Unsupported service: {service}",
            status_code=302,
        )

    oauth_service = get_oauth_service()
    try:
        result = oauth_service.handle_oauth_callback(service, code, state, user_id)

        if result.get("success"):
            # Redirect back to Streamlit with success message
            service_name = service.title()
            message = result.get("message", f"Successfully connected {service_name}")
            return RedirectResponse(
                url=f"http://localhost:8501?oauth_success={service}&message={message}",
                status_code=302,
            )
        else:
            # Redirect back to Streamlit with error
            error_msg = result.get("message", "OAuth connection failed")
            return RedirectResponse(
                url=f"http://localhost:8501?oauth_error={error_msg}", status_code=302
            )

    except (OAuthConfigurationError, OAuthTokenError) as e:
        # Redirect back to Streamlit with error
        return RedirectResponse(
            url=f"http://localhost:8501?oauth_error={str(e)}", status_code=302
        )
    except OAuthServiceError as e:
        # Redirect back to Streamlit with error
        return RedirectResponse(
            url=f"http://localhost:8501?oauth_error=Service error: {str(e)}",
            status_code=302,
        )


@router.get("/status/{user_id}", response_model=OAuthStatusResponse)
async def get_oauth_status(user_id: str) -> OAuthStatusResponse:
    """
    Get OAuth status for all services for a specific user.

    Args:
        user_id: User identifier

    Returns:
        OAuth status for Todoist and Google accounts

    Raises:
        HTTPException: If user not found or database error
    """
    oauth_service = get_oauth_service()
    try:
        status_data = oauth_service.get_oauth_status(user_id)
        return OAuthStatusResponse(
            todoist=OAuthStatus(**status_data["todoist"]),
            google_accounts=[
                {
                    "user_id": acc["user_id"],
                    "email": acc["email"],
                    "name": acc["name"],
                    "is_valid": acc["is_valid"],
                    "calendars_enabled": acc["calendars_enabled"],
                    "calendars_total": acc["calendars_total"],
                }
                for acc in status_data["google_accounts"]
            ],
        )
    except OAuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete(
    "/disconnect/{service}/{user_id}", response_model=OAuthDisconnectResponse
)
async def disconnect_oauth_service(
    service: str, user_id: str
) -> OAuthDisconnectResponse:
    """
    Disconnect a specific OAuth service for a user.

    Args:
        service: Service name ("todoist" or "google")
        user_id: User identifier (for Google, includes account email)

    Returns:
        Success response with disconnection status

    Raises:
        HTTPException: If service is unsupported or disconnection fails
    """
    if service not in ["todoist", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported service: {service}",
        )

    oauth_service = get_oauth_service()
    try:
        success = oauth_service.remove_token(service, user_id)
        return OAuthDisconnectResponse(
            success=success,
            message=f"Successfully disconnected {service.title()}" if success else f"Failed to disconnect {service.title()}"
        )
    except OAuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/refresh/{service}/{user_id}", response_model=OAuthRefreshResponse)
async def refresh_oauth_token(service: str, user_id: str) -> OAuthRefreshResponse:
    """
    Refresh OAuth token for a specific service and user.

    Args:
        service: Service name ("todoist" or "google")
        user_id: User identifier

    Returns:
        Success response with refresh status and new expiration

    Raises:
        HTTPException: If service is unsupported or refresh fails
    """
    if service not in ["todoist", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported service: {service}",
        )

    # TODO: Implement in Task 2.10 with OAuth service layer
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth service layer not yet implemented. "
        "Will be completed in Task 2.10.",
    )


# Calendar-specific endpoints
calendar_router = APIRouter(prefix="/api/calendars", tags=["calendars"])


@calendar_router.get("/{user_id}", response_model=CalendarsResponse)
async def get_user_calendars(user_id: str) -> CalendarsResponse:
    """
    Get calendar list for a user's Google accounts.

    Args:
        user_id: User identifier

    Returns:
        List of calendars with enabled/disabled status

    Raises:
        HTTPException: If user not found or no Google accounts connected
    """
    # TODO: Implement in Task 2.10 with OAuth service layer
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth service layer not yet implemented. "
        "Will be completed in Task 2.10.",
    )


@calendar_router.put(
    "/{user_id}/preferences", response_model=CalendarPreferencesResponse
)
async def update_calendar_preferences(
    user_id: str, preferences: CalendarPreferencesRequest
) -> CalendarPreferencesResponse:
    """
    Update calendar preferences for a user.

    Args:
        user_id: User identifier
        preferences: Calendar preferences to update

    Returns:
        Success response with update count

    Raises:
        HTTPException: If user not found or update fails
    """
    # TODO: Implement in Task 2.10 with OAuth service layer
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth service layer not yet implemented. "
        "Will be completed in Task 2.10.",
    )


@calendar_router.get("/{user_id}/summary")
async def get_calendar_summary(user_id: str) -> Dict[str, int]:
    """
    Get summary of enabled vs total calendars for a user.

    Args:
        user_id: User identifier

    Returns:
        Summary with enabled and total calendar counts

    Raises:
        HTTPException: If user not found
    """
    # TODO: Implement in Task 2.10 with OAuth service layer
    return {"enabled": 0, "total": 0}


# Health check endpoints for OAuth services
@router.get("/health/{service}/{user_id}")
async def get_oauth_health(service: str, user_id: str) -> Dict[str, Any]:
    """
    Get detailed health information for an OAuth service.

    Args:
        service: Service name ("todoist" or "google")
        user_id: User identifier

    Returns:
        Detailed health status with expiration and refresh information

    Raises:
        HTTPException: If service is unsupported
    """
    if service not in ["todoist", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported service: {service}",
        )

    # TODO: Implement in Task 2.10 with OAuth service layer
    return {
        "status": "disconnected",
        "icon": "⚫",
        "message": "Not connected",
        "can_refresh": False,
    }


@router.get("/summary/{service}")
async def get_service_summary(service: str) -> Dict[str, Any]:
    """
    Get service summary information for all users.

    Args:
        service: Service name ("todoist" or "google")

    Returns:
        Service summary with account counts and status

    Raises:
        HTTPException: If service is unsupported
    """
    if service not in ["todoist", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported service: {service}",
        )

    # TODO: Implement in Task 2.10 with OAuth service layer
    return {
        "total_accounts": 0,
        "healthy_accounts": 0,
        "expired_accounts": 0,
        "service_status": "no_accounts",
    }
