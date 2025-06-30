"""
Todoist API integration tools for weekly review agent.

This module provides functions to interact with the Todoist REST API v2 for
fetching and managing tasks, projects, and labels. It integrates with the
existing OAuth infrastructure to handle authentication.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union, Callable
import requests
from requests.exceptions import RequestException, Timeout
import json
import time
from functools import wraps
from threading import Lock
from dataclasses import dataclass
from enum import Enum

from common.oauth_manager import oauth_manager
from service.oauth_service import OAuthToken

# Configure logging
logger = logging.getLogger(__name__)

# Todoist API configuration
TODOIST_API_BASE = "https://api.todoist.com/rest/v2"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3

# ==================== FALLBACK AND RESILIENCE CONFIGURATION ====================

# Circuit breaker configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5  # failures before opening circuit
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 300  # seconds (5 minutes)
CIRCUIT_BREAKER_SUCCESS_THRESHOLD = 3  # successes needed to close circuit

# Cache configuration
CACHE_DEFAULT_TTL = 300  # seconds (5 minutes)
CACHE_OFFLINE_TTL = 3600  # seconds (1 hour) - longer cache for offline scenarios
MAX_CACHE_SIZE = 1000  # maximum number of cached items

# Health check configuration
HEALTH_CHECK_INTERVAL = 60  # seconds
HEALTH_CHECK_TIMEOUT = 10  # seconds


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit breaker tripped, failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CacheEntry:
    """Cache entry with TTL and metadata."""

    data: Any
    timestamp: float
    ttl: int
    key: str


class CircuitBreaker:
    """Circuit breaker implementation for API resilience."""

    def __init__(
        self,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout: int = CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        success_threshold: int = CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0
        self.lock = Lock()

    def can_execute(self) -> bool:
        """Check if circuit allows execution."""
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    return True
                return False
            else:  # HALF_OPEN
                return True

    def record_success(self):
        """Record a successful operation."""
        with self.lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    logger.info("Circuit breaker CLOSED - service recovered")

    def record_failure(self):
        """Record a failed operation."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker OPEN - service degraded after {self.failure_count} failures"
                )


class APICache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        with self.lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]
            if time.time() - entry.timestamp > entry.ttl:
                del self.cache[key]
                return None

            logger.debug(f"Cache hit for key: {key}")
            return entry.data

    def set(self, key: str, data: Any, ttl: int = CACHE_DEFAULT_TTL):
        """Set cached value with TTL."""
        with self.lock:
            # Remove expired entries if cache is full
            if len(self.cache) >= self.max_size:
                self._cleanup_expired()

            # If still full, remove oldest entries
            if len(self.cache) >= self.max_size:
                oldest_key = min(
                    self.cache.keys(), key=lambda k: self.cache[k].timestamp
                )
                del self.cache[oldest_key]

            self.cache[key] = CacheEntry(
                data=data, timestamp=time.time(), ttl=ttl, key=key
            )
            logger.debug(f"Cached data for key: {key} (TTL: {ttl}s)")

    def _cleanup_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self.cache.items()
            if current_time - entry.timestamp > entry.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            logger.debug("Cache cleared")


class HealthMonitor:
    """Health monitoring for Todoist API."""

    def __init__(self):
        self.last_check = 0
        self.is_healthy = True
        self.consecutive_failures = 0
        self.lock = Lock()

    def check_health(self, user_id: str) -> bool:
        """Check API health with caching."""
        current_time = time.time()

        with self.lock:
            # Use cached health status if recent
            if current_time - self.last_check < HEALTH_CHECK_INTERVAL:
                return self.is_healthy

            self.last_check = current_time

        try:
            # Simple health check - try to get user info
            response = requests.get(
                f"{TODOIST_API_BASE}/projects",
                headers={
                    "Authorization": f"Bearer {_get_valid_token(user_id).access_token}"
                },
                timeout=HEALTH_CHECK_TIMEOUT,
            )

            is_healthy = response.status_code in [
                200,
                401,
                403,
            ]  # Service is up even if auth fails

            with self.lock:
                if is_healthy:
                    self.consecutive_failures = 0
                    if not self.is_healthy:
                        logger.info("Todoist API health check: Service recovered")
                else:
                    self.consecutive_failures += 1
                    if self.is_healthy and self.consecutive_failures >= 3:
                        logger.warning("Todoist API health check: Service appears down")

                self.is_healthy = is_healthy
                return self.is_healthy

        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            with self.lock:
                self.consecutive_failures += 1
                if self.is_healthy and self.consecutive_failures >= 3:
                    logger.warning("Todoist API health check: Service appears down")
                self.is_healthy = False
                return False


# Global instances
circuit_breaker = CircuitBreaker()
api_cache = APICache()
health_monitor = HealthMonitor()


