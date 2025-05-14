from typing import List, Dict, Any, Optional
from datetime import datetime
from plugins.todoist.server import (
    initialize_api, search_tasks, add_task, update_task, complete_task,
    add_comment, get_task_comments, add_recurring_task, get_projects,
    get_labels, add_label, TodoistError, add_project, reschedule_filtered_tasks
)

class TodoistPlugin:
    """Plugin for integrating Todoist with the main agent."""

    def __init__(self, api_token: str):
        """Initialize the Todoist plugin.

        Args:
            api_token: Todoist API token
        """
        initialize_api(api_token)
        self.name = "todoist"
        self.description = "Manage Todoist tasks, projects, and labels"

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search Todoist tasks.

        Args:
            query: Search query
            **kwargs: Additional search parameters

        Returns:
            List of matching tasks with metadata
        """
        try:
            result = await search_tasks(query, **kwargs)
            if not result['success']:
                print(f"Error searching Todoist: {result['message']}")
                return []

            return [{
                'content': task['content'],
                'source': 'todoist',
                'source_type': 'task',
                'metadata': {
                    'task_id': task['id'],
                    'project_id': task['project_id'],
                    'priority': task['priority'],
                    'due': task['due'],
                    'url': task['url'],
                    'labels': task['labels'],
                    'relevance_score': task.get('relevance_score', 0)
                }
            } for task in result['tasks']]
        except TodoistError as e:
            print(f"Error searching Todoist: {e}")
            return []

    async def create_task(
        self,
        content: str,
        project_name: Optional[str] = None,
        due_string: Optional[str] = None,
        priority: int = 1,
        labels: Optional[List[str]] = None,
        is_recurring: bool = False
    ) -> Dict[str, Any]:
        """Create a new task in Todoist.

        Args:
            content: Task content/description
            project_name: Optional project name (will be created if doesn't exist)
            due_string: Optional due date in natural language
            priority: Task priority (1-4)
            labels: Optional list of labels
            is_recurring: Whether this is a recurring task

        Returns:
            Created task details
        """
        try:
            # Handle project creation/lookup
            project_id = None
            if project_name:
                projects = await get_projects()
                project = next((p for p in projects if p['name'].lower() == project_name.lower()), None)
                if not project:
                    # Create new project
                    project = await add_project(name=project_name)
                project_id = project['id']

            # Handle labels
            if labels:
                existing_labels = await get_labels()
                existing_label_names = {l['name'].lower() for l in existing_labels}

                # Create any missing labels
                for label in labels:
                    if label.lower() not in existing_label_names:
                        await add_label(name=label)

            # Create the task
            if is_recurring:
                task = await add_recurring_task(
                    content=content,
                    due_string=due_string,
                    project_id=project_id,
                    priority=priority,
                    labels=labels
                )
            else:
                task = await add_task(
                    content=content,
                    project_id=project_id,
                    priority=priority,
                    due_string=due_string,
                    labels=labels
                )

            return {
                'task_id': task['id'],
                'content': task['content'],
                'project_id': task['project_id'],
                'url': task['url']
            }

        except TodoistError as e:
            print(f"Error creating Todoist task: {e}")
            return None

    async def add_note(self, task_id: str, content: str) -> Dict[str, Any]:
        """Add a note (comment) to a task.

        Args:
            task_id: Task ID
            content: Note content

        Returns:
            Created comment details
        """
        try:
            comment = await add_comment(task_id=task_id, content=content)
            return {
                'comment_id': comment['id'],
                'content': comment['content'],
                'task_id': comment['task_id'],
                'posted_at': comment['posted_at']
            }
        except TodoistError as e:
            print(f"Error adding note to Todoist task: {e}")
            return None

    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as complete.

        Args:
            task_id: Task ID

        Returns:
            True if successful, False otherwise
        """
        try:
            return await complete_task(task_id)
        except TodoistError as e:
            print(f"Error completing Todoist task: {e}")
            return False

    async def update_task(
        self,
        task_id: str,
        content: Optional[str] = None,
        due_string: Optional[str] = None,
        priority: Optional[int] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update a task.

        Args:
            task_id: Task ID
            content: Optional new content
            due_string: Optional new due date
            priority: Optional new priority
            labels: Optional new labels

        Returns:
            Updated task details
        """
        try:
            task = await update_task(
                task_id=task_id,
                content=content,
                due_string=due_string,
                priority=priority,
                labels=labels
            )
            return {
                'task_id': task['id'],
                'content': task['content'],
                'project_id': task['project_id'],
                'url': task['url']
            }
        except TodoistError as e:
            print(f"Error updating Todoist task: {e}")
            return None

    async def reschedule_overdue(self, due_string: str = "today") -> Dict[str, Any]:
        """Reschedule all overdue tasks to a new due date.

        Args:
            due_string: Natural language due date (e.g. "today", "tomorrow")

        Returns:
            Dict with success status and results
        """
        try:
            result = await reschedule_filtered_tasks("overdue", due_string)
            return result
        except TodoistError as e:
            print(f"Error rescheduling overdue tasks: {e}")
            return {
                "success": False,
                "message": f"Error rescheduling overdue tasks: {str(e)}",
                "tasks": []
            }

    async def reschedule_tasks_by_filter(self, filter_string: str, due_string: str) -> Dict[str, Any]:
        """Reschedule tasks matching a filter to a new due date.

        Args:
            filter_string: Todoist filter query (e.g. "today", "7 days", "no date")
            due_string: Natural language due date (e.g. "tomorrow", "next Monday")

        Returns:
            Dict with success status and results
        """
        try:
            result = await reschedule_filtered_tasks(filter_string, due_string)
            return result
        except TodoistError as e:
            print(f"Error rescheduling tasks with filter '{filter_string}': {e}")
            return {
                "success": False,
                "message": f"Error rescheduling tasks: {str(e)}",
                "tasks": []
            }

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the list of tools provided by this plugin."""
        return [
            {
                "name": "search_todoist",
                "description": "Search for tasks in Todoist",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "filter_string": {
                            "type": "string",
                            "description": "Optional Todoist filter (e.g. 'today', 'overdue')"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Filter by priority (1-4)"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by labels"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_todoist_task",
                "description": "Create a new task in Todoist",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Task content/description"
                        },
                        "project_name": {
                            "type": "string",
                            "description": "Optional project name"
                        },
                        "due_string": {
                            "type": "string",
                            "description": "Due date in natural language"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority level (1-4)"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to apply"
                        },
                        "is_recurring": {
                            "type": "boolean",
                            "description": "Whether this is a recurring task"
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "add_todoist_note",
                "description": "Add a note to a Todoist task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        },
                        "content": {
                            "type": "string",
                            "description": "Note content"
                        }
                    },
                    "required": ["task_id", "content"]
                }
            },
            {
                "name": "complete_todoist_task",
                "description": "Mark a Todoist task as complete",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "update_todoist_task",
                "description": "Update a Todoist task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        },
                        "content": {
                            "type": "string",
                            "description": "New task content"
                        },
                        "due_string": {
                            "type": "string",
                            "description": "New due date in natural language"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "New priority level (1-4)"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New labels"
                        }
                    },
                    "required": ["task_id"]
                }
            }
        ]
