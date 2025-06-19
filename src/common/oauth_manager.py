"""
OAuth Manager for Todoist and Google Calendar integrations.

This module provides OAuth 2.0 authentication flows and token management
for external service integrations with the weekly review agent.
"""

import json
import os
import secrets
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import requests
from urllib.parse import urlencode


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


class OAuthManager:
    """Manages OAuth flows and token storage for multiple services."""

    def __init__(self, storage_path: str = "oauth_tokens.json"):
        self.storage_path = storage_path
        self._tokens: Dict[str, Dict[str, OAuthToken]] = {}
        self._load_tokens()

    def _load_tokens(self) -> None:
        """Load tokens from persistent storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for service, users in data.items():
                        self._tokens[service] = {}
                        for user_id, token_data in users.items():
                            self._tokens[service][user_id] = OAuthToken(**token_data)
            except (json.JSONDecodeError, FileNotFoundError):
                self._tokens = {}

    def _save_tokens(self) -> None:
        """Save tokens to persistent storage."""
        try:
            data = {}
            for service, users in self._tokens.items():
                data[service] = {}
                for user_id, token in users.items():
                    data[service][user_id] = asdict(token)

            # Write to temporary file first, then rename for atomic operation
            temp_path = f"{self.storage_path}.tmp"
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.rename(temp_path, self.storage_path)
        except Exception as e:
            print(f"Error saving tokens: {e}")

    def store_token(self, service: str, user_id: str, token: OAuthToken) -> None:
        """Store an OAuth token for a user and service."""
        if service not in self._tokens:
            self._tokens[service] = {}
        self._tokens[service][user_id] = token
        self._save_tokens()

    def get_token(self, service: str, user_id: str) -> Optional[OAuthToken]:
        """Retrieve an OAuth token for a user and service."""
        return self._tokens.get(service, {}).get(user_id)

    def remove_token(self, service: str, user_id: str) -> None:
        """Remove an OAuth token for a user and service."""
        if service in self._tokens and user_id in self._tokens[service]:
            del self._tokens[service][user_id]
            if not self._tokens[service]:  # Remove service if no users
                del self._tokens[service]
            self._save_tokens()

    def is_token_valid(self, token: OAuthToken) -> bool:
        """Check if a token is still valid (not expired)."""
        if not token.expires_at:
            return True  # No expiration set
        return time.time() < token.expires_at

    def refresh_todoist_token(self, refresh_token: str) -> Optional[OAuthToken]:
        """
        Refresh a Todoist token (placeholder - Todoist doesn't support refresh tokens).
        """
        # Note: As of 2024, Todoist OAuth doesn't provide refresh tokens
        # This is a placeholder for future implementation if they add support
        return None

    def get_valid_token(self, service: str, user_id: str) -> Optional[OAuthToken]:
        """Get a valid token, refreshing if necessary."""
        token = self.get_token(service, user_id)
        if not token:
            return None

        if self.is_token_valid(token):
            return token

        # Try to refresh if possible
        if token.refresh_token and service == "todoist":
            refreshed = self.refresh_todoist_token(token.refresh_token)
            if refreshed:
                self.store_token(service, user_id, refreshed)
                return refreshed

        return None


class TodoistOAuth:
    """Handles Todoist OAuth 2.0 authentication flow."""

    def __init__(self, config: TodoistConfig, oauth_manager: OAuthManager):
        self.config = config
        self.oauth_manager = oauth_manager
        self.auth_url = "https://todoist.com/oauth/authorize"
        self.token_url = "https://todoist.com/oauth/access_token"
        self.api_base = "https://api.todoist.com/rest/v2"

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate the authorization URL for Todoist OAuth.

        Returns:
            tuple: (authorization_url, state)
        """
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "scope": self.config.scope,
            "state": state,
            "redirect_uri": self.config.redirect_uri,
        }

        auth_url = f"{self.auth_url}?{urlencode(params)}"
        return auth_url, state

    def exchange_code_for_token(self, code: str, state: str) -> Optional[OAuthToken]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from callback
            state: State parameter for CSRF protection

        Returns:
            OAuthToken if successful, None otherwise
        """
        try:
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": code,
                "redirect_uri": self.config.redirect_uri,
            }

            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()

            # Get user info
            user_info = self._get_user_info(token_data["access_token"])

            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                scope=self.config.scope,
                user_info=user_info,
            )

        except requests.RequestException as e:
            print(f"Error exchanging code for token: {e}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error parsing token response: {e}")
            return None

    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Todoist API."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                f"{self.api_base}/user", headers=headers, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error getting user info: {e}")
            return None

    def test_token(self, token: OAuthToken) -> bool:
        """Test if a token is working by making an API call."""
        try:
            headers = {"Authorization": f"Bearer {token.access_token}"}
            response = requests.get(
                f"{self.api_base}/user", headers=headers, timeout=10
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def revoke_token(self, token: OAuthToken) -> bool:
        """Revoke an access token."""
        try:
            params = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "access_token": token.access_token,
            }

            response = requests.delete(
                "https://api.todoist.com/api/v1/access_tokens",
                params=params,
                timeout=10,
            )
            return response.status_code == 200

        except requests.RequestException as e:
            print(f"Error revoking token: {e}")
            return False


def get_todoist_config() -> Optional[TodoistConfig]:
    """Get Todoist OAuth configuration from environment variables."""
    client_id = os.getenv("TODOIST_CLIENT_ID")
    client_secret = os.getenv("TODOIST_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "TODOIST_REDIRECT_URI", "http://localhost:8501/oauth/todoist/callback"
    )

    if not client_id or not client_secret:
        return None

    return TodoistConfig(
        client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri
    )


# Global OAuth manager instance
oauth_manager = OAuthManager()