def with_fallback(
    cache_key_func: Optional[Callable] = None,
    cache_ttl: int = CACHE_DEFAULT_TTL,
    fallback_data: Optional[Any] = None,
    enable_circuit_breaker: bool = True,
):
    """
    Decorator to add fallback mechanisms to API functions.

    Args:
        cache_key_func: Function to generate cache key from args
        cache_ttl: Cache time-to-live in seconds
        fallback_data: Default data to return if all else fails
        enable_circuit_breaker: Whether to use circuit breaker
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key if function provided
            cache_key = None
            if cache_key_func:
                try:
                    cache_key = cache_key_func(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"Failed to generate cache key: {e}")

            # Check circuit breaker
            if enable_circuit_breaker and not circuit_breaker.can_execute():
                logger.warning(
                    f"Circuit breaker OPEN - using cached data for {func.__name__}"
                )
                if cache_key:
                    cached_data = api_cache.get(cache_key)
                    if cached_data is not None:
                        return cached_data

                if fallback_data is not None:
                    logger.info(f"Using fallback data for {func.__name__}")
                    return fallback_data

                raise TodoistConnectionError(
                    "Service temporarily unavailable (circuit breaker open) and no cached data available"
                )

            # Try to get from cache first
            if cache_key:
                cached_data = api_cache.get(cache_key)
                if cached_data is not None:
                    return cached_data

            # Execute the function
            try:
                result = func(*args, **kwargs)

                # Record success and cache result
                if enable_circuit_breaker:
                    circuit_breaker.record_success()

                if cache_key and result is not None:
                    api_cache.set(cache_key, result, cache_ttl)

                return result

            except (TodoistConnectionError, TodoistAPIError) as e:
                # Record failure
                if enable_circuit_breaker:
                    circuit_breaker.record_failure()

                # Try to use cached data with extended TTL
                if cache_key:
                    # Check for expired cache that we can still use as fallback
                    with api_cache.lock:
                        if cache_key in api_cache.cache:
                            entry = api_cache.cache[cache_key]
                            age = time.time() - entry.timestamp
                            if (
                                age <= CACHE_OFFLINE_TTL
                            ):  # Use stale cache for offline scenarios
                                logger.warning(
                                    f"Using stale cached data for {func.__name__} (age: {age:.0f}s)"
                                )
                                return entry.data

                # Use fallback data if available
                if fallback_data is not None:
                    logger.warning(f"Using fallback data for {func.__name__}: {e}")
                    return fallback_data

                # Re-raise the exception
                raise

        return wrapper

    return decorator


def _generate_cache_key(endpoint: str, user_id: str, **params) -> str:
    """Generate cache key for API requests."""
    param_str = json.dumps(sorted(params.items())) if params else ""
    return f"todoist:{user_id}:{endpoint}:{hash(param_str)}"


def _projects_cache_key(user_id: str) -> str:
    """Cache key for projects."""
    return f"todoist:{user_id}:projects"


def _tasks_cache_key(user_id: str, **params) -> str:
    """Cache key for tasks with parameters."""
    return _generate_cache_key("tasks", user_id, **params)


def _labels_cache_key(user_id: str) -> str:
    """Cache key for labels."""
    return f"todoist:{user_id}:labels"


class TodoistAPIError(Exception):
    """Custom exception for Todoist API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class TodoistConnectionError(TodoistAPIError):
    """Exception for Todoist connection/network errors."""
    pass


class TodoistAuthenticationError(TodoistAPIError):
    """Exception for Todoist authentication errors."""
    pass


def _get_valid_token(user_id: str) -> OAuthToken:
    """
    Get a valid Todoist OAuth token for the user.

    Args:
        user_id: User identifier

    Returns:
        OAuthToken: Valid OAuth token

    Raises:
        TodoistAuthenticationError: If no valid token is available or token is expired.
            Todoist does not support refresh tokens; user must re-authenticate.
    """
    token = oauth_manager.get_valid_token("todoist", user_id)

    if not token:
        raise TodoistAuthenticationError(
            f"No valid Todoist token found for user {user_id}. "
            "Your Todoist session has expired or is invalid. "
            "Todoist does NOT support refresh tokens. "
            "Please re-authenticate with Todoist via the OAuth flow to continue."
        )
    return token


