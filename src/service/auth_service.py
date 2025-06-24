"""
Authentication Service Layer for Login Management.

This module provides authentication services for user login sessions,
JWT token management, and user account management separate from OAuth integrations.
"""

import time
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import logging

from memory.oauth_db import oauth_db

logger = logging.getLogger(__name__)


@dataclass
class LoginSession:
    """Login session data structure."""
    session_token: str
    app_user_id: str
    google_user_id: str
    expires_at: float
    created_at: float
    last_accessed_at: float
    is_active: bool


@dataclass
class UserAccount:
    """User account data structure."""
    app_user_id: str
    google_user_id: str
    email: str
    name: Optional[str]
    picture_url: Optional[str]
    is_primary_login: bool
    created_at: float
    updated_at: float


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class SessionExpiredError(AuthenticationError):
    """Exception for expired sessions."""
    pass


class InvalidSessionError(AuthenticationError):
    """Exception for invalid sessions."""
    pass


class AuthService:
    """Authentication service for managing login sessions and user accounts."""
    
    def __init__(self, jwt_secret: Optional[str] = None, session_duration_days: int = 30):
        """
        Initialize the authentication service.
        
        Args:
            jwt_secret: Secret key for JWT signing. If None, generates a random one.
            session_duration_days: How long sessions should last in days.
        """
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.session_duration_days = session_duration_days
        self.session_duration_seconds = session_duration_days * 24 * 60 * 60

    def generate_session_token(self, app_user_id: str, google_user_id: str) -> str:
        """Generate a JWT session token for a user."""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.session_duration_days)
        
        payload = {
            "app_user_id": app_user_id,
            "google_user_id": google_user_id,
            "iat": now,
            "exp": expires_at,
            "type": "login_session"
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def validate_session_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT session token and return user info.
        
        Returns:
            Dict with user info if valid
            
        Raises:
            SessionExpiredError: If token is expired
            InvalidSessionError: If token is invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Verify token type
            if payload.get("type") != "login_session":
                raise InvalidSessionError("Invalid token type")
                
            # Check if session exists in database
            session = oauth_db.get_login_session(token)
            if not session:
                raise InvalidSessionError("Session not found in database")
                
            # Update last accessed time
            oauth_db.update_session_access_time(token)
            
            return {
                "app_user_id": payload["app_user_id"],
                "google_user_id": payload["google_user_id"],
                "session_token": token
            }
            
        except jwt.ExpiredSignatureError:
            # Clean up expired session from database
            oauth_db.invalidate_session(token)
            raise SessionExpiredError("Session has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidSessionError(f"Invalid token: {str(e)}")

    def create_user_account(
        self, 
        google_user_info: Dict[str, Any], 
        app_user_id: Optional[str] = None
    ) -> UserAccount:
        """
        Create or update a user account from Google user info.
        
        Args:
            google_user_info: User info from Google OAuth
            app_user_id: Existing app user ID, or None to generate new one
        
        Returns:
            UserAccount object
        """
        google_user_id = google_user_info.get("id") or google_user_info.get("sub")
        if not google_user_id:
            raise AuthenticationError("No Google user ID found in user info")
            
        # Check if account already exists
        existing_account = oauth_db.get_user_account_by_google_id(google_user_id)
        
        if existing_account:
            # Update existing account
            app_user_id = existing_account["app_user_id"]
        else:
            # Create new account
            if not app_user_id:
                app_user_id = f"user_{secrets.token_urlsafe(16)}"
                
            # Check if this is the first account (make it primary)
            primary_account = oauth_db.get_primary_login_account()
            is_primary = primary_account is None
        
        # Create or update the account
        success = oauth_db.create_user_account(
            app_user_id=app_user_id,
            google_user_id=google_user_id,
            email=google_user_info.get("email", ""),
            name=google_user_info.get("name"),
            picture_url=google_user_info.get("picture"),
            is_primary_login=is_primary if not existing_account else existing_account["is_primary_login"]
        )
        
        if not success:
            raise AuthenticationError("Failed to create user account")
            
        # Return the account
        account_data = oauth_db.get_user_account_by_app_id(app_user_id)
        if not account_data:
            raise AuthenticationError("Failed to retrieve created account")
            
        return UserAccount(**account_data)

    def create_login_session(self, google_user_info: Dict[str, Any]) -> Tuple[str, UserAccount]:
        """
        Create a login session for a user.
        
        Args:
            google_user_info: User info from Google OAuth
            
        Returns:
            Tuple of (session_token, user_account)
        """
        # Create or get user account
        user_account = self.create_user_account(google_user_info)
        
        # Generate session token
        session_token = self.generate_session_token(
            user_account.app_user_id, 
            user_account.google_user_id
        )
        
        # Store session in database
        expires_at = time.time() + self.session_duration_seconds
        success = oauth_db.create_login_session(
            session_token=session_token,
            app_user_id=user_account.app_user_id,
            google_user_id=user_account.google_user_id,
            expires_at=expires_at
        )
        
        if not success:
            raise AuthenticationError("Failed to create login session")
            
        return session_token, user_account

    def get_user_from_session(self, session_token: str) -> Optional[UserAccount]:
        """Get user account from session token."""
        try:
            user_info = self.validate_session_token(session_token)
            account_data = oauth_db.get_user_account_by_app_id(user_info["app_user_id"])
            return UserAccount(**account_data) if account_data else None
        except (SessionExpiredError, InvalidSessionError):
            return None

    def logout_user(self, session_token: str) -> bool:
        """Logout a user by invalidating their session."""
        return oauth_db.invalidate_session(session_token)

    def logout_all_user_sessions(self, app_user_id: str) -> bool:
        """Logout all sessions for a user."""
        return oauth_db.invalidate_user_sessions(app_user_id)

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from database."""
        return oauth_db.cleanup_expired_sessions()

    def get_primary_login_account(self) -> Optional[UserAccount]:
        """Get the primary login account."""
        account_data = oauth_db.get_primary_login_account()
        return UserAccount(**account_data) if account_data else None

    def is_valid_login_account(self, google_user_id: str) -> bool:
        """Check if a Google user ID corresponds to a valid login account."""
        account = oauth_db.get_user_account_by_google_id(google_user_id)
        return account is not None and account.get("is_primary_login", False)


# Global auth service instance
auth_service = AuthService()