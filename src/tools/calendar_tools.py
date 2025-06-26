"""
Google Calendar Tools for Multi-Account Calendar Data Fetching.

This module provides tools for fetching and analyzing calendar events across multiple
Google Calendar accounts for the weekly review agent. It builds on the existing
oauth_manager infrastructure to provide comprehensive calendar data access.

Functional Requirements Addressed:
- FR-007: Multi-account calendar data fetching
- FR-014: Past week accomplishment identification from calendar events
- FR-018: Time slot analysis and availability detection
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from urllib.parse import urlencode

from common.oauth_manager import oauth_manager, OAuthToken


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    """Standardized calendar event data structure."""

    id: str
    summary: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: bool = False
    calendar_id: str = ""
    calendar_name: str = ""
    account_email: str = ""
    location: Optional[str] = None
    attendees: List[Dict[str, Any]] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    status: str = "confirmed"  # confirmed, cancelled, tentative
    transparency: str = "opaque"  # opaque, transparent
    visibility: str = "default"  # default, public, private
    recurring: bool = False
    recurring_event_id: Optional[str] = None
    organizer: Optional[Dict[str, Any]] = None
    creator: Optional[Dict[str, Any]] = None
    etag: Optional[str] = None
    html_link: Optional[str] = None

    def __post_init__(self):
        """Initialize attendees list if None."""
        if self.attendees is None:
            self.attendees = []

    @property
    def duration_minutes(self) -> Optional[int]:
        """Get event duration in minutes."""
        if not self.start_time or not self.end_time:
            return None
        if self.all_day:
            return None  # All-day events don't have duration in minutes
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    @property
    def is_past(self) -> bool:
        """Check if event is in the past."""
        if self.all_day:
            # For all-day events, compare dates
            return self.start_time.date() < datetime.now().date()
        return self.end_time < datetime.now()

    @property
    def is_upcoming(self) -> bool:
        """Check if event is upcoming."""
        return self.start_time > datetime.now()

    @property
    def is_today(self) -> bool:
        """Check if event is today."""
        return self.start_time.date() == datetime.now().date()

    @property
    def is_this_week(self) -> bool:
        """Check if event is this week."""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week <= self.start_time.date() <= end_of_week


@dataclass
class CalendarSummary:
    """Summary of calendar events for analysis."""

    total_events: int
    events_by_calendar: Dict[str, int]
    events_by_account: Dict[str, int]
    events_by_day: Dict[str, int]  # Date string -> count
    total_duration_minutes: int
    average_event_duration: Optional[float]
    busiest_day: Optional[str]
    busiest_account: Optional[str]
    busiest_calendar: Optional[str]
    upcoming_events: int
    past_events: int
    all_day_events: int
    working_hours_events: int  # 9 AM - 5 PM
    evening_events: int  # After 5 PM
    weekend_events: int


class CalendarAPIError(Exception):
    """Exception raised for Google Calendar API errors."""

    pass


class CalendarAuthError(CalendarAPIError):
    """Exception raised for authentication/authorization errors."""

    pass


class CalendarRateLimitError(CalendarAPIError):
    """Exception raised when API rate limits are exceeded."""

    pass


class CalendarDataFetcher:
    """Handles fetching calendar data from Google Calendar API across multiple accounts."""

    CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

    def __init__(self, oauth_manager_instance=None):
        """Initialize with oauth manager instance."""
        self.oauth_manager = oauth_manager_instance or oauth_manager
        self.request_timeout = 30
        self.max_results_per_request = 250  # Google Calendar API limit
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

    def get_all_google_accounts(self) -> List[Dict[str, Any]]:
        """Get all connected Google accounts with basic info."""
        try:
            return self.oauth_manager.get_user_accounts("google")
        except Exception as e:
            logger.error(f"Error getting Google accounts: {e}")
            return []

    def get_calendars_for_account(self, user_id: str) -> List[Dict[str, Any]]:
        """Get calendars for a specific Google account."""
        try:
            # Get enabled calendars only
            calendars = self.oauth_manager.get_enabled_calendars(user_id)
            if not calendars:
                # Fall back to getting all calendars if no preferences set
                token = self.oauth_manager.get_valid_token("google", user_id)
                if token:
                    # Use the GoogleOAuth class to fetch calendars
                    from common.oauth_manager import GoogleOAuth, get_google_config

                    google_config = get_google_config()
                    if google_config:
                        google_oauth = GoogleOAuth(google_config, self.oauth_manager)
                        calendars = google_oauth.get_calendars(token)
                        if calendars:
                            # Store preferences for future use
                            self.oauth_manager.store_calendar_preferences(
                                user_id, calendars
                            )

            return calendars or []
        except Exception as e:
            logger.error(f"Error getting calendars for account {user_id}: {e}")
            return []

    def get_all_calendars_multi_account(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get calendars from all connected Google accounts."""
        all_calendars = {}
        accounts = self.get_all_google_accounts()

        for account in accounts:
            user_id = account["user_id"]
            email = account["email"]
            calendars = self.get_calendars_for_account(user_id)
            if calendars:
                all_calendars[email] = calendars

        return all_calendars

    def _make_calendar_api_request(
        self, token: OAuthToken, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a request to Google Calendar API with error handling and retries."""
        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Accept": "application/json",
        }

        url = f"{self.CALENDAR_API_BASE}/{endpoint}"
        if params:
            url += f"?{urlencode(params)}"

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url, headers=headers, timeout=self.request_timeout
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise CalendarAuthError(f"Authentication failed for Calendar API")
                elif response.status_code == 403:
                    # Check if it's a rate limit error
                    error_data = response.json().get("error", {})
                    if "quotaExceeded" in error_data.get("message", ""):
                        raise CalendarRateLimitError("Calendar API quota exceeded")
                    else:
                        raise CalendarAPIError(
                            f"Access denied: {error_data.get('message', 'Unknown error')}"
                        )
                elif response.status_code == 429:
                    # Rate limited, wait and retry
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limited, waiting {wait_time}s before retry {attempt + 1}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()

            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Calendar API request failed after {self.max_retries} attempts: {e}"
                    )
                    raise CalendarAPIError(f"Request failed: {e}")
                else:
                    logger.warning(
                        f"Calendar API request attempt {attempt + 1} failed: {e}"
                    )
                    time.sleep(self.retry_delay * (attempt + 1))

        return None

    def fetch_events_from_calendar(
        self,
        user_id: str,
        calendar_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: Optional[int] = None,
    ) -> List[CalendarEvent]:
        """Fetch events from a specific calendar."""
        token = self.oauth_manager.get_valid_token("google", user_id)
        if not token:
            logger.warning(f"No valid token for user {user_id}")
            return []

        # Set default time range if not provided (last 30 days)
        if not start_time:
            start_time = datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now() + timedelta(days=30)

        # Ensure timezone awareness
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        params = {
            "timeMin": start_time.isoformat(),
            "timeMax": end_time.isoformat(),
            "singleEvents": "true",  # Expand recurring events
            "orderBy": "startTime",
            "maxResults": max_results or self.max_results_per_request,
        }

        try:
            response_data = self._make_calendar_api_request(
                token, f"calendars/{calendar_id}/events", params
            )

            if not response_data:
                return []

            events = []
            account_info = self._get_account_info_from_user_id(user_id)
            account_email = (
                account_info.get("email", "unknown") if account_info else "unknown"
            )

            for event_data in response_data.get("items", []):
                event = self._parse_event_data(event_data, calendar_id, account_email)
                if event:
                    events.append(event)

            # Handle pagination if there are more results
            next_page_token = response_data.get("nextPageToken")
            while next_page_token and len(events) < (max_results or 1000):
                params["pageToken"] = next_page_token
                params["maxResults"] = min(
                    self.max_results_per_request, (max_results or 1000) - len(events)
                )

                response_data = self._make_calendar_api_request(
                    token, f"calendars/{calendar_id}/events", params
                )

                if not response_data:
                    break

                for event_data in response_data.get("items", []):
                    event = self._parse_event_data(
                        event_data, calendar_id, account_email
                    )
                    if event:
                        events.append(event)

                next_page_token = response_data.get("nextPageToken")

            logger.info(f"Fetched {len(events)} events from calendar {calendar_id}")
            return events

        except Exception as e:
            logger.error(f"Error fetching events from calendar {calendar_id}: {e}")
            return []

    def _get_account_info_from_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account info from user_id."""
        accounts = self.get_all_google_accounts()
        for account in accounts:
            if account["user_id"] == user_id:
                return account
        return None

    def _parse_event_data(
        self, event_data: Dict[str, Any], calendar_id: str, account_email: str
    ) -> Optional[CalendarEvent]:
        """Parse raw Google Calendar event data into CalendarEvent object."""
        try:
            # Parse start and end times
            start_info = event_data.get("start", {})
            end_info = event_data.get("end", {})

            # Check if it's an all-day event
            all_day = "date" in start_info and "dateTime" not in start_info

            if all_day:
                # All-day event - parse date only
                start_time = datetime.fromisoformat(start_info["date"]).replace(
                    tzinfo=timezone.utc
                )
                end_time = datetime.fromisoformat(end_info["date"]).replace(
                    tzinfo=timezone.utc
                )
            else:
                # Timed event - parse datetime
                start_time = datetime.fromisoformat(
                    start_info.get("dateTime", "").replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(
                    end_info.get("dateTime", "").replace("Z", "+00:00")
                )

            # Parse attendees
            attendees = []
            for attendee in event_data.get("attendees", []):
                attendees.append(
                    {
                        "email": attendee.get("email"),
                        "displayName": attendee.get("displayName"),
                        "responseStatus": attendee.get("responseStatus", "needsAction"),
                        "organizer": attendee.get("organizer", False),
                        "self": attendee.get("self", False),
                    }
                )

            # Parse organizer and creator
            organizer = event_data.get("organizer", {})
            creator = event_data.get("creator", {})

            # Parse creation and update times
            created = None
            updated = None
            if event_data.get("created"):
                created = datetime.fromisoformat(
                    event_data["created"].replace("Z", "+00:00")
                )
            if event_data.get("updated"):
                updated = datetime.fromisoformat(
                    event_data["updated"].replace("Z", "+00:00")
                )

            return CalendarEvent(
                id=event_data.get("id", ""),
                summary=event_data.get("summary", "Untitled Event"),
                description=event_data.get("description"),
                start_time=start_time,
                end_time=end_time,
                all_day=all_day,
                calendar_id=calendar_id,
                calendar_name=self._get_calendar_name(calendar_id, account_email),
                account_email=account_email,
                location=event_data.get("location"),
                attendees=attendees,
                created=created,
                updated=updated,
                status=event_data.get("status", "confirmed"),
                transparency=event_data.get("transparency", "opaque"),
                visibility=event_data.get("visibility", "default"),
                recurring="recurringEventId" in event_data,
                recurring_event_id=event_data.get("recurringEventId"),
                organizer=organizer,
                creator=creator,
                etag=event_data.get("etag"),
                html_link=event_data.get("htmlLink"),
            )

        except Exception as e:
            logger.error(f"Error parsing event data: {e}")
            return None

    def _get_calendar_name(self, calendar_id: str, account_email: str) -> str:
        """Get calendar name from calendar ID and account email."""
        # Try to find the calendar name from stored preferences
        accounts = self.get_all_google_accounts()
        for account in accounts:
            if account["email"] == account_email:
                calendars = self.get_calendars_for_account(account["user_id"])
                for calendar in calendars:
                    if calendar.get("id") == calendar_id:
                        return calendar.get("summary", "Unknown Calendar")

        # Fallback - if it's the primary calendar, use the email
        if calendar_id == account_email:
            return f"Primary ({account_email})"

        return "Unknown Calendar"

    def fetch_events_multi_account(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results_per_calendar: Optional[int] = None,
        filter_calendars: Optional[List[str]] = None,
        exclude_calendars: Optional[List[str]] = None,
    ) -> List[CalendarEvent]:
        """Fetch events from all calendars across all connected Google accounts."""
        all_events = []
        accounts = self.get_all_google_accounts()

        if not accounts:
            logger.warning("No Google accounts connected")
            return []

        # Use ThreadPoolExecutor for concurrent fetching
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_account = {}

            for account in accounts:
                if not account["is_valid"]:
                    logger.warning(f"Skipping invalid account: {account['email']}")
                    continue

                user_id = account["user_id"]
                calendars = self.get_calendars_for_account(user_id)

                for calendar in calendars:
                    calendar_id = calendar.get("id")
                    if not calendar_id:
                        continue

                    # Apply calendar filters
                    if filter_calendars and calendar_id not in filter_calendars:
                        continue
                    if exclude_calendars and calendar_id in exclude_calendars:
                        continue

                    # Submit the fetch task
                    future = executor.submit(
                        self.fetch_events_from_calendar,
                        user_id,
                        calendar_id,
                        start_time,
                        end_time,
                        max_results_per_calendar,
                    )
                    future_to_account[future] = {
                        "account": account,
                        "calendar": calendar,
                    }

            # Collect results as they complete
            for future in as_completed(future_to_account):
                try:
                    events = future.result()
                    all_events.extend(events)
                    account_info = future_to_account[future]["account"]
                    calendar_info = future_to_account[future]["calendar"]
                    logger.info(
                        f"Fetched {len(events)} events from {calendar_info.get('summary', 'Unknown')} "
                        f"({account_info['email']})"
                    )
                except Exception as e:
                    account_info = future_to_account[future]["account"]
                    calendar_info = future_to_account[future]["calendar"]
                    logger.error(
                        f"Error fetching from {calendar_info.get('summary', 'Unknown')} "
                        f"({account_info['email']}): {e}"
                    )

        # Sort events by start time
        all_events.sort(
            key=lambda e: e.start_time or datetime.min.replace(tzinfo=timezone.utc)
        )

        logger.info(f"Total events fetched from all accounts: {len(all_events)}")
        return all_events


class CalendarAnalyzer:
    """Analyzes calendar events for insights and patterns."""

    def __init__(self):
        """Initialize the analyzer."""
        pass

    def analyze_events(self, events: List[CalendarEvent]) -> CalendarSummary:
        """Analyze a list of calendar events and return summary statistics."""
        if not events:
            return CalendarSummary(
                total_events=0,
                events_by_calendar={},
                events_by_account={},
                events_by_day={},
                total_duration_minutes=0,
                average_event_duration=None,
                busiest_day=None,
                busiest_account=None,
                busiest_calendar=None,
                upcoming_events=0,
                past_events=0,
                all_day_events=0,
                working_hours_events=0,
                evening_events=0,
                weekend_events=0,
            )

        # Initialize counters
        events_by_calendar = defaultdict(int)
        events_by_account = defaultdict(int)
        events_by_day = defaultdict(int)
        total_duration = 0
        duration_count = 0
        upcoming_count = 0
        past_count = 0
        all_day_count = 0
        working_hours_count = 0
        evening_count = 0
        weekend_count = 0

        for event in events:
            # Count by calendar and account
            events_by_calendar[f"{event.calendar_name} ({event.account_email})"] += 1
            events_by_account[event.account_email] += 1

            # Count by day
            day_key = event.start_time.strftime("%Y-%m-%d")
            events_by_day[day_key] += 1

            # Duration analysis
            if event.duration_minutes:
                total_duration += event.duration_minutes
                duration_count += 1

            # Time-based categorization
            if event.is_upcoming:
                upcoming_count += 1
            elif event.is_past:
                past_count += 1

            if event.all_day:
                all_day_count += 1

            # Working hours (9 AM - 5 PM on weekdays)
            if not event.all_day and event.start_time:
                hour = event.start_time.hour
                weekday = event.start_time.weekday()  # 0 = Monday, 6 = Sunday

                if weekday >= 5:  # Weekend (Saturday = 5, Sunday = 6)
                    weekend_count += 1
                elif 9 <= hour < 17:  # 9 AM - 5 PM
                    working_hours_count += 1
                elif hour >= 17:  # After 5 PM
                    evening_count += 1

        # Calculate averages and identify busiest periods
        average_duration = (
            total_duration / duration_count if duration_count > 0 else None
        )
        busiest_day = (
            max(events_by_day.items(), key=lambda x: x[1])[0] if events_by_day else None
        )
        busiest_account = (
            max(events_by_account.items(), key=lambda x: x[1])[0]
            if events_by_account
            else None
        )
        busiest_calendar = (
            max(events_by_calendar.items(), key=lambda x: x[1])[0]
            if events_by_calendar
            else None
        )

        return CalendarSummary(
            total_events=len(events),
            events_by_calendar=dict(events_by_calendar),
            events_by_account=dict(events_by_account),
            events_by_day=dict(events_by_day),
            total_duration_minutes=total_duration,
            average_event_duration=average_duration,
            busiest_day=busiest_day,
            busiest_account=busiest_account,
            busiest_calendar=busiest_calendar,
            upcoming_events=upcoming_count,
            past_events=past_count,
            all_day_events=all_day_count,
            working_hours_events=working_hours_count,
            evening_events=evening_count,
            weekend_events=weekend_count,
        )

    def get_past_week_accomplishments(
        self,
        events: List[CalendarEvent],
        accomplishment_keywords: Optional[List[str]] = None,
    ) -> List[CalendarEvent]:
        """Identify events from the past week that represent accomplishments."""
        if not accomplishment_keywords:
            accomplishment_keywords = [
                "meeting",
                "presentation",
                "demo",
                "review",
                "project",
                "milestone",
                "delivery",
                "launch",
                "completion",
                "training",
                "workshop",
                "conference",
                "interview",
                "onboarding",
                "standup",
                "sync",
                "planning",
                "retrospective",
                "deployment",
                "release",
                "client",
                "customer",
                "stakeholder",
            ]

        # Get date range for past week
        today = datetime.now().date()
        start_of_week = today - timedelta(days=7)

        past_week_events = []
        for event in events:
            # Check if event is in the past week
            if event.start_time and start_of_week <= event.start_time.date() <= today:
                # Check if event represents an accomplishment
                if self._is_accomplishment_event(event, accomplishment_keywords):
                    past_week_events.append(event)

        # Sort by start time (most recent first)
        past_week_events.sort(key=lambda e: e.start_time, reverse=True)
        return past_week_events

    def _is_accomplishment_event(
        self, event: CalendarEvent, keywords: List[str]
    ) -> bool:
        """Check if an event represents an accomplishment based on keywords."""
        # Combine summary and description for searching
        text_to_search = (event.summary + " " + (event.description or "")).lower()

        # Check for accomplishment keywords
        for keyword in keywords:
            if keyword.lower() in text_to_search:
                return True

        # Additional heuristics
        # Events with multiple attendees (collaborative work)
        if len(event.attendees) >= 3:
            return True

        # Events longer than 30 minutes (substantial meetings)
        if event.duration_minutes and event.duration_minutes >= 30:
            return True

        return False

    def analyze_availability(
        self,
        events: List[CalendarEvent],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        working_hours_start: int = 9,
        working_hours_end: int = 17,
        include_weekends: bool = False,
    ) -> Dict[str, Any]:
        """Analyze availability windows based on existing calendar events."""
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=7)  # Next week by default

        # Filter events to the specified date range
        relevant_events = [
            event
            for event in events
            if event.start_time
            and start_date <= event.start_time <= end_date
            and event.status == "confirmed"
            and event.transparency == "opaque"  # Only consider "busy" events
        ]

        # Generate availability analysis
        availability_analysis = {
            "analysis_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "busy_periods": [],
            "free_periods": [],
            "daily_availability": {},
            "total_busy_hours": 0,
            "total_free_hours": 0,
            "busiest_days": [],
            "lightest_days": [],
        }

        # Process each day in the range
        current_date = start_date.date()
        end_analysis_date = end_date.date()
        daily_busy_minutes = {}

        while current_date <= end_analysis_date:
            # Skip weekends if not included
            if not include_weekends and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            # Get events for this day
            day_events = [
                event
                for event in relevant_events
                if event.start_time.date() == current_date and not event.all_day
            ]

            # Calculate busy periods for this day
            busy_periods = []
            total_busy_minutes = 0

            for event in day_events:
                if event.duration_minutes:
                    # Constrain to working hours if specified
                    event_start = event.start_time.time()
                    event_end = event.end_time.time()

                    working_start = datetime.min.time().replace(
                        hour=working_hours_start
                    )
                    working_end = datetime.min.time().replace(hour=working_hours_end)

                    # Check if event overlaps with working hours
                    if event_start < working_end and event_end > working_start:
                        # Calculate overlap
                        overlap_start = max(event_start, working_start)
                        overlap_end = min(event_end, working_end)

                        overlap_minutes = (
                            datetime.combine(current_date, overlap_end)
                            - datetime.combine(current_date, overlap_start)
                        ).total_seconds() / 60

                        total_busy_minutes += overlap_minutes
                        busy_periods.append(
                            {
                                "start": overlap_start.strftime("%H:%M"),
                                "end": overlap_end.strftime("%H:%M"),
                                "event_summary": event.summary,
                                "duration_minutes": overlap_minutes,
                            }
                        )

            # Calculate total working minutes for the day
            total_working_minutes = (working_hours_end - working_hours_start) * 60
            free_minutes = total_working_minutes - total_busy_minutes

            daily_busy_minutes[current_date.isoformat()] = total_busy_minutes
            availability_analysis["daily_availability"][current_date.isoformat()] = {
                "busy_minutes": total_busy_minutes,
                "free_minutes": max(0, free_minutes),
                "busy_periods": busy_periods,
                "availability_percentage": max(0, free_minutes)
                / total_working_minutes
                * 100,
            }

            availability_analysis["total_busy_hours"] += total_busy_minutes / 60
            availability_analysis["total_free_hours"] += max(0, free_minutes) / 60

            current_date += timedelta(days=1)

        # Identify busiest and lightest days
        if daily_busy_minutes:
            sorted_days = sorted(daily_busy_minutes.items(), key=lambda x: x[1])
            availability_analysis["lightest_days"] = [day for day, _ in sorted_days[:3]]
            availability_analysis["busiest_days"] = [day for day, _ in sorted_days[-3:]]

        return availability_analysis

    def find_free_time_slots(
        self,
        events: List[CalendarEvent],
        start_date: datetime,
        end_date: datetime,
        slot_duration_minutes: int = 60,
        working_hours_start: int = 9,
        working_hours_end: int = 17,
        include_weekends: bool = False,
    ) -> List[Dict[str, Any]]:
        """Find available time slots of specified duration."""
        free_slots = []

        current_date = start_date.date()
        end_analysis_date = end_date.date()

        while current_date <= end_analysis_date:
            # Skip weekends if not included
            if not include_weekends and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            # Get busy periods for this day
            day_events = [
                event
                for event in events
                if (
                    event.start_time.date() == current_date
                    and not event.all_day
                    and event.status == "confirmed"
                    and event.transparency == "opaque"
                )
            ]

            # Sort events by start time
            day_events.sort(key=lambda e: e.start_time)

            # Find gaps between events
            day_start = datetime.combine(
                current_date, datetime.min.time().replace(hour=working_hours_start)
            )
            day_end = datetime.combine(
                current_date, datetime.min.time().replace(hour=working_hours_end)
            )

            # Check for slot at the beginning of the day
            if not day_events or day_events[0].start_time > day_start + timedelta(
                minutes=slot_duration_minutes
            ):
                first_event_start = day_events[0].start_time if day_events else day_end
                available_minutes = (first_event_start - day_start).total_seconds() / 60

                if available_minutes >= slot_duration_minutes:
                    free_slots.append(
                        {
                            "start": day_start,
                            "end": min(
                                day_start + timedelta(minutes=slot_duration_minutes),
                                first_event_start,
                            ),
                            "duration_minutes": min(
                                slot_duration_minutes, available_minutes
                            ),
                            "type": "morning_slot",
                        }
                    )

            # Check gaps between events
            for i in range(len(day_events) - 1):
                current_event_end = day_events[i].end_time
                next_event_start = day_events[i + 1].start_time

                gap_minutes = (
                    next_event_start - current_event_end
                ).total_seconds() / 60

                if gap_minutes >= slot_duration_minutes:
                    free_slots.append(
                        {
                            "start": current_event_end,
                            "end": min(
                                current_event_end
                                + timedelta(minutes=slot_duration_minutes),
                                next_event_start,
                            ),
                            "duration_minutes": min(slot_duration_minutes, gap_minutes),
                            "type": "between_events",
                        }
                    )

            # Check for slot at the end of the day
            if day_events:
                last_event_end = day_events[-1].end_time
                if last_event_end < day_end - timedelta(minutes=slot_duration_minutes):
                    available_minutes = (day_end - last_event_end).total_seconds() / 60

                    if available_minutes >= slot_duration_minutes:
                        free_slots.append(
                            {
                                "start": last_event_end,
                                "end": min(
                                    last_event_end
                                    + timedelta(minutes=slot_duration_minutes),
                                    day_end,
                                ),
                                "duration_minutes": min(
                                    slot_duration_minutes, available_minutes
                                ),
                                "type": "evening_slot",
                            }
                        )

            current_date += timedelta(days=1)

        return free_slots


# High-level convenience functions for the weekly review agent


def get_all_calendar_events(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    max_results_per_calendar: Optional[int] = None,
) -> List[CalendarEvent]:
    """Get all calendar events from all connected Google accounts."""
    fetcher = CalendarDataFetcher()
    return fetcher.fetch_events_multi_account(
        start_time=start_time,
        end_time=end_time,
        max_results_per_calendar=max_results_per_calendar,
    )


def get_past_week_accomplishments(
    accomplishment_keywords: Optional[List[str]] = None,
) -> List[CalendarEvent]:
    """Get accomplishment events from the past week across all accounts."""
    # Get events from the past 2 weeks to ensure we capture the full past week
    start_time = datetime.now() - timedelta(days=14)
    end_time = datetime.now()

    events = get_all_calendar_events(start_time=start_time, end_time=end_time)

    analyzer = CalendarAnalyzer()
    return analyzer.get_past_week_accomplishments(events, accomplishment_keywords)


def analyze_upcoming_availability(
    days_ahead: int = 7,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
    include_weekends: bool = False,
) -> Dict[str, Any]:
    """Analyze availability for the upcoming period."""
    start_time = datetime.now()
    end_time = start_time + timedelta(days=days_ahead)

    events = get_all_calendar_events(start_time=start_time, end_time=end_time)

    analyzer = CalendarAnalyzer()
    return analyzer.analyze_availability(
        events,
        start_time,
        end_time,
        working_hours_start,
        working_hours_end,
        include_weekends,
    )


def find_next_available_slots(
    slot_duration_minutes: int = 60,
    days_ahead: int = 7,
    max_slots: int = 10,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
    include_weekends: bool = False,
) -> List[Dict[str, Any]]:
    """Find the next available time slots of specified duration."""
    start_time = datetime.now()
    end_time = start_time + timedelta(days=days_ahead)

    events = get_all_calendar_events(start_time=start_time, end_time=end_time)

    analyzer = CalendarAnalyzer()
    slots = analyzer.find_free_time_slots(
        events,
        start_time,
        end_time,
        slot_duration_minutes,
        working_hours_start,
        working_hours_end,
        include_weekends,
    )

    return slots[:max_slots]


def get_calendar_summary(
    start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
) -> CalendarSummary:
    """Get a comprehensive summary of calendar events."""
    events = get_all_calendar_events(start_time=start_time, end_time=end_time)
    analyzer = CalendarAnalyzer()
    return analyzer.analyze_events(events)


def test_calendar_connection() -> Dict[str, Any]:
    """Test calendar connections and return status information."""
    fetcher = CalendarDataFetcher()
    accounts = fetcher.get_all_google_accounts()

    result = {
        "connected_accounts": len(accounts),
        "accounts": [],
        "total_calendars": 0,
        "connection_status": "healthy" if accounts else "no_accounts",
    }

    for account in accounts:
        account_info = {
            "email": account["email"],
            "is_valid": account["is_valid"],
            "calendars": [],
        }

        if account["is_valid"]:
            calendars = fetcher.get_calendars_for_account(account["user_id"])
            account_info["calendars"] = [
                {
                    "id": cal.get("id"),
                    "name": cal.get("summary", "Unknown"),
                    "enabled": cal.get("enabled", True),
                }
                for cal in calendars
            ]
            result["total_calendars"] += len(calendars)

        result["accounts"].append(account_info)

    return result
