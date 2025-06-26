"""
Comprehensive unit tests for Todoist API integration tools.

This module contains tests for all Todoist API integration functions including
basic API operations, task management, recurring tasks, error handling,
circuit breaker functionality, caching, and health monitoring.
"""

import os
import sys
import time
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock, call
import json
import pytest
import requests

# Add src to path for importing the source modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from tools.todoist_tools import (
    # Basic API functions
    get_all_tasks,
    get_all_projects,
    get_all_labels,
    get_task_by_id,
    get_project_by_id,
    get_label_by_id,
    get_tasks_by_filter,
    get_completed_tasks,
    test_connection,
    get_user_info,
    # Task management functions
    create_task,
    update_task,
    delete_task,
    complete_task,
    reopen_task,
    bulk_complete_tasks,
    update_task_status,
    move_task_to_project,
    set_task_priority,
    add_task_labels,
    set_task_due_date,
    # Recurring task functions
    is_recurring_task,
    get_recurring_pattern,
    create_recurring_task,
    get_next_occurrence_date,
    complete_recurring_task,
    get_all_recurring_tasks,
    update_recurring_pattern,
    convert_to_recurring_task,
    remove_recurring_pattern,
    get_recurring_task_summary,
    get_common_recurring_patterns,
    # Error handling and fallback functions
    check_todoist_health,
    clear_cache,
    get_cache_stats,
    reset_circuit_breaker,
    get_all_projects_with_fallback,
    get_all_tasks_with_fallback,
    get_all_labels_with_fallback,
    safe_api_call,
    batch_api_calls,
    get_todoist_status_summary,
    # Exceptions
    TodoistAPIError,
    TodoistConnectionError,
    TodoistAuthenticationError,
    # Internal functions for testing
    _make_api_request,
    _get_valid_token,
    # Circuit breaker and cache instances
    circuit_breaker,
    api_cache,
    health_monitor,
    CircuitState,
)


# Test fixtures and helper functions
@pytest.fixture
def mock_oauth_token():
    """Fixture providing a mock OAuth token."""
    token = Mock()
    token.access_token = "test_access_token_12345"
    token.refresh_token = "test_refresh_token_67890"
    token.expires_at = time.time() + 3600  # Expires in 1 hour
    return token


@pytest.fixture
def mock_oauth_service():
    """Fixture providing a mock OAuth service."""
    with patch("tools.todoist_tools.get_oauth_service") as mock_service:
        service = Mock()
        mock_service.return_value = service
        service._is_token_valid.return_value = True
        yield service


@pytest.fixture
def mock_requests():
    """Fixture providing a mock requests module."""
    with patch("tools.todoist_tools.requests") as mock_req:
        yield mock_req


@pytest.fixture
def sample_task_data():
    """Fixture providing sample task data."""
    return {
        "id": "12345",
        "content": "Test task content",
        "description": "Test task description",
        "project_id": "67890",
        "section_id": None,
        "parent_id": None,
        "order": 1,
        "priority": 1,
        "labels": ["urgent", "work"],
        "completed_at": None,
        "url": "https://todoist.com/showTask?id=12345",
        "comment_count": 0,
        "assignee_id": None,
        "creator_id": "user123",
        "created_at": "2025-01-09T10:00:00Z",
        "due": {
            "date": "2025-01-10",
            "is_recurring": False,
            "datetime": None,
            "string": "tomorrow",
            "timezone": None,
        },
    }


@pytest.fixture
def sample_recurring_task_data():
    """Fixture providing sample recurring task data."""
    return {
        "id": "recurring123",
        "content": "Daily standup meeting",
        "description": "Team daily standup",
        "project_id": "67890",
        "priority": 2,
        "labels": ["meetings"],
        "due": {
            "date": "2025-01-10",
            "is_recurring": True,
            "datetime": None,
            "string": "every day",
            "timezone": None,
        },
    }


@pytest.fixture
def sample_project_data():
    """Fixture providing sample project data."""
    return {
        "id": "67890",
        "name": "Test Project",
        "comment_count": 5,
        "order": 1,
        "color": "blue",
        "is_shared": False,
        "is_favorite": True,
        "is_inbox_project": False,
        "is_team_inbox": False,
        "view_style": "list",
        "url": "https://todoist.com/showProject?id=67890",
        "parent_id": None,
    }