def _make_api_request(
    endpoint: str,
    user_id: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    Make an authenticated request to the Todoist API.

    Args:
        endpoint: API endpoint (relative to base URL)
        user_id: User identifier for authentication
        method: HTTP method (GET, POST, PUT, DELETE)
        params: Query parameters
        data: Request body data
        timeout: Request timeout in seconds

    Returns:
        Dict containing the API response

    Raises:
        TodoistAPIError: For API-related errors
        TodoistConnectionError: For network/connection errors
        TodoistAuthenticationError: For authentication errors
    """
    token = _get_valid_token(user_id)

    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "Content-Type": "application/json"
    }

    url = f"{TODOIST_API_BASE}/{endpoint.lstrip('/')}"

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=timeout
            )

            # Handle different response status codes
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as e:
                    logger.error(f"Invalid JSON response from Todoist API: {e}")
                    raise TodoistAPIError(
                        "Invalid JSON response from Todoist API",
                        status_code=response.status_code
                    )
            elif response.status_code == 401:
                raise TodoistAuthenticationError(
                    "Todoist authentication failed. Token may be invalid or expired.",
                    status_code=response.status_code
                )
            elif response.status_code == 403:
                raise TodoistAuthenticationError(
                    "Access forbidden. Check Todoist API permissions.",
                    status_code=response.status_code
                )
            elif response.status_code == 404:
                raise TodoistAPIError(
                    f"Todoist API endpoint not found: {endpoint}",
                    status_code=response.status_code
                )
            elif response.status_code == 429:
                # Rate limiting - wait and retry
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Rate limited by Todoist API. Waiting {wait_time}s before retry."
                    )
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    raise TodoistAPIError(
                        "Todoist API rate limit exceeded. Please try again later.",
                        status_code=response.status_code
                    )
            else:
                # Other HTTP errors
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", f"HTTP {response.status_code}")
                except ValueError:
                    error_message = f"HTTP {response.status_code}: {response.text[:200]}"

                raise TodoistAPIError(
                    f"Todoist API error: {error_message}",
                    status_code=response.status_code,
                    response_data=error_data if 'error_data' in locals() else None
                )

        except Timeout:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Todoist API request timeout (attempt {attempt + 1}). Retrying...")
                continue
            raise TodoistConnectionError(f"Todoist API request timed out after {timeout}s")

        except RequestException as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Network error contacting Todoist API (attempt {attempt + 1}): {e}")
                continue
            raise TodoistConnectionError(f"Failed to connect to Todoist API: {e}")

    # This should never be reached due to the exception handling above
    raise TodoistConnectionError("Unexpected error in API request")


def get_all_projects(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all projects from Todoist.

    Args:
        user_id: User identifier for authentication

    Returns:
        List of project dictionaries with details like id, name, color, etc.

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Fetching all projects for user {user_id}")
        projects = _make_api_request("projects", user_id)

        logger.info(f"Successfully fetched {len(projects)} projects for user {user_id}")
        return projects

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching projects for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching projects: {e}")


def get_project_by_id(user_id: str, project_id: str) -> Dict[str, Any]:
    """
    Fetch a specific project by ID.

    Args:
        user_id: User identifier for authentication
        project_id: Todoist project ID

    Returns:
        Project dictionary with details

    Raises:
        TodoistAPIError: If the project is not found or API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Fetching project {project_id} for user {user_id}")
        project = _make_api_request(f"projects/{project_id}", user_id)

        logger.info(f"Successfully fetched project {project_id} for user {user_id}")
        return project

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching project {project_id} for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching project: {e}")


def get_all_tasks(
    user_id: str,
    project_id: Optional[str] = None,
    label: Optional[str] = None,
    filter_expr: Optional[str] = None,
    lang: str = "en"
) -> List[Dict[str, Any]]:
    """
    Fetch tasks from Todoist with optional filtering.

    Args:
        user_id: User identifier for authentication
        project_id: Optional project ID to filter tasks
        label: Optional label name to filter tasks
        filter_expr: Optional Todoist filter expression (e.g., "today", "overdue")
        lang: Language for dates (default: "en")

    Returns:
        List of task dictionaries with details like id, content, project_id, etc.

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        # Build query parameters
        params = {"lang": lang}
        if project_id:
            params["project_id"] = project_id
        if label:
            params["label"] = label
        if filter_expr:
            params["filter"] = filter_expr

        logger.info(f"Fetching tasks for user {user_id} with params: {params}")
        tasks = _make_api_request("tasks", user_id, params=params)

        logger.info(f"Successfully fetched {len(tasks)} tasks for user {user_id}")
        return tasks

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching tasks for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching tasks: {e}")


def get_task_by_id(user_id: str, task_id: str) -> Dict[str, Any]:
    """
    Fetch a specific task by ID.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID

    Returns:
        Task dictionary with details

    Raises:
        TodoistAPIError: If the task is not found or API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Fetching task {task_id} for user {user_id}")
        task = _make_api_request(f"tasks/{task_id}", user_id)

        logger.info(f"Successfully fetched task {task_id} for user {user_id}")
        return task

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching task {task_id} for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching task: {e}")


def get_all_labels(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all labels from Todoist.

    Args:
        user_id: User identifier for authentication

    Returns:
        List of label dictionaries with details like id, name, color, etc.

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Fetching all labels for user {user_id}")
        labels = _make_api_request("labels", user_id)

        logger.info(f"Successfully fetched {len(labels)} labels for user {user_id}")
        return labels

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching labels for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching labels: {e}")


def get_label_by_id(user_id: str, label_id: str) -> Dict[str, Any]:
    """
    Fetch a specific label by ID.

    Args:
        user_id: User identifier for authentication
        label_id: Todoist label ID

    Returns:
        Label dictionary with details

    Raises:
        TodoistAPIError: If the label is not found or API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Fetching label {label_id} for user {user_id}")
        label = _make_api_request(f"labels/{label_id}", user_id)

        logger.info(f"Successfully fetched label {label_id} for user {user_id}")
        return label

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching label {label_id} for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching label: {e}")


def get_tasks_by_filter(
    user_id: str, filter_expression: str, lang: str = "en"
) -> List[Dict[str, Any]]:
    """
    Fetch tasks using Todoist's powerful filter expressions.

    Common filter examples:
    - "today" - Tasks due today
    - "overdue" - Overdue tasks
    - "7 days" - Tasks due in the next 7 days
    - "p1" - Priority 1 tasks
    - "#Work" - Tasks in Work project
    - "@calls" - Tasks with 'calls' label

    Args:
        user_id: User identifier for authentication
        filter_expression: Todoist filter expression
        lang: Language for dates (default: "en")

    Returns:
        List of task dictionaries matching the filter

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        params = {
            "filter": filter_expression,
            "lang": lang
        }

        logger.info(f"Fetching tasks for user {user_id} with filter: {filter_expression}")
        tasks = _make_api_request("tasks", user_id, params=params)

        logger.info(f"Successfully fetched {len(tasks)} tasks for user {user_id} with filter")
        return tasks

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching filtered tasks for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching filtered tasks: {e}")


def get_completed_tasks(
    user_id: str,
    project_id: Optional[str] = None,
    since: Optional[Union[str, date, datetime]] = None,
    until: Optional[Union[str, date, datetime]] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Fetch completed tasks (requires Todoist Pro).

    Args:
        user_id: User identifier for authentication
        project_id: Optional project ID to filter completed tasks
        since: Optional start date (ISO format string, date, or datetime)
        until: Optional end date (ISO format string, date, or datetime)
        limit: Maximum number of tasks to return (default: 50, max: 200)

    Returns:
        Dictionary containing completed tasks and pagination info

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        params = {"limit": min(limit, 200)}  # Respect API maximum

        if project_id:
            params["project_id"] = project_id

        if since:
            if isinstance(since, (date, datetime)):
                params["since"] = since.isoformat()
            else:
                params["since"] = since

        if until:
            if isinstance(until, (date, datetime)):
                params["until"] = until.isoformat()
            else:
                params["until"] = until

        logger.info(f"Fetching completed tasks for user {user_id} with params: {params}")
        result = _make_api_request("tasks/completed", user_id, params=params)

        items = result.get("items", [])
        logger.info(f"Successfully fetched {len(items)} completed tasks for user {user_id}")
        return result

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching completed tasks for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching completed tasks: {e}")


def test_connection(user_id: str) -> bool:
    """
    Test the Todoist API connection and authentication.

    Args:
        user_id: User identifier for authentication

    Returns:
        True if connection is successful, False otherwise
    """
    try:
        # Try to fetch user info as a simple test
        _make_api_request("user", user_id)
        logger.info(f"Todoist connection test successful for user {user_id}")
        return True

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError) as e:
        logger.warning(f"Todoist connection test failed for user {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error testing Todoist connection for user {user_id}: {e}")
        return False


def get_user_info(user_id: str) -> Dict[str, Any]:
    """
    Get Todoist user information.

    Args:
        user_id: User identifier for authentication

    Returns:
        User information dictionary

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Fetching user info for user {user_id}")
        user_info = _make_api_request("user", user_id)

        logger.info(f"Successfully fetched user info for user {user_id}")
        return user_info

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching user info for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error fetching user info: {e}")


# Task Update and Management Functions


def complete_task(user_id: str, task_id: str) -> bool:
    """
    Mark a task as completed in Todoist.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID to complete

    Returns:
        True if task was successfully completed, False otherwise

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Completing task {task_id} for user {user_id}")

        # Todoist API uses POST to close a task
        _make_api_request(f"tasks/{task_id}/close", user_id, method="POST")

        logger.info(f"Successfully completed task {task_id} for user {user_id}")
        return True

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error completing task {task_id} for user {user_id}: {e}"
        )
        raise TodoistAPIError(f"Unexpected error completing task: {e}")


def reopen_task(user_id: str, task_id: str) -> bool:
    """
    Reopen a completed task in Todoist.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID to reopen

    Returns:
        True if task was successfully reopened, False otherwise

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Reopening task {task_id} for user {user_id}")

        # Todoist API uses POST to reopen a task
        _make_api_request(f"tasks/{task_id}/reopen", user_id, method="POST")

        logger.info(f"Successfully reopened task {task_id} for user {user_id}")
        return True

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error reopening task {task_id} for user {user_id}: {e}"
        )
        raise TodoistAPIError(f"Unexpected error reopening task: {e}")


def create_task(
    user_id: str,
    content: str,
    project_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    order: Optional[int] = None,
    labels: Optional[List[str]] = None,
    priority: Optional[int] = None,
    due_string: Optional[str] = None,
    due_date: Optional[str] = None,
    due_datetime: Optional[str] = None,
    due_lang: Optional[str] = None,
    assignee_id: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new task in Todoist.

    Args:
        user_id: User identifier for authentication
        content: Task content/title (required)
        project_id: Project ID to add task to
        parent_id: Parent task ID for creating subtasks
        order: Task order in project
        labels: List of label names
        priority: Task priority (1-4, where 4 is highest)
        due_string: Due date in natural language (e.g., "tomorrow", "next monday")
        due_date: Due date in YYYY-MM-DD format
        due_datetime: Due datetime in RFC3339 format
        due_lang: Language for due_string (default: "en")
        assignee_id: User ID to assign task to (for shared projects)
        description: Task description

    Returns:
        Created task dictionary

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Creating task '{content}' for user {user_id}")

        # Build task data
        task_data = {"content": content}

        if project_id:
            task_data["project_id"] = project_id
        if parent_id:
            task_data["parent_id"] = parent_id
        if order is not None:
            task_data["order"] = order
        if labels:
            task_data["labels"] = labels
        if priority is not None:
            # Validate priority range
            if priority < 1 or priority > 4:
                raise ValueError("Priority must be between 1-4")
            task_data["priority"] = priority
        if due_string:
            task_data["due_string"] = due_string
        if due_date:
            task_data["due_date"] = due_date
        if due_datetime:
            task_data["due_datetime"] = due_datetime
        if due_lang:
            task_data["due_lang"] = due_lang
        if assignee_id:
            task_data["assignee_id"] = assignee_id
        if description:
            task_data["description"] = description

        task = _make_api_request("tasks", user_id, method="POST", data=task_data)

        logger.info(f"Successfully created task {task.get('id')} for user {user_id}")
        return task

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except ValueError as e:
        raise TodoistAPIError(f"Invalid task data: {e}")
    except Exception as e:
        logger.error(f"Unexpected error creating task for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error creating task: {e}")


def update_task(
    user_id: str,
    task_id: str,
    content: Optional[str] = None,
    description: Optional[str] = None,
    labels: Optional[List[str]] = None,
    priority: Optional[int] = None,
    due_string: Optional[str] = None,
    due_date: Optional[str] = None,
    due_datetime: Optional[str] = None,
    due_lang: Optional[str] = None,
    assignee_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update an existing task in Todoist.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID to update
        content: New task content/title
        description: New task description
        labels: New list of label names
        priority: New task priority (1-4, where 4 is highest)
        due_string: New due date in natural language
        due_date: New due date in YYYY-MM-DD format
        due_datetime: New due datetime in RFC3339 format
        due_lang: Language for due_string
        assignee_id: New assignee user ID

    Returns:
        Updated task dictionary

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Updating task {task_id} for user {user_id}")

        # Build update data with only provided fields
        update_data = {}

        if content is not None:
            update_data["content"] = content
        if description is not None:
            update_data["description"] = description
        if labels is not None:
            update_data["labels"] = labels
        if priority is not None:
            # Validate priority range
            if priority < 1 or priority > 4:
                raise ValueError("Priority must be between 1-4")
            update_data["priority"] = priority
        if due_string is not None:
            update_data["due_string"] = due_string
        if due_date is not None:
            update_data["due_date"] = due_date
        if due_datetime is not None:
            update_data["due_datetime"] = due_datetime
        if due_lang is not None:
            update_data["due_lang"] = due_lang
        if assignee_id is not None:
            update_data["assignee_id"] = assignee_id

        if not update_data:
            raise ValueError("At least one field must be provided for update")

        task = _make_api_request(
            f"tasks/{task_id}", user_id, method="POST", data=update_data
        )

        logger.info(f"Successfully updated task {task_id} for user {user_id}")
        return task

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except ValueError as e:
        raise TodoistAPIError(f"Invalid update data: {e}")
    except Exception as e:
        logger.error(
            f"Unexpected error updating task {task_id} for user {user_id}: {e}"
        )
        raise TodoistAPIError(f"Unexpected error updating task: {e}")


def delete_task(user_id: str, task_id: str) -> bool:
    """
    Delete a task from Todoist.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID to delete

    Returns:
        True if task was successfully deleted

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Deleting task {task_id} for user {user_id}")

        _make_api_request(f"tasks/{task_id}", user_id, method="DELETE")

        logger.info(f"Successfully deleted task {task_id} for user {user_id}")
        return True

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error deleting task {task_id} for user {user_id}: {e}"
        )
        raise TodoistAPIError(f"Unexpected error deleting task: {e}")


