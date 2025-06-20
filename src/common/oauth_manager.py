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


@dataclass
class GoogleConfig:
    """Google OAuth configuration."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = (
        "https://www.googleapis.com/auth/calendar.readonly "
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly"
    )


class OAuthManager:
    """Manages OAuth flows and token storage for multiple services."""

    def __init__(self, storage_path: str = "oauth_tokens.json"):
        self.storage_path = storage_path
        self.calendar_prefs_path = "calendar_preferences.json"
        self._tokens: Dict[str, Dict[str, OAuthToken]] = {}
        self._calendar_preferences: Dict[str, Dict[str, Any]] = {}
        self._load_tokens()
        self._load_calendar_preferences()

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

    def _load_calendar_preferences(self) -> None:
        """Load calendar preferences from persistent storage."""
        if os.path.exists(self.calendar_prefs_path):
            try:
                with open(self.calendar_prefs_path, "r") as f:
                    self._calendar_preferences = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self._calendar_preferences = {}
        else:
            self._calendar_preferences = {}

    def _save_calendar_preferences(self) -> None:
        """Save calendar preferences to persistent storage."""
        try:
            # Write to temporary file first, then rename for atomic operation
            temp_path = f"{self.calendar_prefs_path}.tmp"
            with open(temp_path, "w") as f:
                json.dump(self._calendar_preferences, f, indent=2)
            os.rename(temp_path, self.calendar_prefs_path)
        except Exception as e:
            print(f"Error saving calendar preferences: {e}")

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

            # Also remove calendar preferences for Google accounts
            if service == "google":
                self.remove_calendar_preferences(user_id)

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

    def refresh_google_token(self, refresh_token: str) -> Optional[OAuthToken]:
        """
        Refresh a Google token using a refresh token.
        """
        google_config = get_google_config()
        if not google_config:
            return None

        google_oauth = GoogleOAuth(google_config, self)
        return google_oauth.refresh_token(refresh_token)

    def get_valid_token(self, service: str, user_id: str) -> Optional[OAuthToken]:
        """Get a valid token, refreshing if necessary."""
        token = self.get_token(service, user_id)
        if not token:
            return None

        if self.is_token_valid(token):
            return token

        # Try to refresh if possible
        if token.refresh_token:
            refreshed = None
            if service == "todoist":
                refreshed = self.refresh_todoist_token(token.refresh_token)
            elif service == "google":
                refreshed = self.refresh_google_token(token.refresh_token)

            if refreshed:
                self.store_token(service, user_id, refreshed)
                return refreshed

        return None

    def get_all_tokens(self, service: str) -> Dict[str, OAuthToken]:
        """Get all tokens for a specific service."""
        return self._tokens.get(service, {}).copy()

    def get_user_accounts(self, service: str) -> list[Dict[str, Any]]:
        """Get list of connected accounts for a service with user info."""
        accounts = []
        tokens = self.get_all_tokens(service)
        for user_id, token in tokens.items():
            if token.user_info:
                account = {
                    "user_id": user_id,
                    "email": token.user_info.get("email", "Unknown"),
                    "name": token.user_info.get("name", "Unknown"),
                    "is_valid": self.is_token_valid(token),
                    "connected_at": self._get_connection_time(service, user_id),
                    "last_used": self._get_last_used_time(service, user_id),
                    "has_refresh_token": bool(token.refresh_token),
                    "expires_at": token.expires_at,
                    "token_type": token.token_type,
                    "scope": token.scope,
                }
                accounts.append(account)
        return accounts

    def _get_connection_time(self, service: str, user_id: str) -> Optional[float]:
        """Get when an account was first connected."""
        # For now, we'll use a simple approach. In production, you might want
        # to store connection timestamps separately
        if service in self._tokens and user_id in self._tokens[service]:
            # Fallback to current time if no stored timestamp
            return time.time()
        return None

    def _get_last_used_time(self, service: str, user_id: str) -> Optional[float]:
        """Get when an account was last used."""
        # This could be enhanced to track actual API usage
        token = self.get_token(service, user_id)
        if token and token.expires_at:
            # Estimate last use based on token age
            return token.expires_at - 3600  # Assume 1 hour before expiry
        return None

    def refresh_account_token(self, service: str, user_id: str) -> bool:
        """Manually refresh a token for an account."""
        token = self.get_token(service, user_id)
        if not token or not token.refresh_token:
            return False

        refreshed_token = None
        if service == "google":
            refreshed_token = self.refresh_google_token(token.refresh_token)
        elif service == "todoist":
            # Todoist doesn't require refresh tokens - just validate current token
            refreshed_token = token

        if refreshed_token:
            self.store_token(service, user_id, refreshed_token)
            return True

        return False

    def get_account_health(self, service: str, user_id: str) -> Dict[str, Any]:
        """Get health status for an account."""
        token = self.get_token(service, user_id)
        if not token:
            return {
                "status": "disconnected",
                "message": "No token found",
                "can_refresh": False,
                "needs_reauth": True,
            }

        health = {
            "status": "unknown",
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
                    health["status"] = "expired_refreshable"
                    health["message"] = "Token expired but can be refreshed"
                else:
                    health["status"] = "expired"
                    health["message"] = "Token expired, requires re-authentication"
                    health["needs_reauth"] = True
            elif expires_in < 3600:  # Less than 1 hour
                health["status"] = "expiring_soon"
                health["message"] = f"Token expires in {int(expires_in/60)} minutes"
            else:
                health["status"] = "healthy"
                health["message"] = "Token is valid"
        else:
            # Token without expiration (like some service tokens)
            if self.is_token_valid(token):
                health["status"] = "healthy"
                health["message"] = "Token is valid"
            else:
                health["status"] = "invalid"
                health["message"] = "Token appears to be invalid"
                health["needs_reauth"] = True

        return health

    def get_service_summary(self, service: str) -> Dict[str, Any]:
        """Get summary statistics for a service."""
        accounts = self.get_user_accounts(service)

        total_accounts = len(accounts)
        healthy_accounts = sum(1 for acc in accounts if acc["is_valid"])
        expired_accounts = total_accounts - healthy_accounts

        with_refresh = sum(1 for acc in accounts if acc["has_refresh_token"])

        return {
            "total_accounts": total_accounts,
            "healthy_accounts": healthy_accounts,
            "expired_accounts": expired_accounts,
            "accounts_with_refresh": with_refresh,
            "service_status": (
                "healthy" if healthy_accounts == total_accounts else "degraded"
            ),
        }

    def store_calendar_preferences(
        self, user_id: str, calendars: list[Dict[str, Any]]
    ) -> None:
        """Store calendar preferences for a Google account."""
        self._calendar_preferences[user_id] = {
            "calendars": calendars,
            "updated_at": time.time(),
        }
        self._save_calendar_preferences()

    def get_calendar_preferences(self, user_id: str) -> Optional[list[Dict[str, Any]]]:
        """Get calendar preferences for a Google account."""
        prefs = self._calendar_preferences.get(user_id)
        if prefs:
            return prefs.get("calendars")
        return None

    def update_calendar_enabled_status(
        self, user_id: str, calendar_id: str, enabled: bool
    ) -> bool:
        """Update the enabled status of a specific calendar."""
        prefs = self._calendar_preferences.get(user_id)
        if not prefs or "calendars" not in prefs:
            return False

        for calendar in prefs["calendars"]:
            if calendar.get("id") == calendar_id:
                calendar["enabled"] = enabled
                prefs["updated_at"] = time.time()
                self._save_calendar_preferences()
                return True

        return False

    def get_enabled_calendars(self, user_id: str) -> list[Dict[str, Any]]:
        """Get list of enabled calendars for a Google account."""
        calendars = self.get_calendar_preferences(user_id)
        if not calendars:
            return []

        return [cal for cal in calendars if cal.get("enabled", True)]

    def remove_calendar_preferences(self, user_id: str) -> None:
        """Remove calendar preferences for a user (e.g., when disconnecting)."""
        if user_id in self._calendar_preferences:
            del self._calendar_preferences[user_id]
            self._save_calendar_preferences()

    def apply_calendar_filters(
        self, calendars: list[Dict[str, Any]], filters: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        """Apply filtering criteria to calendar list."""
        if not filters:
            return calendars

        filtered_calendars = calendars.copy()

        # Filter by access role
        if filters.get("access_roles"):
            allowed_roles = filters["access_roles"]
            filtered_calendars = [
                cal
                for cal in filtered_calendars
                if cal.get("access_role", "reader") in allowed_roles
            ]

        # Filter by calendar type/category
        if filters.get("calendar_types"):
            allowed_types = filters["calendar_types"]
            filtered_calendars = [
                cal
                for cal in filtered_calendars
                if self._get_calendar_type(cal) in allowed_types
            ]

        # Filter by keywords in name/description
        if filters.get("include_keywords"):
            keywords = [kw.lower() for kw in filters["include_keywords"]]
            filtered_calendars = [
                cal
                for cal in filtered_calendars
                if any(
                    keyword in cal.get("summary", "").lower()
                    or keyword in cal.get("description", "").lower()
                    for keyword in keywords
                )
            ]

        # Exclude calendars with certain keywords
        if filters.get("exclude_keywords"):
            keywords = [kw.lower() for kw in filters["exclude_keywords"]]
            filtered_calendars = [
                cal
                for cal in filtered_calendars
                if not any(
                    keyword in cal.get("summary", "").lower()
                    or keyword in cal.get("description", "").lower()
                    for keyword in keywords
                )
            ]

        # Filter by primary status
        if filters.get("primary_only"):
            filtered_calendars = [
                cal for cal in filtered_calendars if cal.get("primary", False)
            ]

        # Filter by ownership
        if filters.get("owned_only"):
            filtered_calendars = [
                cal for cal in filtered_calendars if cal.get("access_role") == "owner"
            ]

        return filtered_calendars

    def _get_calendar_type(self, calendar: Dict[str, Any]) -> str:
        """Determine calendar type/category."""
        summary = calendar.get("summary", "").lower()
        description = calendar.get("description", "").lower()

        # Primary calendar
        if calendar.get("primary"):
            return "primary"

        # Work-related keywords
        work_keywords = [
            "work",
            "office",
            "meetings",
            "team",
            "project",
            "company",
            "business",
            "client",
            "conference",
            "standup",
            "sprint",
        ]
        if any(
            keyword in summary or keyword in description for keyword in work_keywords
        ):
            return "work"

        # Personal keywords
        personal_keywords = [
            "personal",
            "family",
            "home",
            "birthday",
            "anniversary",
            "vacation",
            "holiday",
            "exercise",
            "fitness",
            "health",
        ]
        if any(
            keyword in summary or keyword in description
            for keyword in personal_keywords
        ):
            return "personal"

        # Holiday/special calendars
        if "holiday" in summary or "holiday" in description:
            return "holiday"

        # Shared calendars (not primary, multiple people have access)
        if calendar.get("access_role") in ["reader", "freeBusyReader"]:
            return "shared"

        return "other"

    def get_calendar_filter_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined filter presets for common use cases."""
        return {
            "all": {
                "name": "📅 All Calendars",
                "description": "Show all available calendars",
                "filters": {},
            },
            "work_only": {
                "name": "💼 Work Only",
                "description": "Work-related calendars only",
                "filters": {
                    "calendar_types": ["work", "primary"],
                    "access_roles": ["owner", "writer"],
                },
            },
            "personal_only": {
                "name": "🏠 Personal Only",
                "description": "Personal and family calendars only",
                "filters": {
                    "calendar_types": ["personal", "primary"],
                },
            },
            "owned_only": {
                "name": "👤 Owned Only",
                "description": "Calendars you own/manage",
                "filters": {
                    "owned_only": True,
                },
            },
            "primary_only": {
                "name": "⭐ Primary Only",
                "description": "Primary calendar only",
                "filters": {
                    "primary_only": True,
                },
            },
            "exclude_holidays": {
                "name": "🚫 No Holidays",
                "description": "Exclude holiday calendars",
                "filters": {
                    "exclude_keywords": ["holiday", "holidays"],
                },
            },
            "active_only": {
                "name": "🔥 Active Only",
                "description": "Calendars you can edit",
                "filters": {
                    "access_roles": ["owner", "writer"],
                },
            },
        }

    def get_calendar_statistics(
        self, calendars: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get statistics about calendar collection."""
        if not calendars:
            return {"total": 0}

        stats = {
            "total": len(calendars),
            "enabled": sum(1 for cal in calendars if cal.get("enabled", True)),
            "by_type": {},
            "by_access": {},
            "primary_count": sum(1 for cal in calendars if cal.get("primary", False)),
        }

        # Count by type
        for calendar in calendars:
            cal_type = self._get_calendar_type(calendar)
            stats["by_type"][cal_type] = stats["by_type"].get(cal_type, 0) + 1

        # Count by access role
        for calendar in calendars:
            access_role = calendar.get("access_role", "reader")
            stats["by_access"][access_role] = stats["by_access"].get(access_role, 0) + 1

        return stats


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


class GoogleOAuth:
    """Handles Google OAuth 2.0 authentication flow for Calendar API."""

    def __init__(self, config: GoogleConfig, oauth_manager: OAuthManager):
        self.config = config
        self.oauth_manager = oauth_manager
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.revoke_url = "https://oauth2.googleapis.com/revoke"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"

    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate the authorization URL for Google OAuth.

        Returns:
            tuple: (authorization_url, state)
        """
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
            "include_granted_scopes": "true",  # Incremental authorization
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
                "grant_type": "authorization_code",
                "redirect_uri": self.config.redirect_uri,
            }

            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()

            # Calculate expiration time
            expires_at = None
            if "expires_in" in token_data:
                expires_at = time.time() + int(token_data["expires_in"])

            # Get user info
            user_info = self._get_user_info(token_data["access_token"])

            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                refresh_token=token_data.get("refresh_token"),
                expires_at=expires_at,
                scope=token_data.get("scope", self.config.scope),
                user_info=user_info,
            )

        except requests.RequestException as e:
            print(f"Error exchanging code for token: {e}")
            return None
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing token response: {e}")
            return None

    def refresh_token(self, refresh_token: str) -> Optional[OAuthToken]:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            OAuthToken if successful, None otherwise
        """
        try:
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = requests.post(self.token_url, data=data, timeout=10)
            response.raise_for_status()

            token_data = response.json()

            # Calculate expiration time
            expires_at = None
            if "expires_in" in token_data:
                expires_at = time.time() + int(token_data["expires_in"])

            # Use existing refresh token if not provided in response
            new_refresh_token = token_data.get("refresh_token", refresh_token)

            # Get user info with new access token
            user_info = self._get_user_info(token_data["access_token"])

            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                refresh_token=new_refresh_token,
                expires_at=expires_at,
                scope=token_data.get("scope", self.config.scope),
                user_info=user_info,
            )

        except requests.RequestException as e:
            print(f"Error refreshing token: {e}")
            return None
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing refresh response: {e}")
            return None

    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google API."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(self.userinfo_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error getting user info: {e}")
            return None

    def test_token(self, token: OAuthToken) -> bool:
        """Test if a token is working by making an API call."""
        try:
            headers = {"Authorization": f"Bearer {token.access_token}"}
            # Test with Calendar API user info endpoint
            response = requests.get(
                "https://www.googleapis.com/calendar/v3/users/me/settings",
                headers=headers,
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_calendars(self, token: OAuthToken) -> Optional[list[Dict[str, Any]]]:
        """Get list of calendars from Google Calendar API."""
        try:
            headers = {"Authorization": f"Bearer {token.access_token}"}
            response = requests.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            calendar_data = response.json()
            calendars = []

            for calendar_item in calendar_data.get("items", []):
                calendar_info = {
                    "id": calendar_item.get("id"),
                    "summary": calendar_item.get("summary", "Untitled Calendar"),
                    "description": calendar_item.get("description", ""),
                    "primary": calendar_item.get("primary", False),
                    "access_role": calendar_item.get("accessRole", "reader"),
                    "selected": calendar_item.get("selected", True),
                    "background_color": calendar_item.get("backgroundColor", "#9FC6E7"),
                    "foreground_color": calendar_item.get("foregroundColor", "#000000"),
                    "time_zone": calendar_item.get("timeZone"),
                    "enabled": True,  # Default to enabled for new calendars
                }
                calendars.append(calendar_info)

            return calendars

        except requests.RequestException as e:
            print(f"Error fetching calendars: {e}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error parsing calendar response: {e}")
            return None

    def revoke_token(self, token: OAuthToken) -> bool:
        """Revoke an access token."""
        try:
            data = {"token": token.access_token}
            response = requests.post(self.revoke_url, data=data, timeout=10)
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


def get_google_config() -> Optional[GoogleConfig]:
    """Get Google OAuth configuration from environment variables."""
    client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8501/oauth/google/callback"
    )

    if not client_id or not client_secret:
        return None

    return GoogleConfig(
        client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri
    )


# Global OAuth manager instance
oauth_manager = OAuthManager()
