"""
Pydantic models for OAuth API requests and responses.

This module defines the data structures for OAuth management API endpoints,
providing request/response validation and OpenAPI documentation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Request Models


class OAuthStartRequest(BaseModel):
    """Request model for OAuth start endpoints."""

    user_id: str = Field(..., description="User identifier for OAuth association")


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback handling."""

    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State parameter for security verification")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class CalendarPreferencesRequest(BaseModel):
    """Request for updating calendar preferences."""

    calendar_preferences: List[Dict[str, Any]] = Field(
        ..., description="List of calendar configurations with enabled/disabled status"
    )


# Response Models


class OAuthStartResponse(BaseModel):
    """Response for OAuth start endpoints."""

    authorization_url: str = Field(
        ..., description="OAuth authorization URL to redirect user to"
    )
    state: str = Field(..., description="State parameter for security verification")
    message: str = Field(..., description="Human-readable success message")


class OAuthCallbackResponse(BaseModel):
    """Response for OAuth callback handling."""

    success: bool = Field(..., description="Whether OAuth callback was successful")
    service: str = Field(..., description="Service name (todoist or google)")
    user_email: Optional[str] = Field(None, description="Email of connected account")
    user_id: Optional[str] = Field(
        None, description="Unique user ID for the connected account"
    )
    message: str = Field(..., description="Human-readable result message")


class OAuthStatus(BaseModel):
    """OAuth status for a single service."""

    connected: bool = Field(..., description="Whether service is connected")
    user_email: Optional[str] = Field(None, description="Email of connected account")
    user_name: Optional[str] = Field(None, description="Name of connected user")
    expires_in: Optional[int] = Field(None, description="Seconds until token expires")
    status: str = Field(
        ..., description="Status: healthy, expired, expiring_soon, etc."
    )
    can_refresh: bool = Field(False, description="Whether token can be refreshed")


class GoogleAccount(BaseModel):
    """Google account information."""

    user_id: str = Field(..., description="Unique user ID for this Google account")
    email: str = Field(..., description="Google account email")
    name: str = Field(..., description="Google account display name")
    is_valid: bool = Field(..., description="Whether the token is currently valid")
    calendars_enabled: int = Field(..., description="Number of calendars enabled")
    calendars_total: int = Field(..., description="Total number of calendars")


class OAuthStatusResponse(BaseModel):
    """Response for OAuth status endpoint."""

    todoist: OAuthStatus = Field(..., description="Todoist OAuth status")
    google_accounts: List[GoogleAccount] = Field(
        ..., description="List of connected Google accounts"
    )


class OAuthDisconnectResponse(BaseModel):
    """Response for OAuth disconnect endpoint."""

    success: bool = Field(..., description="Whether disconnection was successful")
    message: str = Field(..., description="Human-readable result message")


class OAuthRefreshResponse(BaseModel):
    """Response for OAuth refresh endpoint."""

    success: bool = Field(..., description="Whether token refresh was successful")
    message: str = Field(..., description="Human-readable result message")
    expires_in: Optional[int] = Field(
        None, description="Seconds until new token expires"
    )


class OAuthHealthResponse(BaseModel):
    """Response for OAuth health endpoint."""

    status: str = Field(
        ..., description="Health status: healthy, expired, disconnected, etc."
    )
    icon: str = Field(..., description="Status icon emoji")
    message: str = Field(..., description="Human-readable status message")
    can_refresh: bool = Field(..., description="Whether token can be refreshed")
    needs_reauth: bool = Field(..., description="Whether re-authentication is required")
    expires_in: Optional[int] = Field(None, description="Seconds until token expires")


class ServiceSummaryResponse(BaseModel):
    """Response for service summary endpoint."""

    total_accounts: int = Field(..., description="Total number of connected accounts")
    healthy_accounts: int = Field(..., description="Number of healthy accounts")
    expired_accounts: int = Field(..., description="Number of expired accounts")
    service_status: str = Field(..., description="Overall service status")


# Calendar Models


class Calendar(BaseModel):
    """Google Calendar information."""

    id: str = Field(..., description="Calendar ID")
    summary: str = Field(..., description="Calendar name/title")
    description: Optional[str] = Field(None, description="Calendar description")
    primary: bool = Field(False, description="Whether this is the primary calendar")
    accessRole: str = Field(
        ..., description="User's access role (owner, writer, reader)"
    )
    enabled: bool = Field(
        True, description="Whether calendar is enabled for integration"
    )


class CalendarsResponse(BaseModel):
    """Response for calendars endpoint."""

    calendars: List[Calendar] = Field(..., description="List of available calendars")
    total_count: int = Field(..., description="Total number of calendars")
    enabled_count: int = Field(..., description="Number of enabled calendars")


class CalendarPreferencesResponse(BaseModel):
    """Response for calendar preferences update."""

    success: bool = Field(..., description="Whether preferences update was successful")
    message: str = Field(..., description="Human-readable result message")
    updated_count: int = Field(..., description="Number of calendars updated")


class CalendarSummaryResponse(BaseModel):
    """Response for calendar summary endpoint."""

    enabled: int = Field(..., description="Number of enabled calendars")
    total: int = Field(..., description="Total number of calendars")


# Error Models


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str = Field(..., description="Main error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
    errors: Optional[List[ErrorDetail]] = Field(
        None, description="Detailed error information"
    )


# Service Health Models


class OAuthServiceHealth(BaseModel):
    """OAuth service health check response."""

    status: str = Field(
        ..., description="Overall service status: healthy, degraded, unhealthy"
    )
    database_connection: bool = Field(
        ..., description="Whether database connection is working"
    )
    todoist_config: bool = Field(
        ..., description="Whether Todoist configuration is complete"
    )
    google_config: bool = Field(
        ..., description="Whether Google configuration is complete"
    )
    errors: List[str] = Field(
        ..., description="List of any errors found during health check"
    )


# Utility Models for Complex Operations


class BatchOperationRequest(BaseModel):
    """Request for batch operations on multiple accounts."""

    user_ids: List[str] = Field(..., description="List of user IDs to operate on")
    operation: str = Field(
        ..., description="Operation to perform: refresh, disconnect, test"
    )


class BatchOperationResponse(BaseModel):
    """Response for batch operations."""

    success_count: int = Field(..., description="Number of successful operations")
    failure_count: int = Field(..., description="Number of failed operations")
    results: List[Dict[str, Any]] = Field(
        ..., description="Detailed results for each operation"
    )


# Additional validation and configuration models


class OAuthConfiguration(BaseModel):
    """OAuth service configuration information."""

    service: str = Field(..., description="Service name")
    configured: bool = Field(..., description="Whether service is properly configured")
    client_id_set: bool = Field(..., description="Whether client ID is configured")
    client_secret_set: bool = Field(
        ..., description="Whether client secret is configured"
    )
    redirect_uri_set: bool = Field(
        ..., description="Whether redirect URI is configured"
    )
    missing_variables: List[str] = Field(
        ..., description="List of missing environment variables"
    )


class OAuthConfigurationResponse(BaseModel):
    """Response for OAuth configuration check."""

    todoist: OAuthConfiguration = Field(..., description="Todoist configuration status")
    google: OAuthConfiguration = Field(..., description="Google configuration status")
    overall_status: str = Field(..., description="Overall configuration status")