def bulk_complete_tasks(user_id: str, task_ids: List[str]) -> Dict[str, bool]:
    """
    Complete multiple tasks in Todoist.

    Args:
        user_id: User identifier for authentication
        task_ids: List of Todoist task IDs to complete

    Returns:
        Dictionary mapping task_id to success status

    Raises:
        TodoistAPIError: If any API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    results = {}

    for task_id in task_ids:
        try:
            success = complete_task(user_id, task_id)
            results[task_id] = success
        except TodoistAPIError as e:
            logger.warning(f"Failed to complete task {task_id}: {e}")
            results[task_id] = False

    logger.info(
        f"Bulk completed {sum(results.values())}/{len(task_ids)} tasks for user {user_id}"
    )
    return results


def update_task_status(user_id: str, task_id: str, completed: bool) -> bool:
    """
    Update a task's completion status.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID
        completed: True to complete the task, False to reopen it

    Returns:
        True if status was successfully updated

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        if completed:
            return complete_task(user_id, task_id)
        else:
            return reopen_task(user_id, task_id)
    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating task status for {task_id}: {e}")
        raise TodoistAPIError(f"Unexpected error updating task status: {e}")


def move_task_to_project(user_id: str, task_id: str, project_id: str) -> Dict[str, Any]:
    """
    Move a task to a different project.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID to move
        project_id: Target project ID

    Returns:
        Updated task dictionary

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Moving task {task_id} to project {project_id} for user {user_id}")

        update_data = {"project_id": project_id}
        task = _make_api_request(
            f"tasks/{task_id}", user_id, method="POST", data=update_data
        )

        logger.info(
            f"Successfully moved task {task_id} to project {project_id} for user {user_id}"
        )
        return task

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error moving task {task_id} for user {user_id}: {e}")
        raise TodoistAPIError(f"Unexpected error moving task: {e}")


def set_task_priority(user_id: str, task_id: str, priority: int) -> Dict[str, Any]:
    """
    Set a task's priority level.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID
        priority: Priority level (1-4, where 4 is highest)

    Returns:
        Updated task dictionary

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        if priority < 1 or priority > 4:
            raise ValueError("Priority must be between 1-4")

        logger.info(f"Setting task {task_id} priority to {priority} for user {user_id}")

        update_data = {"priority": priority}
        task = _make_api_request(
            f"tasks/{task_id}", user_id, method="POST", data=update_data
        )

        logger.info(
            f"Successfully set task {task_id} priority to {priority} for user {user_id}"
        )
        return task

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except ValueError as e:
        raise TodoistAPIError(f"Invalid priority value: {e}")
    except Exception as e:
        logger.error(f"Unexpected error setting task priority for {task_id}: {e}")
        raise TodoistAPIError(f"Unexpected error setting task priority: {e}")