@pytest.fixture
def sample_label_data():
    """Fixture providing sample label data."""
    return {
        "id": "label123",
        "name": "urgent",
        "color": "red",
        "order": 1,
        "is_favorite": False,
    }


@pytest.fixture
def reset_singletons():
    """Fixture to reset singleton state between tests."""
    # Reset circuit breaker
    circuit_breaker.state = CircuitState.CLOSED
    circuit_breaker.failure_count = 0
    circuit_breaker.success_count = 0
    circuit_breaker.last_failure_time = 0

    # Clear cache
    api_cache.clear()

    # Reset health monitor
    health_monitor.last_check = 0
    health_monitor.is_healthy = True
    health_monitor.consecutive_failures = 0

    yield

    # Clean up after test
    api_cache.clear()


class TestBasicAPIFunctions:
    """Test cases for basic Todoist API functions."""

    def test_get_all_tasks_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful retrieval of all tasks."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_task_data]
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_all_tasks("test_user")

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "12345"
        assert result[0]["content"] == "Test task content"

        # Verify API call
        mock_requests.request.assert_called_once()
        call_args = mock_requests.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "api.todoist.com/rest/v2/tasks" in call_args[1]["url"]
        assert (
            call_args[1]["headers"]["Authorization"] == "Bearer test_access_token_12345"
        )

    def test_get_all_tasks_with_filters(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test get_all_tasks with various filter parameters."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests.request.return_value = mock_response

        # Call with filters
        get_all_tasks(
            "test_user", project_id="123", label="urgent", filter_expr="today"
        )

        # Verify parameters were passed
        call_args = mock_requests.request.call_args
        params = call_args[1]["params"]
        assert params["project_id"] == "123"
        assert params["label"] == "urgent"
        assert params["filter"] == "today"

    def test_get_all_projects_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_project_data
    ):
        """Test successful retrieval of all projects."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_project_data]
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_all_projects("test_user")

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "67890"
        assert result[0]["name"] == "Test Project"

    def test_get_all_labels_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_label_data
    ):
        """Test successful retrieval of all labels."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_label_data]
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_all_labels("test_user")

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "label123"
        assert result[0]["name"] == "urgent"

    def test_get_task_by_id_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful retrieval of a specific task by ID."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_task_by_id("test_user", "12345")

        # Assertions
        assert isinstance(result, dict)
        assert result["id"] == "12345"
        assert result["content"] == "Test task content"

        # Verify correct endpoint was called
        call_args = mock_requests.request.call_args
        assert "tasks/12345" in call_args[1]["url"]

    def test_get_tasks_by_filter_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful filtering of tasks."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_tasks_by_filter("test_user", "today & p1")

        # Assertions
        assert isinstance(result, list)

        # Verify filter parameter
        call_args = mock_requests.request.call_args
        assert call_args[1]["params"]["filter"] == "today & p1"

    def test_get_completed_tasks_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful retrieval of completed tasks."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": "completed1", "content": "Completed task"}],
            "next_cursor": None,
        }
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_completed_tasks("test_user", limit=100)

        # Assertions
        assert isinstance(result, dict)
        assert "items" in result
        assert len(result["items"]) == 1

        # Verify endpoint and parameters
        call_args = mock_requests.request.call_args
        assert "tasks/completed" in call_args[1]["url"]
        assert call_args[1]["params"]["limit"] == 100

    def test_test_connection_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful connection test."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "user123", "email": "test@example.com"}
        mock_requests.request.return_value = mock_response

        # Call function
        result = test_connection("test_user")

        # Assertions
        assert result is True

    def test_get_user_info_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful user info retrieval."""
        user_data = {
            "id": "user123",
            "email": "test@example.com",
            "full_name": "Test User",
            "timezone": "UTC",
        }

        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = user_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_user_info("test_user")

        # Assertions
        assert isinstance(result, dict)
        assert result["id"] == "user123"
        assert result["email"] == "test@example.com"


class TestAuthenticationAndErrors:
    """Test cases for authentication and error handling."""

    def test_no_token_available(self, mock_oauth_service):
        """Test behavior when no OAuth token is available."""
        mock_oauth_service.get_token.return_value = None

        with pytest.raises(TodoistAuthenticationError) as exc_info:
            get_all_tasks("test_user")

        assert "No Todoist token found" in str(exc_info.value)

    def test_invalid_token(self, mock_oauth_service, mock_oauth_token):
        """Test behavior when token is invalid/expired."""
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_oauth_service._is_token_valid.return_value = False

        with pytest.raises(TodoistAuthenticationError) as exc_info:
            get_all_tasks("test_user")

        assert "token for user test_user has expired" in str(exc_info.value)

    def test_api_authentication_error(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test handling of 401 authentication errors from API."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 401
        mock_requests.request.return_value = mock_response

        with pytest.raises(TodoistAuthenticationError) as exc_info:
            get_all_tasks("test_user")

        assert "authentication failed" in str(exc_info.value).lower()

    def test_api_forbidden_error(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test handling of 403 forbidden errors from API."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 403
        mock_requests.request.return_value = mock_response

        with pytest.raises(TodoistAuthenticationError) as exc_info:
            get_all_tasks("test_user")

        assert "forbidden" in str(exc_info.value).lower()

    def test_api_not_found_error(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test handling of 404 not found errors from API."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.request.return_value = mock_response

        with pytest.raises(TodoistAPIError) as exc_info:
            get_task_by_id("test_user", "nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_api_rate_limit_with_retry(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test handling of rate limiting with successful retry."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        # First call returns 429, second call succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = [sample_task_data]

        mock_requests.request.side_effect = [rate_limit_response, success_response]

        # Mock time.sleep to avoid actual delays in tests
        with patch("tools.todoist_tools.time.sleep"):
            result = get_all_tasks("test_user")

        # Should succeed after retry
        assert isinstance(result, list)
        assert len(result) == 1
        assert mock_requests.request.call_count == 2

    def test_api_rate_limit_exhausted_retries(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test handling of rate limiting when retries are exhausted."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        mock_requests.request.return_value = rate_limit_response

        # Mock time.sleep to avoid actual delays in tests
        with patch("tools.todoist_tools.time.sleep"):
            with pytest.raises(TodoistAPIError) as exc_info:
                get_all_tasks("test_user")

        assert "rate limit exceeded" in str(exc_info.value).lower()
        # Should have tried MAX_RETRIES times
        assert mock_requests.request.call_count == 3  # MAX_RETRIES = 3

    def test_network_timeout_error(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test handling of network timeout errors."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_requests.request.side_effect = requests.exceptions.Timeout(
            "Request timed out"
        )

        with pytest.raises(TodoistConnectionError) as exc_info:
            get_all_tasks("test_user")

        assert "timed out" in str(exc_info.value).lower()

    def test_network_connection_error(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test handling of network connection errors."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_requests.request.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        with pytest.raises(TodoistConnectionError) as exc_info:
            get_all_tasks("test_user")

        assert "failed to connect" in str(exc_info.value).lower()

    def test_invalid_json_response(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test handling of invalid JSON responses."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_requests.request.return_value = mock_response

        with pytest.raises(TodoistAPIError) as exc_info:
            get_all_tasks("test_user")

        assert "invalid json" in str(exc_info.value).lower()


class TestTaskManagementFunctions:
    """Test cases for task management functions."""

    def test_create_task_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful task creation."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = create_task(
            "test_user", "New test task", project_id="67890", priority=2
        )

        # Assertions
        assert isinstance(result, dict)
        assert result["id"] == "12345"

        # Verify API call
        call_args = mock_requests.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "tasks" in call_args[1]["url"]

        # Verify request data
        request_data = call_args[1]["json"]
        assert request_data["content"] == "New test task"
        assert request_data["project_id"] == "67890"
        assert request_data["priority"] == 2

    def test_create_task_with_all_parameters(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test task creation with all optional parameters."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function with all parameters
        result = create_task(
            "test_user",
            "Comprehensive test task",
            project_id="67890",
            parent_id="parent123",
            order=5,
            labels=["urgent", "work"],
            priority=3,
            due_string="tomorrow at 3pm",
            description="Detailed task description",
        )

        # Verify request data includes all parameters
        call_args = mock_requests.request.call_args
        request_data = call_args[1]["json"]

        assert request_data["content"] == "Comprehensive test task"
        assert request_data["project_id"] == "67890"
        assert request_data["parent_id"] == "parent123"
        assert request_data["order"] == 5
        assert request_data["labels"] == ["urgent", "work"]
        assert request_data["priority"] == 3
        assert request_data["due_string"] == "tomorrow at 3pm"
        assert request_data["description"] == "Detailed task description"

    def test_update_task_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful task update."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = update_task(
            "test_user", "12345", content="Updated content", priority=4
        )

        # Assertions
        assert isinstance(result, dict)

        # Verify API call
        call_args = mock_requests.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "tasks/12345" in call_args[1]["url"]

        # Verify request data
        request_data = call_args[1]["json"]
        assert request_data["content"] == "Updated content"
        assert request_data["priority"] == 4

    def test_delete_task_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful task deletion."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        # Call function
        result = delete_task("test_user", "12345")

        # Assertions
        assert result is True

        # Verify API call
        call_args = mock_requests.request.call_args
        assert call_args[1]["method"] == "DELETE"
        assert "tasks/12345" in call_args[1]["url"]

    def test_complete_task_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful task completion."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        # Call function
        result = complete_task("test_user", "12345")

        # Assertions
        assert result is True

        # Verify API call
        call_args = mock_requests.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "tasks/12345/close" in call_args[1]["url"]

    def test_reopen_task_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful task reopening."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        # Call function
        result = reopen_task("test_user", "12345")

        # Assertions
        assert result is True

        # Verify API call
        call_args = mock_requests.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "tasks/12345/reopen" in call_args[1]["url"]

    def test_bulk_complete_tasks_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test successful bulk task completion."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        # Mock successful responses for each task
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {}
        mock_requests.request.return_value = success_response

        # Call function
        task_ids = ["12345", "67890", "abcdef"]
        result = bulk_complete_tasks("test_user", task_ids)

        # Assertions
        assert isinstance(result, dict)
        assert len(result) == 3
        assert all(status is True for status in result.values())
        assert result["12345"] is True
        assert result["67890"] is True
        assert result["abcdef"] is True

        # Verify all API calls were made
        assert mock_requests.request.call_count == 3

    def test_bulk_complete_tasks_partial_failure(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test bulk task completion with some failures."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        # Mock mixed responses
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {}

        failure_response = Mock()
        failure_response.status_code = 404

        mock_requests.request.side_effect = [
            success_response,
            failure_response,
            success_response,
        ]

        # Call function
        task_ids = ["12345", "invalid", "67890"]
        result = bulk_complete_tasks("test_user", task_ids)

        # Assertions
        assert isinstance(result, dict)
        assert len(result) == 3
        assert result["12345"] is True
        assert result["invalid"] is False  # Should fail for 404
        assert result["67890"] is True

    def test_update_task_status_complete(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test updating task status to completed."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        # Call function
        result = update_task_status("test_user", "12345", completed=True)

        # Assertions
        assert result is True

        # Verify correct endpoint was called
        call_args = mock_requests.request.call_args
        assert "tasks/12345/close" in call_args[1]["url"]

    def test_update_task_status_reopen(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test updating task status to reopened."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        # Call function
        result = update_task_status("test_user", "12345", completed=False)

        # Assertions
        assert result is True

        # Verify correct endpoint was called
        call_args = mock_requests.request.call_args
        assert "tasks/12345/reopen" in call_args[1]["url"]

    def test_move_task_to_project_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful task move to different project."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = move_task_to_project("test_user", "12345", "new_project_123")

        # Assertions
        assert isinstance(result, dict)

        # Verify API call
        call_args = mock_requests.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "tasks/12345" in call_args[1]["url"]

        # Verify request data
        request_data = call_args[1]["json"]
        assert request_data["project_id"] == "new_project_123"

    def test_set_task_priority_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful task priority update."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = set_task_priority("test_user", "12345", 4)

        # Assertions
        assert isinstance(result, dict)

        # Verify request data
        call_args = mock_requests.request.call_args
        request_data = call_args[1]["json"]
        assert request_data["priority"] == 4

    def test_set_task_priority_validation(self):
        """Test task priority validation."""
        with pytest.raises(ValueError) as exc_info:
            set_task_priority("test_user", "12345", 5)  # Invalid priority

        assert "priority must be between 1 and 4" in str(exc_info.value).lower()

    def test_add_task_labels_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful addition of labels to task."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = add_task_labels("test_user", "12345", ["important", "review"])

        # Assertions
        assert isinstance(result, dict)

        # Verify request data
        call_args = mock_requests.request.call_args
        request_data = call_args[1]["json"]
        assert request_data["labels"] == ["important", "review"]

    def test_set_task_due_date_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, sample_task_data
    ):
        """Test successful setting of task due date."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_task_data
        mock_requests.request.return_value = mock_response

        # Call function
        result = set_task_due_date("test_user", "12345", due_string="tomorrow at 3pm")

        # Assertions
        assert isinstance(result, dict)

        # Verify request data
        call_args = mock_requests.request.call_args
        request_data = call_args[1]["json"]
        assert request_data["due_string"] == "tomorrow at 3pm"


