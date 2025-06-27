from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class WeeklyReviewEntry(BaseModel):
    """A single entry or note within a weekly review session (e.g., accomplishment, challenge, insight)."""

    type: str = Field(
        ...,
        description="Type of entry, e.g., 'accomplishment', 'challenge', 'insight', 'task', etc.",
    )
    content: str = Field(..., description="Content of the entry.")
    related_task_ids: Optional[List[str]] = Field(
        default=None, description="List of related task IDs, if any."
    )
    related_event_ids: Optional[List[str]] = Field(
        default=None, description="List of related calendar event IDs, if any."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata for the entry."
    )


class WeeklyReviewSession(BaseModel):
    """Structured data for a user's weekly review session."""

    user_id: str = Field(..., description="Unique user identifier.")
    session_id: str = Field(..., description="Unique session identifier.")
    start_time: datetime = Field(..., description="Start time of the review session.")
    end_time: Optional[datetime] = Field(
        default=None, description="End time of the review session."
    )
    week_start: datetime = Field(
        ..., description="Start date of the week being reviewed."
    )
    week_end: datetime = Field(..., description="End date of the week being reviewed.")
    entries: List[WeeklyReviewEntry] = Field(
        ..., description="List of entries for this review session."
    )
    summary: Optional[str] = Field(
        default=None, description="Summary or conclusion of the weekly review."
    )
    rules_version: Optional[str] = Field(
        default=None, description="Version of the weekly review rules used."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the session was created.",
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Timestamp when the session was last updated."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata for the session."
    )