def add_task_labels(user_id: str, task_id: str, labels: List[str]) -> Dict[str, Any]:
    """
    Add labels to a task (replaces existing labels).

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID
        labels: List of label names to set

    Returns:
        Updated task dictionary

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        logger.info(f"Setting labels {labels} for task {task_id} for user {user_id}")

        update_data = {"labels": labels}
        task = _make_api_request(
            f"tasks/{task_id}", user_id, method="POST", data=update_data
        )

        logger.info(f"Successfully set labels for task {task_id} for user {user_id}")
        return task

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error setting task labels for {task_id}: {e}")
        raise TodoistAPIError(f"Unexpected error setting task labels: {e}")


def set_task_due_date(
    user_id: str,
    task_id: str,
    due_string: Optional[str] = None,
    due_date: Optional[str] = None,
    due_datetime: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set a task's due date using various formats.

    Args:
        user_id: User identifier for authentication
        task_id: Todoist task ID
        due_string: Due date in natural language (e.g., "tomorrow", "next friday")
        due_date: Due date in YYYY-MM-DD format
        due_datetime: Due datetime in RFC3339 format

    Returns:
        Updated task dictionary

    Raises:
        TodoistAPIError: If the API request fails
        TodoistAuthenticationError: If authentication fails
        TodoistConnectionError: If network connection fails
    """
    try:
        update_data = {}

        if due_string:
            update_data["due_string"] = due_string
        elif due_date:
            update_data["due_date"] = due_date
        elif due_datetime:
            update_data["due_datetime"] = due_datetime
        else:
            raise ValueError("At least one due date parameter must be provided")

        logger.info(f"Setting due date for task {task_id} for user {user_id}")

        task = _make_api_request(
            f"tasks/{task_id}", user_id, method="POST", data=update_data
        )

        logger.info(f"Successfully set due date for task {task_id} for user {user_id}")
        return task

    except (TodoistAPIError, TodoistAuthenticationError, TodoistConnectionError):
        raise
    except ValueError as e:
        raise TodoistAPIError(f"Invalid due date parameters: {e}")
    except Exception as e:
        logger.error(f"Unexpected error setting due date for task {task_id}: {e}")
        raise TodoistAPIError(f"Unexpected error setting due date: {e}")


