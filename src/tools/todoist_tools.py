"""
Todoist API integration tools for weekly review agent.

This module provides functions to interact with the Todoist REST API v2 for
fetching and managing tasks, projects, and labels. It integrates with the
existing OAuth infrastructure to handle authentication.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
import requests
from requests.exceptions import RequestException, Timeout, HTTPError

from service.oauth_service import get_oauth_service, OAuthToken
from core.settings import settings

# Configure logging
logger = logging.getLogger(__name__)

# Todoist API configuration
TODOIST_API_BASE = "https://api.todoist.com/rest/v2"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3


class TodoistAPIError(Exception):
    """Custom exception for Todoist API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
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
        TodoistAuthenticationError: If no valid token is available
    """
    oauth_service = get_oauth_service()
    token = oauth_service.get_token("todoist", user_id)
    
    if not token:
        raise TodoistAuthenticationError(
            f"No Todoist token found for user {user_id}. "
            "Please complete OAuth authentication first."
        )
    
    if not oauth_service._is_token_valid(token):
        raise TodoistAuthenticationError(
            f"Todoist token for user {user_id} has expired. "
            "Please re-authenticate with Todoist."
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
                    logger.warning(f"Rate limited by Todoist API. Waiting {wait_time}s before retry.")
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
    user_id: str, 
    filter_expression: str,
    lang: str = "en"
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
