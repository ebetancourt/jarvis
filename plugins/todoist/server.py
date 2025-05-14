from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from rapidfuzz import fuzz
from mcp.server.fastmcp import FastMCP
from todoist_api_python.api_async import TodoistAPIAsync
import backoff
import aiohttp
import json
import logging
from .filters import DEFAULT_FILTERS, get_filter_help

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TodoistError(Exception):
    """Base class for Todoist API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after

class TodoistRateLimitError(TodoistError):
    """Raised when Todoist API rate limit is exceeded."""
    pass

class TodoistAuthError(TodoistError):
    """Raised when there are authentication issues."""
    pass

class TodoistNotFoundError(TodoistError):
    """Raised when a resource is not found."""
    pass

mcp = FastMCP("Todoist")
api: Optional[TodoistAPIAsync] = None
api_token: Optional[str] = None

def initialize_api(token: str):
    """Initialize the Todoist API with the given token."""
    global api, api_token
    api = TodoistAPIAsync(token)
    api_token = token

def _handle_api_error(e: Exception) -> None:
    """Handle common API errors and raise appropriate exceptions."""
    error_msg = str(e).lower()

    if isinstance(e, aiohttp.ClientResponseError):
        if e.status == 429:  # Rate limit exceeded
            retry_after = int(e.headers.get('Retry-After', 60))
            raise TodoistRateLimitError(
                f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                status_code=429,
                retry_after=retry_after
            )
        elif e.status == 401:
            raise TodoistAuthError("Invalid API token or authentication failed.", status_code=401)
        elif e.status == 404:
            raise TodoistNotFoundError("Requested resource not found.", status_code=404)
        else:
            raise TodoistError(f"API request failed: {str(e)}", status_code=e.status)

    if "rate limit exceeded" in error_msg:
        raise TodoistRateLimitError("Rate limit exceeded. Please try again later.")
    elif "unauthorized" in error_msg or "authentication" in error_msg:
        raise TodoistAuthError("Invalid API token or authentication failed.")
    elif "not found" in error_msg:
        raise TodoistNotFoundError("Requested resource not found.")

    raise TodoistError(f"API request failed: {str(e)}")

@backoff.on_exception(
    backoff.expo,
    TodoistRateLimitError,
    max_tries=3,
    giveup=lambda e: not isinstance(e, TodoistRateLimitError)
)
async def _api_request(func, *args, **kwargs):
    """Make an API request with retries and error handling."""
    if not api:
        raise TodoistError("Todoist API not initialized")

    try:
        result = await func(*args, **kwargs)
        # Handle async generators (like get_tasks())
        if hasattr(result, '__aiter__'):
            items = []
            async for item in result:
                items.append(item)
            return items
        return result
    except Exception as e:
        _handle_api_error(e)

def task_to_dict(task: Any) -> Dict[str, Any]:
    """Convert a Todoist task to a dictionary representation."""
    # Handle if task is already a dictionary
    if isinstance(task, dict):
        return {
            'id': task.get('id'),
            'content': task.get('content'),
            'project_id': task.get('project_id'),
            'section_id': task.get('section_id'),
            'parent_id': task.get('parent_id'),
            'priority': task.get('priority', 1),
            'due': task.get('due'),
            'url': task.get('url'),
            'is_completed': task.get('is_completed', False),
            'created_at': task.get('created_at'),
            'labels': task.get('labels', []),
        }
    # Handle if task is an object
    return {
        'id': getattr(task, 'id', None),
        'content': getattr(task, 'content', ''),
        'project_id': getattr(task, 'project_id', None),
        'section_id': getattr(task, 'section_id', None),
        'parent_id': getattr(task, 'parent_id', None),
        'priority': getattr(task, 'priority', 1),
        'due': task.due.dict() if getattr(task, 'due', None) else None,
        'url': getattr(task, 'url', None),
        'is_completed': getattr(task, 'is_completed', False),
        'created_at': getattr(task, 'created_at', None),
        'labels': getattr(task, 'labels', []),
    }

def calculate_content_score(query: str, content: str) -> float:
    """Calculate a relevance score for task content.

    Uses a combination of exact and fuzzy matching, with word-level analysis.
    """
    query_lower = query.lower()
    content_lower = content.lower()

    # Start with full string fuzzy match
    full_score = fuzz.ratio(query_lower, content_lower)

    # Word-level matching
    query_words = set(query_lower.split())
    content_words = set(content_lower.split())

    # Calculate word-level scores
    word_scores = []
    for qw in query_words:
        best_word_score = 0
        for cw in content_words:
            # Exact match gets full score
            if qw == cw:
                best_word_score = 100
                break
            # Otherwise use fuzzy matching
            score = fuzz.ratio(qw, cw)
            best_word_score = max(best_word_score, score)
        word_scores.append(best_word_score)

    # Average word-level score
    avg_word_score = sum(word_scores) / len(word_scores) if word_scores else 0

    # Combine scores (60% word-level, 40% full string)
    final_score = (avg_word_score * 0.6) + (full_score * 0.4)

    # Bonus for exact substring match
    if query_lower in content_lower:
        final_score = min(100, final_score + 20)

    return final_score

def format_task_response(tasks: List[Dict[str, Any]], action: str = "found") -> Dict[str, Any]:
    """Format tasks into a friendly response.

    Args:
        tasks: List of tasks to format
        action: The action being performed ("found", "completed", etc.)

    Returns:
        Dict with message and tasks
    """
    if not tasks:
        return {
            "success": False,
            "message": "No tasks found matching your query.",
            "tasks": []
        }

    task_list = []
    for task in tasks:
        # Safely extract due date
        due_date = None
        if isinstance(task.get('due'), dict):
            due_date = task['due'].get('date')

        task_info = {
            "content": task.get('content', ''),
            "priority": task.get('priority', 1),
            "due": due_date,
            "project_id": task.get('project_id'),
            "url": task.get('url')
        }
        task_list.append(task_info)

    if len(tasks) == 1:
        task = tasks[0]
        message = f"I {action} the task '{task.get('content', '')}'"
        if isinstance(task.get('due'), dict) and task['due'].get('date'):
            message += f" (due {task['due']['date']})"
    else:
        message = f"I {action} {len(tasks)} tasks"

    return {
        "success": True,
        "message": message,
        "tasks": task_list
    }

@mcp.tool()
async def list_tasks(
    project_id: Optional[str] = None,
    section_id: Optional[str] = None,
    label: Optional[str] = None,
    filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List tasks from Todoist with optional filtering.

    Args:
        project_id: Optional project ID to filter tasks
        section_id: Optional section ID to filter tasks
        label: Optional label to filter tasks
        filter: Optional Todoist filter query (e.g. "today", "overdue", "priority 4")
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        tasks = await _api_request(api.get_tasks)
        filtered_tasks = []

        for task in tasks:
            if project_id and task.project_id != project_id:
                continue
            if section_id and task.section_id != section_id:
                continue
            if label and label not in (task.labels if hasattr(task, 'labels') else []):
                continue
            if filter:
                # Basic filter implementation - can be enhanced
                filter_lower = filter.lower()
                if filter_lower == "today" and not task.due:
                    continue
                if filter_lower == "overdue" and not (task.due and task.due.is_past):
                    continue
                if filter_lower.startswith("priority "):
                    try:
                        priority = int(filter_lower.split()[-1])
                        if task.priority != priority:
                            continue
                    except ValueError:
                        pass

            filtered_tasks.append(task_to_dict(task))

        return filtered_tasks

    except TodoistRateLimitError as e:
        raise TodoistError(
            f"Rate limit exceeded. Please retry after {e.retry_after} seconds if specified.",
            retry_after=e.retry_after
        )
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def add_task(
    content: str,
    project_id: Optional[str] = None,
    section_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    priority: int = 1,
    due_string: Optional[str] = None,
    due_date: Optional[str] = None,
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Add a new task to Todoist.

    Args:
        content: The task content/description
        project_id: Optional ID of the project to add the task to
        section_id: Optional ID of the section to add the task to
        parent_id: Optional ID of the parent task
        priority: Task priority (1-4, where 4 is highest)
        due_string: Human readable due date (e.g. "tomorrow at 12pm")
        due_date: Due date in YYYY-MM-DD format
        labels: List of labels to apply to the task
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        task = await _api_request(
            api.add_task,
            content=content,
            project_id=project_id,
            section_id=section_id,
            parent_id=parent_id,
            priority=priority,
            due_string=due_string,
            due_date=due_date,
            labels=labels or []
        )
        return task_to_dict(task)
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def get_projects() -> List[Dict[str, Any]]:
    """Get all projects from Todoist."""
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        projects = await _api_request(api.get_projects)
        return [{
            'id': project.id,
            'name': project.name,
            'color': project.color,
            'parent_id': project.parent_id,
            'order': project.order,
            'is_shared': project.is_shared,
            'is_favorite': project.is_favorite,
            'url': project.url,
        } for project in projects]
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def get_sections(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get sections from Todoist.

    Args:
        project_id: Optional project ID to filter sections
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        sections = await _api_request(api.get_sections)
        if project_id:
            sections = [s for s in sections if s.project_id == project_id]

        return [{
            'id': section.id,
            'name': section.name,
            'project_id': section.project_id,
            'order': section.order,
        } for section in sections]
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def complete_task(task_id: str) -> bool:
    """Mark a task as completed.

    Args:
        task_id: The ID of the task to complete
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        # Use the REST API v2 endpoint directly
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_token}"}
            url = f"https://api.todoist.com/rest/v2/tasks/{task_id}/close"
            async with session.post(url, headers=headers) as response:
                response.raise_for_status()
                return True
    except Exception as e:
        print(f"Error completing task: {e}")
        return False