# ==================== RECURRING TASKS SUPPORT ====================


def is_recurring_task(task_data: Dict[str, Any]) -> bool:
    """
    Check if a task is a recurring task.

    Args:
        task_data: Task object from Todoist API

    Returns:
        bool: True if task has a recurring due date
    """
    try:
        if not task_data or not isinstance(task_data, dict):
            return False

        due_info = task_data.get("due")
        if not due_info or not isinstance(due_info, dict):
            return False

        return due_info.get("is_recurring", False)

    except Exception as e:
        logger.error(f"Error checking if task is recurring: {str(e)}")
        return False


def get_recurring_pattern(task_data: Dict[str, Any]) -> Optional[str]:
    """
    Get the recurring pattern string from a recurring task.

    Args:
        task_data: Task object from Todoist API

    Returns:
        Optional[str]: The recurring pattern string (e.g., "every day", "every week")
    """
    try:
        if not is_recurring_task(task_data):
            return None

        due_info = task_data.get("due", {})
        return due_info.get("string")

    except Exception as e:
        logger.error(f"Error getting recurring pattern: {str(e)}")
        return None


def create_recurring_task(
    content: str,
    due_string: str,
    project_id: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    labels: Optional[List[str]] = None,
    section_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a new recurring task with specified pattern.

    Args:
        content: Task content/title
        due_string: Recurring pattern (e.g., "every day", "every mon, fri", "every 3 months")
        project_id: Project ID (optional)
        description: Task description (optional)
        priority: Task priority 1-4 (optional)
        labels: List of label names (optional)
        section_id: Section ID (optional)
        parent_id: Parent task ID for subtasks (optional)
        assignee_id: Assignee user ID (optional)

    Returns:
        Optional[Dict]: Created task data or None if failed
    """
    try:
        # Validate recurring pattern
        if not _is_valid_recurring_pattern(due_string):
            logger.warning(f"Invalid recurring pattern: {due_string}")

        # Create task with due_string parameter
        task_data = create_task(
            content=content,
            project_id=project_id,
            description=description,
            priority=priority,
            labels=labels,
            section_id=section_id,
            parent_id=parent_id,
            assignee_id=assignee_id,
            due_string=due_string,
        )

        if task_data and is_recurring_task(task_data):
            logger.info(
                f"Successfully created recurring task: {content} with pattern: {due_string}"
            )
            return task_data
        else:
            logger.warning(
                f"Task created but may not be recurring as expected: {content}"
            )
            return task_data

    except Exception as e:
        logger.error(f"Error creating recurring task: {str(e)}")
        return None


def get_next_occurrence_date(task_data: Dict[str, Any]) -> Optional[str]:
    """
    Get the next occurrence date for a recurring task.

    Args:
        task_data: Recurring task object from Todoist API

    Returns:
        Optional[str]: Next occurrence date in ISO format or None
    """
    try:
        if not is_recurring_task(task_data):
            logger.warning("Task is not recurring")
            return None

        due_info = task_data.get("due", {})
        return due_info.get("date")

    except Exception as e:
        logger.error(f"Error getting next occurrence date: {str(e)}")
        return None


def complete_recurring_task(task_id: str) -> bool:
    """
    Complete a recurring task, which will automatically create the next occurrence.

    Args:
        task_id: ID of the recurring task to complete

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get task info to verify it's recurring
        task = get_task_by_id(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False

        if not is_recurring_task(task):
            logger.warning(f"Task {task_id} is not recurring")

        # Complete the task - Todoist will automatically create next occurrence
        success = complete_task(task_id)

        if success and is_recurring_task(task):
            logger.info(
                f"Completed recurring task {task_id}, next occurrence should be created automatically"
            )

        return success

    except Exception as e:
        logger.error(f"Error completing recurring task {task_id}: {str(e)}")
        return False


def get_all_recurring_tasks(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all recurring tasks, optionally filtered by project.

    Args:
        project_id: Optional project ID to filter by

    Returns:
        List[Dict]: List of recurring tasks
    """
    try:
        # Get all tasks
        if project_id:
            all_tasks = get_tasks_by_filter(f"#project:{project_id}")
        else:
            all_tasks = get_all_tasks()

        if not all_tasks:
            return []

        # Filter for recurring tasks
        recurring_tasks = [task for task in all_tasks if is_recurring_task(task)]

        logger.info(
            f"Found {len(recurring_tasks)} recurring tasks"
            + (f" in project {project_id}" if project_id else "")
        )

        return recurring_tasks

    except Exception as e:
        logger.error(f"Error getting recurring tasks: {str(e)}")
        return []


def update_recurring_pattern(task_id: str, new_due_string: str) -> bool:
    """
    Update the recurring pattern of a task.

    Args:
        task_id: ID of the task to update
        new_due_string: New recurring pattern

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate the new pattern
        if not _is_valid_recurring_pattern(new_due_string):
            logger.warning(f"Invalid recurring pattern: {new_due_string}")

        # Update the task
        success = update_task(task_id, due_string=new_due_string)

        if success:
            logger.info(
                f"Updated recurring pattern for task {task_id} to: {new_due_string}"
            )

        return success

    except Exception as e:
        logger.error(f"Error updating recurring pattern for task {task_id}: {str(e)}")
        return False


def convert_to_recurring_task(task_id: str, due_string: str) -> bool:
    """
    Convert a one-time task to a recurring task.

    Args:
        task_id: ID of the task to convert
        due_string: Recurring pattern to apply

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current task
        task = get_task_by_id(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False

        # Check if already recurring
        if is_recurring_task(task):
            logger.warning(f"Task {task_id} is already recurring")
            return update_recurring_pattern(task_id, due_string)

        # Convert to recurring
        success = update_task(task_id, due_string=due_string)

        if success:
            logger.info(
                f"Converted task {task_id} to recurring with pattern: {due_string}"
            )

        return success

    except Exception as e:
        logger.error(f"Error converting task {task_id} to recurring: {str(e)}")
        return False


def remove_recurring_pattern(task_id: str, new_due_date: Optional[str] = None) -> bool:
    """
    Remove recurring pattern from a task, making it a one-time task.

    Args:
        task_id: ID of the recurring task
        new_due_date: Optional specific due date (YYYY-MM-DD format)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current task
        task = get_task_by_id(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False

        if not is_recurring_task(task):
            logger.warning(f"Task {task_id} is not recurring")
            return True

        # Update with specific date or remove date entirely
        if new_due_date:
            success = update_task(task_id, due_date=new_due_date)
        else:
            success = update_task(task_id, due_string="no date")

        if success:
            logger.info(f"Removed recurring pattern from task {task_id}")

        return success

    except Exception as e:
        logger.error(f"Error removing recurring pattern from task {task_id}: {str(e)}")
        return False


def _is_valid_recurring_pattern(due_string: str) -> bool:
    """
    Validate if a due string represents a valid recurring pattern.

    Args:
        due_string: The due string to validate

    Returns:
        bool: True if it appears to be a valid recurring pattern
    """
    if not due_string or not isinstance(due_string, str):
        return False

    # Convert to lowercase for checking
    pattern = due_string.lower().strip()

    # Common recurring keywords
    recurring_keywords = [
        "every",
        "daily",
        "weekly",
        "monthly",
        "yearly",
        "quarterly",
        "workday",
        "weekend",
        "weekday",
    ]

    # Check if any recurring keywords are present
    return any(keyword in pattern for keyword in recurring_keywords)


def get_recurring_task_summary(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of recurring task information.

    Args:
        task_data: Task object from Todoist API

    Returns:
        Dict: Summary with recurring task details
    """
    try:
        summary = {
            "is_recurring": is_recurring_task(task_data),
            "pattern": None,
            "next_date": None,
            "has_time": False,
            "timezone": None,
        }

        if summary["is_recurring"]:
            due_info = task_data.get("due", {})
            summary["pattern"] = due_info.get("string")
            summary["next_date"] = due_info.get("date")
            summary["has_time"] = due_info.get("datetime") is not None
            summary["timezone"] = due_info.get("timezone")

        return summary

    except Exception as e:
        logger.error(f"Error creating recurring task summary: {str(e)}")
        return {
            "is_recurring": False,
            "pattern": None,
            "next_date": None,
            "has_time": False,
            "timezone": None,
        }


# Common recurring patterns for easy reference
COMMON_RECURRING_PATTERNS = {
    "daily": "every day",
    "weekly": "every week",
    "monthly": "every month",
    "yearly": "every year",
    "weekdays": "every weekday",
    "weekends": "every weekend",
    "every_other_day": "every other day",
    "every_other_week": "every other week",
    "every_other_month": "every other month",
    "quarterly": "every quarter",
    "twice_weekly": "every mon, fri",
    "three_times_weekly": "every mon, wed, fri",
}


def get_common_recurring_patterns() -> Dict[str, str]:
    """
    Get a dictionary of common recurring patterns.

    Returns:
        Dict[str, str]: Dictionary mapping pattern names to due_string values
    """
    return COMMON_RECURRING_PATTERNS.copy()


# ==================== ENHANCED ERROR HANDLING AND FALLBACK FUNCTIONS ====================


def check_todoist_health(user_id: str) -> Dict[str, Any]:
    """
    Check the health status of Todoist API.

    Args:
        user_id: User identifier for authentication

    Returns:
        Dict with health status information
    """
    try:
        is_healthy = health_monitor.check_health(user_id)

        health_info = {
            "is_healthy": is_healthy,
            "circuit_breaker_state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
            "last_check": health_monitor.last_check,
            "consecutive_failures": health_monitor.consecutive_failures,
        }

        logger.info(f"Todoist health check for user {user_id}: {health_info}")
        return health_info

    except Exception as e:
        logger.error(f"Error checking Todoist health: {e}")
        return {
            "is_healthy": False,
            "error": str(e),
            "circuit_breaker_state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
        }


def clear_cache() -> bool:
    """
    Clear the API cache.

    Returns:
        bool: True if successful
    """
    try:
        api_cache.clear()
        logger.info("Todoist API cache cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return False


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dict with cache statistics
    """
    try:
        with api_cache.lock:
            total_entries = len(api_cache.cache)
            current_time = time.time()

            expired_count = 0
            total_age = 0

            for entry in api_cache.cache.values():
                age = current_time - entry.timestamp
                total_age += age
                if age > entry.ttl:
                    expired_count += 1

            avg_age = total_age / total_entries if total_entries > 0 else 0

            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "active_entries": total_entries - expired_count,
                "average_age_seconds": round(avg_age, 2),
                "max_size": api_cache.max_size,
                "utilization_percent": round(
                    (total_entries / api_cache.max_size) * 100, 2
                ),
            }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {"error": str(e)}


def reset_circuit_breaker() -> bool:
    """
    Manually reset the circuit breaker to closed state.

    Returns:
        bool: True if successful
    """
    try:
        with circuit_breaker.lock:
            circuit_breaker.state = CircuitState.CLOSED
            circuit_breaker.failure_count = 0
            circuit_breaker.success_count = 0

        logger.info("Circuit breaker manually reset to CLOSED state")
        return True
    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {e}")
        return False


@with_fallback(
    cache_key_func=_projects_cache_key, cache_ttl=CACHE_DEFAULT_TTL, fallback_data=[]
)
def get_all_projects_with_fallback(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all projects with enhanced error handling and caching.

    Args:
        user_id: User identifier for authentication

    Returns:
        List of project dictionaries (may be cached or fallback data)
    """
    return get_all_projects(user_id)


@with_fallback(
    cache_key_func=lambda user_id, **kwargs: _tasks_cache_key(user_id, **kwargs),
    cache_ttl=CACHE_DEFAULT_TTL,
    fallback_data=[],
)
def get_all_tasks_with_fallback(
    user_id: str,
    project_id: Optional[str] = None,
    label: Optional[str] = None,
    filter_expr: Optional[str] = None,
    lang: str = "en",
) -> List[Dict[str, Any]]:
    """
    Fetch tasks with enhanced error handling and caching.

    Args:
        user_id: User identifier for authentication
        project_id: Optional project ID to filter tasks
        label: Optional label name to filter tasks
        filter_expr: Optional Todoist filter expression
        lang: Language for dates

    Returns:
        List of task dictionaries (may be cached or fallback data)
    """
    return get_all_tasks(user_id, project_id, label, filter_expr, lang)


@with_fallback(
    cache_key_func=_labels_cache_key, cache_ttl=CACHE_DEFAULT_TTL, fallback_data=[]
)
def get_all_labels_with_fallback(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all labels with enhanced error handling and caching.

    Args:
        user_id: User identifier for authentication

    Returns:
        List of label dictionaries (may be cached or fallback data)
    """
    return get_all_labels(user_id)


def safe_api_call(
    func: Callable,
    *args,
    fallback_result: Optional[Any] = None,
    max_retries: int = MAX_RETRIES,
    **kwargs,
) -> Any:
    """
    Safely execute an API call with configurable retries and fallback.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        fallback_result: Result to return if all attempts fail
        max_retries: Maximum number of retry attempts
        **kwargs: Keyword arguments for the function

    Returns:
        Function result or fallback_result if all attempts fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (TodoistConnectionError, TodoistAPIError) as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = 2**attempt  # Exponential backoff
                logger.warning(
                    f"API call failed (attempt {attempt + 1}): {e}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logger.error(f"API call failed after {max_retries + 1} attempts: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in safe_api_call: {e}")
            last_exception = e
            break

    if fallback_result is not None:
        logger.info(f"Using fallback result for failed API call: {func.__name__}")
        return fallback_result

    raise last_exception


def batch_api_calls(
    calls: List[Dict[str, Any]],
    fail_fast: bool = False,
    delay_between_calls: float = 0.1,
) -> List[Dict[str, Any]]:
    """
    Execute multiple API calls with error handling.

    Args:
        calls: List of call dictionaries with 'func', 'args', 'kwargs', 'fallback'
        fail_fast: Stop on first failure if True, continue if False
        delay_between_calls: Delay in seconds between calls

    Returns:
        List of results with success/failure status
    """
    results = []

    for i, call_info in enumerate(calls):
        if delay_between_calls > 0 and i > 0:
            time.sleep(delay_between_calls)

        try:
            func = call_info["func"]
            args = call_info.get("args", [])
            kwargs = call_info.get("kwargs", {})
            fallback = call_info.get("fallback")

            result = safe_api_call(func, *args, fallback_result=fallback, **kwargs)

            results.append(
                {
                    "success": True,
                    "result": result,
                    "call_index": i,
                    "function": func.__name__,
                }
            )

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "call_index": i,
                "function": call_info["func"].__name__,
            }

            results.append(error_result)

            if fail_fast:
                logger.error(f"Batch API call failed fast at index {i}: {e}")
                break
            else:
                logger.warning(f"Batch API call failed at index {i}, continuing: {e}")

    success_count = sum(1 for r in results if r["success"])
    logger.info(f"Batch API calls completed: {success_count}/{len(results)} successful")

    return results


def get_todoist_status_summary(user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive status summary for Todoist integration.

    Args:
        user_id: User identifier

    Returns:
        Dict with comprehensive status information
    """
    try:
        # Health check
        health_status = check_todoist_health(user_id)

        # Cache statistics
        cache_stats = get_cache_stats()

        # Circuit breaker status
        circuit_status = {
            "state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
            "success_count": circuit_breaker.success_count,
            "failure_threshold": circuit_breaker.failure_threshold,
            "recovery_timeout": circuit_breaker.recovery_timeout,
        }

        # Test basic connectivity
        connection_test = None
        try:
            connection_test = test_connection(user_id)
        except Exception as e:
            connection_test = {"error": str(e)}

        return {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "health_status": health_status,
            "cache_stats": cache_stats,
            "circuit_breaker": circuit_status,
            "connection_test": connection_test,
            "api_base_url": TODOIST_API_BASE,
        }

    except Exception as e:
        logger.error(f"Error getting Todoist status summary: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "error": str(e),
            "health_status": {"is_healthy": False},
            "cache_stats": {"error": "unavailable"},
            "circuit_breaker": {"state": "unknown"},
        }