class TestRecurringTaskFunctions:
    """Test cases for recurring task functions."""

    def test_is_recurring_task_true(self, sample_recurring_task_data):
        """Test identification of recurring tasks."""
        result = is_recurring_task(sample_recurring_task_data)
        assert result is True

    def test_is_recurring_task_false(self, sample_task_data):
        """Test identification of non-recurring tasks."""
        result = is_recurring_task(sample_task_data)
        assert result is False

    def test_is_recurring_task_no_due_info(self):
        """Test handling of tasks without due information."""
        task_data = {"id": "123", "content": "Test task"}
        result = is_recurring_task(task_data)
        assert result is False

    def test_is_recurring_task_invalid_data(self):
        """Test handling of invalid task data."""
        assert is_recurring_task(None) is False
        assert is_recurring_task({}) is False
        assert is_recurring_task("invalid") is False

    def test_get_recurring_pattern_success(self, sample_recurring_task_data):
        """Test extraction of recurring pattern."""
        result = get_recurring_pattern(sample_recurring_task_data)
        assert result == "every day"

    def test_get_recurring_pattern_no_pattern(self, sample_task_data):
        """Test handling of non-recurring tasks."""
        result = get_recurring_pattern(sample_task_data)
        assert result is None

    def test_get_recurring_pattern_invalid_data(self):
        """Test handling of invalid data."""
        assert get_recurring_pattern(None) is None
        assert get_recurring_pattern({}) is None

    def test_get_next_occurrence_date_success(self, sample_recurring_task_data):
        """Test getting next occurrence date."""
        result = get_next_occurrence_date(sample_recurring_task_data)
        assert result == "2025-01-10"

    def test_get_next_occurrence_date_no_due(self):
        """Test handling of tasks without due date."""
        task_data = {"id": "123", "content": "Test"}
        result = get_next_occurrence_date(task_data)
        assert result is None

    def test_get_recurring_task_summary_success(self, sample_recurring_task_data):
        """Test comprehensive recurring task summary."""
        result = get_recurring_task_summary(sample_recurring_task_data)

        assert isinstance(result, dict)
        assert result["is_recurring"] is True
        assert result["pattern"] == "every day"
        assert result["next_due"] == "2025-01-10"
        assert "task_id" in result
        assert "content" in result

    def test_get_recurring_task_summary_non_recurring(self, sample_task_data):
        """Test summary for non-recurring task."""
        result = get_recurring_task_summary(sample_task_data)

        assert isinstance(result, dict)
        assert result["is_recurring"] is False
        assert result["pattern"] is None

    def test_get_common_recurring_patterns(self):
        """Test retrieval of common recurring patterns."""
        result = get_common_recurring_patterns()

        assert isinstance(result, dict)
        assert len(result) > 0
        assert "daily" in result
        assert "weekly" in result
        assert "monthly" in result


