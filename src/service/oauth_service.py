"""
OAuth Service Layer for Backend API.

This module provides the service layer abstraction for OAuth operations,
replacing the embedded OAuth logic removed from the frontend in Task 2.8.
"""

import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from urllib.parse import urlencode

from memory.oauth_db import oauth_db

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class OAuthToken:
    """OAuth token data structure."""

    access_token: str
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    scope: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None


@dataclass
class TodoistConfig:
    """Todoist OAuth configuration."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "data:read_write"


@dataclass
class GoogleConfig:
    """Google OAuth configuration."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = (
        "openid email profile "
        "https://www.googleapis.com/auth/calendar.readonly "
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly"
    )


class OAuthServiceError(Exception):
    """Base exception for OAuth service errors."""

    pass


class OAuthConfigurationError(OAuthServiceError):
    """Exception for OAuth configuration errors."""

    pass


class OAuthTokenError(OAuthServiceError):
    """Exception for OAuth token errors."""

    pass


class OAuthService:
    """OAuth service layer for managing authentication flows and tokens."""

    def __init__(self, use_database: bool = True):
        self.use_database = use_database
        self._todoist_config = None
        self._google_config = None
        self._load_configurations()

    def _load_configurations(self) -> None:
        """Load OAuth configurations from environment variables."""
        try:
            # Load Todoist configuration
            todoist_client_id = os.getenv("TODOIST_CLIENT_ID")
            todoist_client_secret = os.getenv("TODOIST_CLIENT_SECRET")
            todoist_redirect_uri = os.getenv("TODOIST_REDIRECT_URI")

            if todoist_client_id and todoist_client_secret and todoist_redirect_uri:
                self._todoist_config = TodoistConfig(
                    client_id=todoist_client_id,
                    client_secret=todoist_client_secret,
                    redirect_uri=todoist_redirect_uri,
                )
                logger.info("Todoist OAuth configuration loaded successfully")
            else:
                logger.warning("Todoist OAuth configuration incomplete")

            # Load Google configuration
            google_client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
            google_client_secret = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
            google_redirect_uri = os.getenv("GOOGLE_CALENDAR_REDIRECT_URI")

            if google_client_id and google_client_secret and google_redirect_uri:
                self._google_config = GoogleConfig(
                    client_id=google_client_id,
                    client_secret=google_client_secret,
                    redirect_uri=google_redirect_uri,
                )
                logger.info("Google OAuth configuration loaded successfully")
            else:
                logger.warning("Google OAuth configuration incomplete")

        except Exception as e:
            logger.error(f"Error loading OAuth configurations: {e}")
            raise OAuthConfigurationError(f"Failed to load OAuth configurations: {e}")

    def get_todoist_config(self) -> Optional[TodoistConfig]:
        """Get Todoist OAuth configuration."""
        return self._todoist_config

    def get_google_config(self) -> Optional[GoogleConfig]:
        """Get Google OAuth configuration."""
        return self._google_config

    def start_todoist_oauth(self, user_id: str) -> Dict[str, str]:
        """
        Start Todoist OAuth flow.

        Args:
            user_id: User identifier for OAuth association

        Returns:
            Dict with authorization_url, state, and message

        Raises:
            OAuthConfigurationError: If Todoist configuration is missing
        """
        if not self._todoist_config:
            logger.error("Todoist OAuth configuration not available")
            raise OAuthConfigurationError(
                "Todoist OAuth configuration missing. Please set TODOIST_CLIENT_ID, "
                "TODOIST_CLIENT_SECRET, and TODOIST_REDIRECT_URI environment variables."
            )

        try:
            todoist_oauth = TodoistOAuth(self._todoist_config, self)
            auth_url, state = todoist_oauth.get_authorization_url()

            # Store state and user_id for verification during callback
            oauth_db.set_oauth_metadata(f"todoist_state_{user_id}", state)
            oauth_db.set_oauth_metadata(f"todoist_user_{state}", user_id)

            logger.info(f"Started Todoist OAuth flow for user {user_id}")
            return {
                "authorization_url": auth_url,
                "state": state,
                "message": "Redirect user to authorization URL to complete OAuth flow",
            }

        except Exception as e:
            logger.error(f"Error starting Todoist OAuth for user {user_id}: {e}")
            raise OAuthServiceError(f"Failed to start Todoist OAuth: {e}")

    def start_google_oauth(self, user_id: str) -> Dict[str, str]:
        """
        Start Google OAuth flow.

        Args:
            user_id: User identifier for OAuth association

        Returns:
            Dict with authorization_url, state, and message

        Raises:
            OAuthConfigurationError: If Google configuration is missing
        """
        if not self._google_config:
            logger.error("Google OAuth configuration not available")
            raise OAuthConfigurationError(
                "Google OAuth configuration missing. Please set GOOGLE_CALENDAR_CLIENT_ID, "
                "GOOGLE_CALENDAR_CLIENT_SECRET, and GOOGLE_CALENDAR_REDIRECT_URI environment variables."
            )

        try:
            google_oauth = GoogleOAuth(self._google_config, self)
            auth_url, state = google_oauth.get_authorization_url()

            # Store state and user_id for verification during callback
            oauth_db.set_oauth_metadata(f"google_state_{user_id}", state)
            oauth_db.set_oauth_metadata(f"google_user_{state}", user_id)

            logger.info(f"Started Google OAuth flow for user {user_id}")
            return {
                "authorization_url": auth_url,
                "state": state,
                "message": "Redirect user to authorization URL to complete OAuth flow",
            }

        except Exception as e:
            logger.error(f"Error starting Google OAuth for user {user_id}: {e}")
            raise OAuthServiceError(f"Failed to start Google OAuth: {e}")

    def handle_oauth_callback(
        self, service: str, code: str, state: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and exchange code for token.

        Args:
            service: Service name ("todoist" or "google")
            code: Authorization code from OAuth provider
            state: State parameter for security verification
            user_id: Optional user identifier

        Returns:
            Dict with success status and token information

        Raises:
            OAuthServiceError: If callback handling fails
        """
        try:
            if service == "todoist":
                return self._handle_todoist_callback(code, state, user_id)
            elif service == "google":
                return self._handle_google_callback(code, state, user_id)
            else:
                raise OAuthServiceError(f"Unsupported service: {service}")

        except Exception as e:
            logger.error(f"Error handling {service} OAuth callback: {e}")
            raise OAuthServiceError(f"Failed to handle {service} OAuth callback: {e}")

    def _handle_todoist_callback(
        self, code: str, state: str, user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Handle Todoist OAuth callback."""
        if not self._todoist_config:
            raise OAuthConfigurationError("Todoist configuration not available")

        # If user_id not provided, try to retrieve it from stored state
        if not user_id:
            user_id = oauth_db.get_oauth_metadata(f"todoist_user_{state}")
            if not user_id:
                raise OAuthServiceError(
                    "Could not determine user_id for OAuth callback"
                )

        # Verify state
        stored_state = oauth_db.get_oauth_metadata(f"todoist_state_{user_id}")
        if stored_state != state:
            raise OAuthServiceError("Invalid state parameter")

        todoist_oauth = TodoistOAuth(self._todoist_config, self)
        token = todoist_oauth.exchange_code_for_token(code, state)

        if not token:
            raise OAuthTokenError("Failed to exchange code for token")

        # Store token (user_id is guaranteed to exist now)
        self.store_token("todoist", user_id, token)

        # Clean up state metadata
        oauth_db.remove_oauth_metadata(f"todoist_state_{user_id}")
        oauth_db.remove_oauth_metadata(f"todoist_user_{state}")

        logger.info(f"Successfully handled Todoist OAuth callback for user {user_id}")
        return {
            "success": True,
            "service": "todoist",
            "user_email": token.user_info.get("email") if token.user_info else None,
            "message": "Successfully connected to Todoist",
        }

    def _handle_google_callback(
        self, code: str, state: str, user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Handle Google OAuth callback."""
        if not self._google_config:
            raise OAuthConfigurationError("Google configuration not available")

        # If user_id not provided, try to retrieve it from stored state
        if not user_id:
            user_id = oauth_db.get_oauth_metadata(f"google_user_{state}")
            if not user_id:
                raise OAuthServiceError(
                    "Could not determine user_id for OAuth callback"
                )

        # Verify state
        stored_state = oauth_db.get_oauth_metadata(f"google_state_{user_id}")
        if stored_state != state:
            raise OAuthServiceError("Invalid state parameter")

        google_oauth = GoogleOAuth(self._google_config, self)
        token = google_oauth.exchange_code_for_token(code, state)

        if not token:
            raise OAuthTokenError("Failed to exchange code for token")

        # Create unique user ID for Google account
        google_email = (
            token.user_info.get("email", "unknown") if token.user_info else "unknown"
        )
        google_user_id = f"{user_id}_google_{google_email}"

        # Store token
        self.store_token("google", google_user_id, token)

        # Clean up state metadata
        oauth_db.remove_oauth_metadata(f"google_state_{user_id}")
        oauth_db.remove_oauth_metadata(f"google_user_{state}")

        logger.info(f"Successfully handled Google OAuth callback for user {user_id}")
        return {
            "success": True,
            "service": "google",
            "user_email": google_email,
            "user_id": google_user_id,
            "message": f"Successfully connected Google account: {google_email}",
        }

    def store_token(self, service: str, user_id: str, token: OAuthToken) -> None:
        """Store an OAuth token for a user and service."""
        try:
            oauth_db.store_oauth_token(
                service=service,
                user_id=user_id,
                access_token=token.access_token,
                token_type=token.token_type,
                refresh_token=token.refresh_token,
                expires_at=token.expires_at,
                scope=token.scope,
                user_info=token.user_info,
            )
            logger.info(f"Stored {service} token for user {user_id}")

        except Exception as e:
            logger.error(f"Error storing {service} token for user {user_id}: {e}")
            raise OAuthServiceError(f"Failed to store token: {e}")

    def get_token(self, service: str, user_id: str) -> Optional[OAuthToken]:
        """Retrieve an OAuth token for a user and service."""
        try:
            token_data = oauth_db.get_oauth_token(service, user_id)
            if token_data:
                return OAuthToken(
                    access_token=token_data["access_token"],
                    token_type=token_data["token_type"],
                    refresh_token=token_data["refresh_token"],
                    expires_at=token_data["expires_at"],
                    scope=token_data["scope"],
                    user_info=token_data["user_info"],
                )
            return None

        except Exception as e:
            logger.error(f"Error retrieving {service} token for user {user_id}: {e}")
            return None

    def remove_token(self, service: str, user_id: str) -> bool:
        """Remove an OAuth token for a user and service."""
        try:
            # Get token to potentially revoke it
            token = self.get_token(service, user_id)

            if token:
                # Attempt to revoke token with the provider
                self._revoke_token_with_provider(service, token)

            # Remove from database
            oauth_db.remove_oauth_token(service, user_id)

            # Also remove calendar preferences for Google accounts
            if service == "google":
                oauth_db.remove_calendar_preferences(user_id)

            logger.info(f"Removed {service} token for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing {service} token for user {user_id}: {e}")
            return False

    def _revoke_token_with_provider(self, service: str, token: OAuthToken) -> None:
        """Attempt to revoke token with the OAuth provider."""
        try:
            if service == "todoist" and self._todoist_config:
                todoist_oauth = TodoistOAuth(self._todoist_config, self)
                todoist_oauth.revoke_token(token)
            elif service == "google" and self._google_config:
                google_oauth = GoogleOAuth(self._google_config, self)
                google_oauth.revoke_token(token)

        except Exception as e:
            logger.warning(f"Failed to revoke {service} token with provider: {e}")

    def refresh_token(self, service: str, user_id: str) -> bool:
        """Refresh an OAuth token for a user and service."""
        try:
            token = self.get_token(service, user_id)
            if not token or not token.refresh_token:
                logger.warning(
                    f"No refresh token available for {service} user {user_id}"
                )
                return False

            refreshed_token = None
            if service == "google" and self._google_config:
                google_oauth = GoogleOAuth(self._google_config, self)
                refreshed_token = google_oauth.refresh_token(token.refresh_token)
            elif service == "todoist":
                # Todoist doesn't support refresh tokens
                logger.info(f"Todoist doesn't support token refresh for user {user_id}")
                return True  # Consider current token still valid

            if refreshed_token:
                self.store_token(service, user_id, refreshed_token)
                logger.info(
                    f"Successfully refreshed {service} token for user {user_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error refreshing {service} token for user {user_id}: {e}")
            return False

    def get_oauth_status(self, user_id: str) -> Dict[str, Any]:
        """Get OAuth status for all services for a user."""
        try:
            # Get Todoist status
            todoist_token = self.get_token("todoist", user_id)
            todoist_status = {
                "connected": bool(todoist_token),
                "user_email": None,
                "status": "disconnected",
            }

            if todoist_token:
                todoist_status.update(
                    {
                        "user_email": (
                            todoist_token.user_info.get("email")
                            if todoist_token.user_info
                            else None
                        ),
                        "status": (
                            "healthy"
                            if self._is_token_valid(todoist_token)
                            else "expired"
                        ),
                    }
                )

            # Get Google accounts
            google_accounts = []
            google_tokens = oauth_db.get_all_oauth_tokens("google")
            for token_data in google_tokens:
                if token_data["user_id"].startswith(user_id):
                    token = OAuthToken(
                        access_token=token_data["access_token"],
                        token_type=token_data["token_type"],
                        refresh_token=token_data["refresh_token"],
                        expires_at=token_data["expires_at"],
                        scope=token_data["scope"],
                        user_info=token_data["user_info"],
                    )

                    account_info = {
                        "user_id": token_data["user_id"],
                        "email": (
                            token.user_info.get("email", "Unknown")
                            if token.user_info
                            else "Unknown"
                        ),
                        "name": (
                            token.user_info.get("name", "Unknown")
                            if token.user_info
                            else "Unknown"
                        ),
                        "is_valid": self._is_token_valid(token),
                        "calendars_enabled": 0,  # Will be populated by calendar service
                        "calendars_total": 0,  # Will be populated by calendar service
                    }
                    google_accounts.append(account_info)

            return {"todoist": todoist_status, "google_accounts": google_accounts}

        except Exception as e:
            logger.error(f"Error getting OAuth status for user {user_id}: {e}")
            return {
                "todoist": {"connected": False, "status": "error"},
                "google_accounts": [],
            }

    def _is_token_valid(self, token: OAuthToken) -> bool:
        """Check if a token is still valid (not expired)."""
        if not token.expires_at:
            return True  # No expiration set
        return time.time() < token.expires_at

    def get_account_health(self, service: str, user_id: str) -> Dict[str, Any]:
        """Get detailed health status for an account."""
        try:
            token = self.get_token(service, user_id)
            if not token:
                return {
                    "status": "disconnected",
                    "icon": "⚫",
                    "message": "No token found",
                    "can_refresh": False,
                    "needs_reauth": True,
                }

            health = {
                "status": "unknown",
                "icon": "⚪",
                "message": "",
                "can_refresh": bool(token.refresh_token),
                "needs_reauth": False,
                "expires_in": None,
            }

            if token.expires_at:
                expires_in = token.expires_at - time.time()
                health["expires_in"] = expires_in

                if expires_in <= 0:
                    if token.refresh_token:
                        health.update(
                            {
                                "status": "expired_refreshable",
                                "icon": "🟠",
                                "message": "Token expired but can be refreshed",
                            }
                        )
                    else:
                        health.update(
                            {
                                "status": "expired",
                                "icon": "🔴",
                                "message": "Token expired, requires re-authentication",
                                "needs_reauth": True,
                            }
                        )
                elif expires_in < 3600:  # Less than 1 hour
                    health.update(
                        {
                            "status": "expiring_soon",
                            "icon": "🟡",
                            "message": f"Token expires in {int(expires_in/60)} minutes",
                        }
                    )
                else:
                    health.update(
                        {"status": "healthy", "icon": "🟢", "message": "Token is valid"}
                    )
            else:
                if self._is_token_valid(token):
                    health.update(
                        {"status": "healthy", "icon": "🟢", "message": "Token is valid"}
                    )
                else:
                    health.update(
                        {
                            "status": "invalid",
                            "icon": "🔴",
                            "message": "Token appears to be invalid",
                            "needs_reauth": True,
                        }
                    )

            return health

        except Exception as e:
            logger.error(
                f"Error getting account health for {service} user {user_id}: {e}"
            )
            return {
                "status": "error",
                "icon": "🔴",
                "message": f"Error checking account health: {e}",
                "can_refresh": False,
                "needs_reauth": True,
            }

    def get_service_summary(self, service: str) -> Dict[str, Any]:
        """Get service summary statistics."""
        try:
            tokens = oauth_db.get_all_oauth_tokens(service)

            total_accounts = len(tokens)
            healthy_accounts = 0
            expired_accounts = 0

            for token_data in tokens:
                token = OAuthToken(
                    access_token=token_data["access_token"],
                    token_type=token_data["token_type"],
                    refresh_token=token_data["refresh_token"],
                    expires_at=token_data["expires_at"],
                    scope=token_data["scope"],
                    user_info=token_data["user_info"],
                )

                if self._is_token_valid(token):
                    healthy_accounts += 1
                else:
                    expired_accounts += 1

            service_status = "healthy" if expired_accounts == 0 else "degraded"
            if total_accounts == 0:
                service_status = "no_accounts"

            return {
                "total_accounts": total_accounts,
                "healthy_accounts": healthy_accounts,
                "expired_accounts": expired_accounts,
                "service_status": service_status,
            }

        except Exception as e:
            logger.error(f"Error getting service summary for {service}: {e}")
            return {
                "total_accounts": 0,
                "healthy_accounts": 0,
                "expired_accounts": 0,
                "service_status": "error",
            }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the OAuth service."""
        try:
            health = {
                "status": "healthy",
                "database_connection": False,
                "todoist_config": bool(self._todoist_config),
                "google_config": bool(self._google_config),
                "errors": [],
            }

            # Check database connection
            try:
                oauth_db.get_oauth_metadata("health_check")
                health["database_connection"] = True
            except Exception as e:
                health["errors"].append(f"Database connection failed: {e}")

            # Check configuration completeness
            if not self._todoist_config:
                health["errors"].append("Todoist OAuth configuration incomplete")

            if not self._google_config:
                health["errors"].append("Google OAuth configuration incomplete")

            if health["errors"]:
                health["status"] = "degraded"

            return health

        except Exception as e:
            logger.error(f"Error performing OAuth service health check: {e}")
            return {
                "status": "unhealthy",
                "database_connection": False,
                "todoist_config": False,
                "google_config": False,
                "errors": [f"Health check failed: {e}"],
            }


# OAuth provider classes (moved from common/oauth_manager.py)


class TodoistOAuth:
    """Todoist OAuth 2.0 handler."""

    def __init__(self, config: TodoistConfig, oauth_service: OAuthService):
        self.config = config
        self.oauth_service = oauth_service

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """Generate authorization URL for Todoist OAuth."""
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "scope": self.config.scope,
            "state": state,
        }

        base_url = "https://todoist.com/oauth/authorize"
        auth_url = f"{base_url}?{urlencode(params)}"

        logger.info("Generated Todoist authorization URL")
        return auth_url, state

    def exchange_code_for_token(self, code: str, state: str) -> Optional[OAuthToken]:
        """Exchange authorization code for access token."""
        try:
            token_data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": code,
            }

            response = requests.post(
                "https://todoist.com/oauth/access_token", data=token_data, timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")

                if access_token:
                    # Get user info
                    user_info = self._get_user_info(access_token)

                    token = OAuthToken(
                        access_token=access_token,
                        token_type="Bearer",
                        user_info=user_info,
                        scope=self.config.scope,
                    )

                    logger.info("Successfully exchanged Todoist code for token")
                    return token

            logger.error(
                f"Todoist token exchange failed: {response.status_code} - {response.text}"
            )
            return None

        except Exception as e:
            logger.error(f"Error exchanging Todoist code for token: {e}")
            return None

    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Todoist API."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                "https://api.todoist.com/rest/v2/user", headers=headers, timeout=30
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Error getting Todoist user info: {e}")

        return None

    def test_token(self, token: OAuthToken) -> bool:
        """Test if a token is valid by making an API call."""
        try:
            headers = {"Authorization": f"Bearer {token.access_token}"}
            response = requests.get(
                "https://api.todoist.com/rest/v2/user", headers=headers, timeout=30
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error testing Todoist token: {e}")
            return False

    def revoke_token(self, token: OAuthToken) -> bool:
        """Revoke a Todoist token."""
        try:
            # Todoist doesn't have a specific revoke endpoint
            # The token becomes invalid when removed from their side
            logger.info("Todoist token revoked (implicit)")
            return True

        except Exception as e:
            logger.error(f"Error revoking Todoist token: {e}")
            return False


class GoogleOAuth:
    """Google OAuth 2.0 handler."""

    def __init__(self, config: GoogleConfig, oauth_service: OAuthService):
        self.config = config
        self.oauth_service = oauth_service

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """Generate authorization URL for Google OAuth."""
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
            "response_type": "code",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent to get refresh token
            "state": state,
        }

        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        auth_url = f"{base_url}?{urlencode(params)}"

        logger.info("Generated Google authorization URL")
        return auth_url, state

    def exchange_code_for_token(self, code: str, state: str) -> Optional[OAuthToken]:
        """Exchange authorization code for access token."""
        try:
            token_data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.config.redirect_uri,
            }

            response = requests.post(
                "https://oauth2.googleapis.com/token", data=token_data, timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                expires_in = data.get("expires_in")

                if access_token:
                    expires_at = None
                    if expires_in:
                        expires_at = time.time() + expires_in

                    # Get user info
                    user_info = self._get_user_info(access_token)

                    token = OAuthToken(
                        access_token=access_token,
                        token_type="Bearer",
                        refresh_token=refresh_token,
                        expires_at=expires_at,
                        scope=self.config.scope,
                        user_info=user_info,
                    )

                    logger.info("Successfully exchanged Google code for token")
                    return token

            logger.error(
                f"Google token exchange failed: {response.status_code} - {response.text}"
            )
            return None

        except Exception as e:
            logger.error(f"Error exchanging Google code for token: {e}")
            return None

    def refresh_token(self, refresh_token: str) -> Optional[OAuthToken]:
        """Refresh a Google access token using refresh token."""
        try:
            token_data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = requests.post(
                "https://oauth2.googleapis.com/token", data=token_data, timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                expires_in = data.get("expires_in")

                if access_token:
                    expires_at = None
                    if expires_in:
                        expires_at = time.time() + expires_in

                    # Get user info
                    user_info = self._get_user_info(access_token)

                    token = OAuthToken(
                        access_token=access_token,
                        token_type="Bearer",
                        refresh_token=refresh_token,  # Keep original refresh token
                        expires_at=expires_at,
                        scope=self.config.scope,
                        user_info=user_info,
                    )

                    logger.info("Successfully refreshed Google token")
                    return token

            logger.error(
                f"Google token refresh failed: {response.status_code} - {response.text}"
            )
            return None

        except Exception as e:
            logger.error(f"Error refreshing Google token: {e}")
            return None

    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google API."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Error getting Google user info: {e}")

        return None

    def test_token(self, token: OAuthToken) -> bool:
        """Test if a token is valid by making an API call."""
        try:
            headers = {"Authorization": f"Bearer {token.access_token}"}
            response = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers,
                timeout=30,
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error testing Google token: {e}")
            return False

    def get_calendars(self, token: OAuthToken) -> Optional[List[Dict[str, Any]]]:
        """Get calendars for a Google account."""
        try:
            headers = {"Authorization": f"Bearer {token.access_token}"}
            response = requests.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                calendars = []

                for item in data.get("items", []):
                    calendar = {
                        "id": item.get("id"),
                        "summary": item.get("summary", "Unnamed Calendar"),
                        "description": item.get("description"),
                        "primary": item.get("primary", False),
                        "accessRole": item.get("accessRole", "reader"),
                        "enabled": True,  # Default to enabled
                    }
                    calendars.append(calendar)

                logger.info(f"Retrieved {len(calendars)} calendars from Google")
                return calendars

            logger.error(
                f"Failed to get Google calendars: {response.status_code} - {response.text}"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting Google calendars: {e}")
            return None

    def revoke_token(self, token: OAuthToken) -> bool:
        """Revoke a Google token."""
        try:
            params = {"token": token.access_token}
            response = requests.post(
                "https://oauth2.googleapis.com/revoke", params=params, timeout=30
            )

            success = response.status_code == 200
            if success:
                logger.info("Successfully revoked Google token")
            else:
                logger.error(f"Failed to revoke Google token: {response.status_code}")

            return success

        except Exception as e:
            logger.error(f"Error revoking Google token: {e}")
            return False


# Service factory for dependency injection
def create_oauth_service() -> OAuthService:
    """Factory function to create OAuth service instance."""
    return OAuthService(use_database=True)


# Global service instance for dependency injection
_oauth_service_instance: Optional[OAuthService] = None


def get_oauth_service() -> OAuthService:
    """Get or create OAuth service instance (singleton pattern)."""
    global _oauth_service_instance
    if _oauth_service_instance is None:
        _oauth_service_instance = create_oauth_service()
    return _oauth_service_instance