@mcp.tool()
async def update_task(
    task_id: str,
    content: Optional[str] = None,
    priority: Optional[int] = None,
    due_string: Optional[str] = None,
    due_date: Optional[str] = None,
    project_id: Optional[str] = None,
    section_id: Optional[str] = None,
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Update an existing task.

    Args:
        task_id: The ID of the task to update
        content: New task content/description
        priority: New priority (1-4, where 4 is highest)
        due_string: New human readable due date
        due_date: New due date in YYYY-MM-DD format
        project_id: New project ID to move the task to
        section_id: New section ID to move the task to
        labels: New list of labels for the task
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        update_data = {}
        if content is not None:
            update_data['content'] = content
        if priority is not None:
            update_data['priority'] = priority
        if due_string is not None:
            update_data['due_string'] = due_string
        if due_date is not None:
            update_data['due_date'] = due_date
        if project_id is not None:
            update_data['project_id'] = project_id
        if section_id is not None:
            update_data['section_id'] = section_id
        if labels is not None:
            update_data['labels'] = labels

        await _api_request(api.update_task, task_id=task_id, **update_data)

        # Get and return the updated task
        task = await _api_request(api.get_task, task_id=task_id)
        return task_to_dict(task)
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def find_task_by_name(query: str) -> Optional[Dict[str, Any]]:
    """Find a task by name using fuzzy matching.

    Args:
        query: The task name/description to search for

    Returns:
        The best matching task or None if no match found
    """
    try:
        # Get all active tasks
        tasks = await _api_request(api.get_tasks)

        best_match = None
        best_score = 0

        for task in tasks:
            task_dict = task_to_dict(task)
            score = calculate_content_score(query, task_dict['content'])
            if score > best_score:
                best_score = score
                best_match = task_dict

        if best_score >= 60:  # Minimum threshold for a good match
            return best_match
        return None

    except Exception as e:
        logger.error(f"Error finding task: {str(e)}", exc_info=True)
        return None

@mcp.tool()
async def search_tasks(
    query: str,
    filter_string: Optional[str] = None,
    due_after: Optional[str] = None,
    due_before: Optional[str] = None,
    priority: Optional[int] = None,
    labels: Optional[List[str]] = None,
    fuzzy_threshold: float = 60.0
) -> Dict[str, Any]:
    """Search for tasks using various criteria.

    For filter syntax help, see the FILTER_DOCUMENTATION in filters.py.
    Common filter patterns are available in DEFAULT_FILTERS.

    Args:
        query: Search query for task content
        filter_string: Optional Todoist filter string
        due_after: Optional date to filter tasks due after (YYYY-MM-DD)
        due_before: Optional date to filter tasks due before (YYYY-MM-DD)
        priority: Optional priority level (1-4)
        labels: Optional list of labels to filter by
        fuzzy_threshold: Minimum score for fuzzy matching (0-100)

    Returns:
        Dict containing success status, message, and matching tasks
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    filters = []
    if filter_string:
        filters.append(filter_string)
    if due_after:
        filters.append(f"due after: {due_after}")
    if due_before:
        filters.append(f"due before: {due_before}")
    if priority:
        filters.append(f"p{priority}")
    if labels:
        filters.extend(f"@{label}" for label in labels)

    filter_query = " & ".join(filters) if filters else DEFAULT_FILTERS['today_and_overdue']
    logger.debug(f"Using Todoist filter query: {filter_query}")

    try:
        # First try the filter_tasks method
        tasks = await _api_request(api.filter_tasks, query=filter_query)
        logger.debug(f"filter_tasks returned {len(tasks)} tasks")

        # If we get an empty or invalid response, try direct REST API call
        if not tasks or (len(tasks) == 1 and not (isinstance(tasks[0], dict) and tasks[0].get('content'))):
            logger.info("Initial API call returned no results, trying direct REST API call")
            if not api_token:
                raise TodoistError("API token not available for REST API call")

            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_token}"}
                url = "https://api.todoist.com/rest/v2/tasks"
                params = {"filter": filter_query} if filter_query else {}

                async with session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    tasks_json = await response.json()
                    logger.debug(f"Direct REST API call returned {len(tasks_json)} tasks")
                    tasks = tasks_json  # Use the REST API response instead

        logger.info(f"Retrieved {len(tasks)} tasks from Todoist API")

        matching_tasks = []
        for task in tasks:
            task_dict = task_to_dict(task)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Processing task: {json.dumps(task_dict, indent=2)}")

            # For date-based filters (today, overdue, etc.), trust the API's filtering
            is_date_based_filter = any(date_term in (filter_query or "").lower()
                                     for date_term in ["today", "overdue", "7 days", "no date"])

            if is_date_based_filter:
                # For date filters, include all tasks returned by the API
                matching_tasks.append(task_dict)
            else:
                # For content/keyword searches, apply relevance scoring
                content_score = calculate_content_score(query, task_dict['content'])
                logger.debug(f"Content score for task '{task_dict['content']}': {content_score}")

                # Additional scoring factors
                priority_boost = (task_dict['priority'] - 1) * 5
                due_soon_boost = 0
                if task_dict['due']:
                    due_date = task_dict['due'].get('date') if isinstance(task_dict['due'], dict) else None
                    if due_date:
                        try:
                            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                            days_until_due = (due_date_obj - datetime.now()).days
                            if 0 <= days_until_due <= 7:  # Due within a week
                                due_soon_boost = max(0, 10 - days_until_due)  # 0-10 points boost
                        except ValueError:
                            pass

                # Calculate final score
                relevance_score = content_score + priority_boost + due_soon_boost
                logger.debug(f"Final relevance score for task '{task_dict['content']}': {relevance_score}")

                # Only include tasks that meet the fuzzy threshold for non-date filters
                if relevance_score >= fuzzy_threshold:
                    task_dict['relevance_score'] = relevance_score
                    matching_tasks.append(task_dict)

        # Sort by relevance score for non-date filters, otherwise keep API order
        if not is_date_based_filter and matching_tasks:
            matching_tasks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        logger.info(f"Returning {len(matching_tasks)} matching tasks")
        return {
            "success": True,
            "message": f"Found {len(matching_tasks)} matching tasks",
            "tasks": matching_tasks
        }

    except Exception as e:
        logger.error(f"Error searching tasks: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error searching tasks: {str(e)}",
            "tasks": []
        }

@mcp.tool()
async def reschedule_task(
    task_id: str,
    due_string: str
) -> Dict[str, Any]:
    """Reschedule a task to a new due date using natural language.

    Args:
        task_id: The ID of the task to reschedule
        due_string: Natural language due date (e.g. "tomorrow at 3pm", "next Monday", "in 2 weeks", "April 15")

    Raises:
        ValueError: If the API is not initialized, task_id is invalid, or due_string is empty
        Exception: If the API call fails
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    if not task_id:
        raise TodoistError("task_id cannot be empty")

    if not due_string:
        raise TodoistError("due_string cannot be empty")

    try:
        # Verify task exists before updating
        task = await _api_request(api.get_task, task_id=task_id)
        if not task:
            raise TodoistError(f"Task with ID {task_id} not found")

        # Update the task
        await _api_request(api.update_task, task_id=task_id, due_string=due_string)

        # Get and return the updated task
        updated_task = await _api_request(api.get_task, task_id=task_id)
        return task_to_dict(updated_task)
    except Exception as e:
        raise TodoistError(f"Failed to reschedule task: {str(e)}")

@mcp.tool()
async def get_api_status() -> Dict[str, Any]:
    """Get the current API status and rate limit information."""
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        # Make a lightweight API call to check status
        projects = await _api_request(api.get_projects)
        return {
            "status": "ok",
            "message": "API is functioning normally",
            "timestamp": datetime.now().isoformat()
        }
    except TodoistRateLimitError as e:
        return {
            "status": "rate_limited",
            "message": str(e),
            "retry_after": e.retry_after,
            "timestamp": datetime.now().isoformat()
        }
    except TodoistAuthError as e:
        return {
            "status": "auth_error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@mcp.tool()
async def add_project(
    name: str,
    parent_id: Optional[str] = None,
    color: Optional[str] = None,
    is_favorite: bool = False
) -> Dict[str, Any]:
    """Create a new project.

    Args:
        name: The name of the project
        parent_id: Optional ID of the parent project
        color: Optional color (e.g. 'red', 'blue', etc.)
        is_favorite: Whether to mark the project as favorite
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        project = await _api_request(
            api.add_project,
            name=name,
            parent_id=parent_id,
            color=color,
            is_favorite=is_favorite
        )
        return {
            'id': project.id,
            'name': project.name,
            'color': project.color,
            'parent_id': project.parent_id,
            'order': project.order,
            'is_shared': project.is_shared,
            'is_favorite': project.is_favorite,
            'url': project.url,
        }
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def update_project(
    project_id: str,
    name: Optional[str] = None,
    color: Optional[str] = None,
    is_favorite: Optional[bool] = None
) -> Dict[str, Any]:
    """Update an existing project.

    Args:
        project_id: The ID of the project to update
        name: Optional new name for the project
        color: Optional new color
        is_favorite: Optional favorite status
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if color is not None:
            update_data['color'] = color
        if is_favorite is not None:
            update_data['is_favorite'] = is_favorite

        project = await _api_request(api.update_project, project_id=project_id, **update_data)
        return {
            'id': project.id,
            'name': project.name,
            'color': project.color,
            'parent_id': project.parent_id,
            'order': project.order,
            'is_shared': project.is_shared,
            'is_favorite': project.is_favorite,
            'url': project.url,
        }
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def delete_project(project_id: str) -> bool:
    """Delete a project.

    Args:
        project_id: The ID of the project to delete
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        await _api_request(api.delete_project, project_id=project_id)
        return True
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def get_labels() -> List[Dict[str, Any]]:
    """Get all labels."""
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        labels = await _api_request(api.get_labels)
        return [{
            'id': label.id,
            'name': label.name,
            'color': label.color,
            'order': label.order,
            'is_favorite': label.is_favorite,
        } for label in labels]
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def add_label(
    name: str,
    color: Optional[str] = None,
    is_favorite: bool = False
) -> Dict[str, Any]:
    """Create a new label.

    Args:
        name: The name of the label
        color: Optional color (e.g. 'red', 'blue', etc.)
        is_favorite: Whether to mark the label as favorite
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        label = await _api_request(
            api.add_label,
            name=name,
            color=color,
            is_favorite=is_favorite
        )
        return {
            'id': label.id,
            'name': label.name,
            'color': label.color,
            'order': label.order,
            'is_favorite': label.is_favorite,
        }
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def update_label(
    label_id: str,
    name: Optional[str] = None,
    color: Optional[str] = None,
    is_favorite: Optional[bool] = None
) -> Dict[str, Any]:
    """Update an existing label.

    Args:
        label_id: The ID of the label to update
        name: Optional new name for the label
        color: Optional new color
        is_favorite: Optional favorite status
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if color is not None:
            update_data['color'] = color
        if is_favorite is not None:
            update_data['is_favorite'] = is_favorite

        label = await _api_request(api.update_label, label_id=label_id, **update_data)
        return {
            'id': label.id,
            'name': label.name,
            'color': label.color,
            'order': label.order,
            'is_favorite': label.is_favorite,
        }
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def delete_label(label_id: str) -> bool:
    """Delete a label.

    Args:
        label_id: The ID of the label to delete
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        await _api_request(api.delete_label, label_id=label_id)
        return True
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def add_comment(
    task_id: str,
    content: str
) -> Dict[str, Any]:
    """Add a comment to a task.

    Args:
        task_id: The ID of the task to comment on
        content: The comment text
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    if not task_id:
        raise TodoistError("task_id cannot be empty")

    if not content:
        raise TodoistError("content cannot be empty")

    try:
        comment = await _api_request(
            api.add_comment,
            task_id=task_id,
            content=content
        )
        return {
            'id': comment.id,
            'task_id': comment.task_id,
            'content': comment.content,
            'posted_at': comment.posted_at,
        }
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def get_task_comments(task_id: str) -> List[Dict[str, Any]]:
    """Get all comments for a task.

    Args:
        task_id: The ID of the task to get comments for
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    if not task_id:
        raise TodoistError("task_id cannot be empty")

    try:
        comments = await _api_request(api.get_comments, task_id=task_id)
        return [{
            'id': comment.id,
            'task_id': comment.task_id,
            'content': comment.content,
            'posted_at': comment.posted_at,
        } for comment in comments]
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def add_recurring_task(
    content: str,
    due_string: str,
    project_id: Optional[str] = None,
    section_id: Optional[str] = None,
    priority: int = 1,
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Add a new recurring task.

    Args:
        content: The task content/description
        due_string: Recurring due date (e.g. "every monday", "every 2 weeks", "every month on the 1st")
        project_id: Optional ID of the project to add the task to
        section_id: Optional ID of the section to add the task to
        priority: Task priority (1-4, where 4 is highest)
        labels: List of labels to apply to the task
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    if not content:
        raise TodoistError("content cannot be empty")

    if not due_string:
        raise TodoistError("due_string cannot be empty")

    try:
        task = await _api_request(
            api.add_task,
            content=content,
            due_string=due_string,
            project_id=project_id,
            section_id=section_id,
            priority=priority,
            labels=labels or []
        )
        return task_to_dict(task)
    except Exception as e:
        _handle_api_error(e)

@mcp.tool()
async def complete_task_by_name(task_name: str) -> Dict[str, Any]:
    """Find and complete a task by its name.

    Args:
        task_name: The name/description of the task to complete

    Returns:
        Dict with status and message
    """
    if not api:
        raise TodoistError("Todoist API not initialized. Call initialize_api first.")

    try:
        # First search for the task
        search_result = await search_tasks(query=task_name)
        if not search_result['success'] or not search_result['tasks']:
            return {
                "success": False,
                "message": f"I couldn't find a task matching '{task_name}'. Could you please be more specific?",
                "tasks": []
            }

        # Find the best matching task using content score
        tasks = search_result['tasks']
        best_match = None
        best_score = 0
        for task in tasks:
            score = calculate_content_score(task_name, task['content'])
            if score > best_score:
                best_score = score
                best_match = task

        if not best_match or best_score < 60:  # Minimum threshold for a good match
            return {
                "success": False,
                "message": f"I couldn't find a task matching '{task_name}'. Could you please be more specific?",
                "tasks": []
            }

        task_id = best_match.get('id')
        if not task_id:
            return {
                "success": False,
                "message": "Found a matching task but couldn't get its ID. This is likely a bug.",
                "tasks": []
            }

        # Try to complete the task
        success = await complete_task(task_id)
        if success:
            return format_task_response([best_match], action="completed")
        else:
            return {
                "success": False,
                "message": f"Found the task but failed to complete it. Please try again.",
                "tasks": [best_match]
            }

    except Exception as e:
        logger.error(f"Error completing task by name: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error completing task: {str(e)}",
            "tasks": []
        }

@mcp.tool()
async def get_filter_documentation() -> str:
    """Get documentation about Todoist filter syntax and common patterns.

    Returns:
        Formatted string containing filter documentation
    """
    return get_filter_help()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_token = os.getenv("TODOIST_API_TOKEN")
    if not api_token:
        raise ValueError("TODOIST_API_TOKEN environment variable not set")

    initialize_api(api_token)
    mcp.run(transport="sse")