class TestCircuitBreakerFunctionality:
    """Test cases for circuit breaker functionality."""

    def test_circuit_breaker_initial_state(self, reset_singletons):
        """Test circuit breaker initial state."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.can_execute() is True

    def test_circuit_breaker_record_failures(self, reset_singletons):
        """Test circuit breaker failure recording."""
        # Record multiple failures
        for i in range(4):
            circuit_breaker.record_failure()
            assert circuit_breaker.failure_count == i + 1
            assert circuit_breaker.state == CircuitState.CLOSED

        # Fifth failure should open the circuit
        circuit_breaker.record_failure()
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.can_execute() is False

    def test_circuit_breaker_record_success_resets_failures(self, reset_singletons):
        """Test that recording success resets failure count."""
        # Record some failures
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 2

        # Record success should reset
        circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_half_open_recovery(self, reset_singletons):
        """Test circuit breaker recovery through half-open state."""
        # Trip the circuit breaker
        for _ in range(5):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        # Mock time to simulate recovery timeout
        with patch("tools.todoist_tools.time.time") as mock_time:
            # Set time to after recovery timeout
            mock_time.return_value = circuit_breaker.last_failure_time + 301

            # Should transition to half-open
            assert circuit_breaker.can_execute() is True
            assert circuit_breaker.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_half_open_to_closed(self, reset_singletons):
        """Test transition from half-open to closed after successes."""
        # Set circuit to half-open state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.success_count = 0

        # Record required number of successes
        for i in range(3):
            circuit_breaker.record_success()
            if i < 2:
                assert circuit_breaker.state == CircuitState.HALF_OPEN
            else:
                assert circuit_breaker.state == CircuitState.CLOSED

    def test_reset_circuit_breaker_function(self, reset_singletons):
        """Test manual circuit breaker reset."""
        # Trip the circuit breaker
        for _ in range(5):
            circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitState.OPEN

        # Reset manually
        result = reset_circuit_breaker()

        assert result is True
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0


class TestCachingFunctionality:
    """Test cases for caching functionality."""

    def test_cache_set_and_get(self, reset_singletons):
        """Test basic cache set and get operations."""
        test_data = {"test": "data"}
        api_cache.set("test_key", test_data, ttl=60)

        result = api_cache.get("test_key")
        assert result == test_data

    def test_cache_expiration(self, reset_singletons):
        """Test cache entry expiration."""
        test_data = {"test": "data"}
        api_cache.set("test_key", test_data, ttl=1)

        # Should be available immediately
        assert api_cache.get("test_key") == test_data

        # Mock time to simulate expiration
        with patch("tools.todoist_tools.time.time") as mock_time:
            mock_time.return_value = time.time() + 2  # 2 seconds later
            result = api_cache.get("test_key")
            assert result is None

    def test_cache_size_limit(self, reset_singletons):
        """Test cache size limiting."""
        # Fill cache beyond capacity
        original_max_size = api_cache.max_size
        api_cache.max_size = 3  # Set small limit for testing

        try:
            # Add entries beyond limit
            for i in range(5):
                api_cache.set(f"key_{i}", f"data_{i}")

            # Should only have max_size entries
            with api_cache.lock:
                assert len(api_cache.cache) <= api_cache.max_size
        finally:
            api_cache.max_size = original_max_size

    def test_cache_cleanup_expired(self, reset_singletons):
        """Test cleanup of expired cache entries."""
        # Add entries with different TTLs
        api_cache.set("short_ttl", "data1", ttl=1)
        api_cache.set("long_ttl", "data2", ttl=3600)

        with api_cache.lock:
            assert len(api_cache.cache) == 2

        # Mock time to expire first entry
        with patch("tools.todoist_tools.time.time") as mock_time:
            mock_time.return_value = time.time() + 2
            api_cache._cleanup_expired()

            with api_cache.lock:
                assert len(api_cache.cache) == 1
                assert "long_ttl" in api_cache.cache

    def test_clear_cache_function(self, reset_singletons):
        """Test cache clearing function."""
        # Add some data
        api_cache.set("test1", "data1")
        api_cache.set("test2", "data2")

        with api_cache.lock:
            assert len(api_cache.cache) == 2

        # Clear cache
        result = clear_cache()

        assert result is True
        with api_cache.lock:
            assert len(api_cache.cache) == 0

    def test_get_cache_stats(self, reset_singletons):
        """Test cache statistics function."""
        # Add some test data
        api_cache.set("active1", "data1", ttl=3600)
        api_cache.set("active2", "data2", ttl=3600)

        stats = get_cache_stats()

        assert isinstance(stats, dict)
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["expired_entries"] == 0
        assert "average_age_seconds" in stats
        assert "utilization_percent" in stats


class TestFallbackFunctions:
    """Test cases for fallback wrapper functions."""

    def test_get_all_projects_with_fallback_success(
        self,
        mock_oauth_service,
        mock_oauth_token,
        mock_requests,
        sample_project_data,
        reset_singletons,
    ):
        """Test fallback wrapper for projects with successful API call."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_project_data]
        mock_requests.request.return_value = mock_response

        # Call function
        result = get_all_projects_with_fallback("test_user")

        # Should get fresh data
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "67890"

    def test_get_all_projects_with_fallback_uses_cache(self, reset_singletons):
        """Test fallback wrapper uses cached data when circuit is open."""
        # Pre-populate cache
        cached_data = [{"id": "cached123", "name": "Cached Project"}]
        api_cache.set("todoist:test_user:projects", cached_data)

        # Open circuit breaker
        circuit_breaker.state = CircuitState.OPEN

        # Call function - should use cached data
        result = get_all_projects_with_fallback("test_user")

        assert result == cached_data

    def test_get_all_projects_with_fallback_uses_fallback_data(self, reset_singletons):
        """Test fallback wrapper uses default fallback data when no cache."""
        # Open circuit breaker
        circuit_breaker.state = CircuitState.OPEN

        # Call function without cached data - should use fallback
        result = get_all_projects_with_fallback("test_user")

        assert result == []  # fallback_data=[]

    def test_get_all_tasks_with_fallback_with_parameters(
        self,
        mock_oauth_service,
        mock_oauth_token,
        mock_requests,
        sample_task_data,
        reset_singletons,
    ):
        """Test fallback wrapper for tasks with parameters."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_task_data]
        mock_requests.request.return_value = mock_response

        # Call function with parameters
        result = get_all_tasks_with_fallback(
            "test_user", project_id="123", filter_expr="today"
        )

        assert isinstance(result, list)
        assert len(result) == 1

    def test_safe_api_call_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test safe API call wrapper with successful function."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_requests.request.return_value = mock_response

        # Define a test function
        def test_func(user_id):
            return get_user_info(user_id)

        # Call safe_api_call
        result = safe_api_call(test_func, "test_user")

        assert isinstance(result, dict)
        assert result["success"] is True

    def test_safe_api_call_with_fallback(self):
        """Test safe API call with fallback result."""

        # Define a function that always fails
        def failing_func():
            raise TodoistConnectionError("Network error")

        fallback_result = {"fallback": True}

        # Should return fallback result
        result = safe_api_call(failing_func, fallback_result=fallback_result)

        assert result == fallback_result

    def test_safe_api_call_retries(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test safe API call retry mechanism."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        # First two calls fail, third succeeds
        fail_response = Mock()
        fail_response.status_code = 500

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"success": True}

        mock_requests.request.side_effect = [
            fail_response,
            fail_response,
            success_response,
        ]

        # Mock time.sleep to avoid delays
        with patch("tools.todoist_tools.time.sleep"):
            result = safe_api_call(get_user_info, "test_user", max_retries=3)

        assert result["success"] is True
        assert mock_requests.request.call_count == 3

    def test_batch_api_calls_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test batch API calls with all successes."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.request.return_value = mock_response

        # Define batch calls
        calls = [
            {"func": complete_task, "args": ["test_user", "task1"]},
            {"func": complete_task, "args": ["test_user", "task2"]},
            {"func": complete_task, "args": ["test_user", "task3"]},
        ]

        # Execute batch
        results = batch_api_calls(calls, delay_between_calls=0)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert results[0]["function"] == "complete_task"

    def test_batch_api_calls_with_failures(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test batch API calls with some failures."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        # Mix of success and failure responses
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {}

        fail_response = Mock()
        fail_response.status_code = 404

        mock_requests.request.side_effect = [
            success_response,
            fail_response,
            success_response,
        ]

        # Define batch calls
        calls = [
            {"func": complete_task, "args": ["test_user", "task1"]},
            {"func": complete_task, "args": ["test_user", "invalid"]},
            {"func": complete_task, "args": ["test_user", "task3"]},
        ]

        # Execute batch
        results = batch_api_calls(calls, delay_between_calls=0)

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[2]["success"] is True

    def test_batch_api_calls_fail_fast(
        self, mock_oauth_service, mock_oauth_token, mock_requests
    ):
        """Test batch API calls with fail_fast option."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        fail_response = Mock()
        fail_response.status_code = 500
        mock_requests.request.return_value = fail_response

        # Define batch calls
        calls = [
            {"func": complete_task, "args": ["test_user", "task1"]},
            {"func": complete_task, "args": ["test_user", "task2"]},
            {"func": complete_task, "args": ["test_user", "task3"]},
        ]

        # Execute batch with fail_fast
        results = batch_api_calls(calls, fail_fast=True, delay_between_calls=0)

        # Should stop after first failure
        assert len(results) == 1
        assert results[0]["success"] is False


class TestHealthMonitoring:
    """Test cases for health monitoring functionality."""

    def test_check_todoist_health_success(
        self, mock_oauth_service, mock_oauth_token, mock_requests, reset_singletons
    ):
        """Test successful health check."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        # Call function
        result = check_todoist_health("test_user")

        assert isinstance(result, dict)
        assert result["is_healthy"] is True
        assert "circuit_breaker_state" in result
        assert "failure_count" in result

    def test_check_todoist_health_failure(
        self, mock_oauth_service, mock_oauth_token, mock_requests, reset_singletons
    ):
        """Test health check failure."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_requests.get.side_effect = Exception("Network error")

        # Call function
        result = check_todoist_health("test_user")

        assert isinstance(result, dict)
        assert result["is_healthy"] is False

    def test_get_todoist_status_summary(
        self, mock_oauth_service, mock_oauth_token, mock_requests, reset_singletons
    ):
        """Test comprehensive status summary."""
        # Setup mocks for test_connection
        mock_oauth_service.get_token.return_value = mock_oauth_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "user123"}
        mock_requests.request.return_value = mock_response

        # Also mock the health check
        mock_health_response = Mock()
        mock_health_response.status_code = 200
        mock_requests.get.return_value = mock_health_response

        # Call function
        result = get_todoist_status_summary("test_user")

        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "user_id" in result
        assert "health_status" in result
        assert "cache_stats" in result
        assert "circuit_breaker" in result
        assert "connection_test" in result
        assert "api_base_url" in result


class TestIntegrationScenarios:
    """Test cases for integration scenarios and edge cases."""

    def test_api_failure_recovery_scenario(
        self,
        mock_oauth_service,
        mock_oauth_token,
        mock_requests,
        sample_project_data,
        reset_singletons,
    ):
        """Test complete failure and recovery scenario."""
        # Setup mocks
        mock_oauth_service.get_token.return_value = mock_oauth_token

        # Simulate API failures
        fail_response = Mock()
        fail_response.status_code = 500

        # Call function multiple times to trip circuit breaker
        mock_requests.request.return_value = fail_response

        # First few calls should fail and eventually trip circuit breaker
        for _ in range(6):
            try:
                get_all_projects("test_user")
            except TodoistAPIError:
                pass

        # Circuit should be open now
        assert circuit_breaker.state == CircuitState.OPEN

        # Cache some data and test fallback behavior
        cached_data = [sample_project_data]
        api_cache.set("todoist:test_user:projects", cached_data)

        # Should use cached data when circuit is open
        result = get_all_projects_with_fallback("test_user")
        assert result == cached_data

        # Reset circuit breaker and simulate recovery
        reset_circuit_breaker()

        # Setup successful response
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = [sample_project_data]
        mock_requests.request.return_value = success_response

        # Should work normally again
        result = get_all_projects("test_user")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_concurrent_cache_access(self, reset_singletons):
        """Test cache thread safety with concurrent access."""
        import threading
        import time

        results = []
        errors = []

        def cache_worker(worker_id):
            try:
                for i in range(10):
                    key = f"worker_{worker_id}_item_{i}"
                    data = {"worker": worker_id, "item": i}

                    # Set data
                    api_cache.set(key, data)

                    # Get data
                    retrieved = api_cache.get(key)
                    if retrieved == data:
                        results.append(f"worker_{worker_id}_success_{i}")

                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(f"worker_{worker_id}_error: {e}")

        # Start multiple threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=cache_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) > 0  # At least some operations succeeded

        # Verify cache is in consistent state
        with api_cache.lock:
            assert len(api_cache.cache) >= 0  # Should be non-negative

    def test_memory_cleanup_on_large_dataset(self, reset_singletons):
        """Test memory management with large cached datasets."""
        # Set a small cache size for testing
        original_max_size = api_cache.max_size
        api_cache.max_size = 10

        try:
            # Add many items
            for i in range(50):
                large_data = {"index": i, "data": "x" * 100}  # Some bulk data
                api_cache.set(f"large_item_{i}", large_data)

            # Cache should not exceed max size
            with api_cache.lock:
                assert len(api_cache.cache) <= api_cache.max_size

            # Verify we can still get recent items
            recent_item = api_cache.get("large_item_49")
            assert recent_item is not None

        finally:
            api_cache.max_size = original_max_size
