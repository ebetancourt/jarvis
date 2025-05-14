import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from plugins.todoist.server import (
    initialize_api, list_tasks, add_task, complete_task, update_task,
    search_tasks, get_projects, get_sections, reschedule_task, TodoistError,
    add_project, update_project, delete_project, get_labels, add_label, update_label,
    delete_label, add_comment, get_task_comments, add_recurring_task
)

class MockTask:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.content = kwargs.get('content', '')
        self.project_id = kwargs.get('project_id')
        self.section_id = kwargs.get('section_id')
        self.parent_id = kwargs.get('parent_id')
        self.priority = kwargs.get('priority', 1)
        self.url = kwargs.get('url')
        self.is_completed = kwargs.get('is_completed', False)
        self.created_at = kwargs.get('created_at')
        self.labels = kwargs.get('labels', [])
        self.due = kwargs.get('due')

    def dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class MockDue:
    def __init__(self, date):
        self.date = date
        self.is_past = datetime.strptime(date, "%Y-%m-%d") < datetime.now() if date else False

    def dict(self):
        return {'date': self.date, 'is_past': self.is_past}

class MockProject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockSection:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockComment:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.task_id = kwargs.get('task_id')
        self.content = kwargs.get('content')
        self.posted_at = kwargs.get('posted_at')

class MockLabel:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.color = kwargs.get('color')
        self.order = kwargs.get('order')
        self.is_favorite = kwargs.get('is_favorite', False)

today = datetime.now().strftime("%Y-%m-%d")
MOCK_TASK_DATA = {
    'id': '123',
    'content': 'Test task',
    'project_id': '456',
    'section_id': None,
    'parent_id': None,
    'priority': 1,
    'url': 'https://todoist.com/task/123',
    'is_completed': False,
    'created_at': '2024-03-20T10:00:00Z',
    'labels': ['test', 'important'],
    'due': MockDue(today)
}

MOCK_PROJECT_DATA = {
    'id': '456',
    'name': 'Test Project',
    'color': 'red',
    'parent_id': None,
    'order': 1,
    'is_shared': False,
    'is_favorite': True,
    'url': 'https://todoist.com/project/456'
}

MOCK_SECTION_DATA = {
    'id': '789',
    'name': 'Test Section',
    'project_id': '456',
    'order': 1
}

MOCK_COMMENT_DATA = {
    'id': '789',
    'task_id': '123',
    'content': 'Test comment',
    'posted_at': '2024-03-20T10:00:00Z'
}

MOCK_LABEL_DATA = {
    'id': '456',
    'name': 'test',
    'color': 'red',
    'order': 1,
    'is_favorite': False
}

@pytest.fixture
def mock_todoist_api():
    with patch('plugins.todoist.server.TodoistAPI') as mock:
        mock_api = mock.return_value
        mock_task = MockTask(**MOCK_TASK_DATA)
        mock_project = MockProject(**MOCK_PROJECT_DATA)
        mock_section = MockSection(**MOCK_SECTION_DATA)
        mock_comment = MockComment(**MOCK_COMMENT_DATA)
        mock_label = MockLabel(**MOCK_LABEL_DATA)

        # Create async mocks that return the mock objects
        mock_api.get_tasks = AsyncMock(return_value=[mock_task])
        mock_api.get_task = AsyncMock(return_value=mock_task)
        mock_api.add_task = AsyncMock(return_value=mock_task)
        mock_api.update_task = AsyncMock(return_value=mock_task)
        mock_api.complete_task = AsyncMock(return_value=True)
        mock_api.get_projects = AsyncMock(return_value=[mock_project])
        mock_api.get_sections = AsyncMock(return_value=[mock_section])

        # Project management
        mock_api.add_project = AsyncMock(return_value=mock_project)
        mock_api.update_project = AsyncMock(return_value=mock_project)
        mock_api.delete_project = AsyncMock(return_value=True)
        mock_api.get_project = AsyncMock(return_value=mock_project)

        # Label management
        mock_api.get_labels = AsyncMock(return_value=[mock_label])
        mock_api.add_label = AsyncMock(return_value=mock_label)
        mock_api.update_label = AsyncMock(return_value=mock_label)
        mock_api.delete_label = AsyncMock(return_value=True)
        mock_api.get_label = AsyncMock(return_value=mock_label)

        # Comments
        mock_api.get_comments = AsyncMock(return_value=[mock_comment])
        mock_api.add_comment = AsyncMock(return_value=mock_comment)
        mock_api.update_comment = AsyncMock(return_value=mock_comment)
        mock_api.delete_comment = AsyncMock(return_value=True)
        mock_api.get_comment = AsyncMock(return_value=mock_comment)

        yield mock_api

@pytest.fixture
def initialized_api(mock_todoist_api):
    initialize_api('fake_token')
    return mock_todoist_api

@pytest.mark.asyncio
async def test_list_tasks_no_filter(initialized_api):
    tasks = await list_tasks()
    assert len(tasks) == 1
    assert tasks[0]['id'] == '123'
    assert tasks[0]['content'] == 'Test task'
    initialized_api.get_tasks.assert_called_once()

@pytest.mark.asyncio
async def test_list_tasks_with_project_filter(initialized_api):
    tasks = await list_tasks(project_id='456')
    assert len(tasks) == 1
    assert tasks[0]['project_id'] == '456'

@pytest.mark.asyncio
async def test_list_tasks_with_label_filter(initialized_api):
    tasks = await list_tasks(label='test')
    assert len(tasks) == 1
    assert 'test' in tasks[0]['labels']

@pytest.mark.asyncio
async def test_add_task_basic(initialized_api):
    task = await add_task(
        content='New task',
        project_id='456',
        priority=1
    )
    assert task['content'] == 'Test task'  # Using mock data
    initialized_api.add_task.assert_called_once_with(
        content='New task',
        project_id='456',
        section_id=None,
        parent_id=None,
        priority=1,
        due_string=None,
        due_date=None,
        labels=[]
    )

@pytest.mark.asyncio
async def test_add_task_with_labels(initialized_api):
    task = await add_task(
        content='New task',
        labels=['test', 'important']
    )
    assert task['labels'] == ['test', 'important']
    initialized_api.add_task.assert_called_once()

@pytest.mark.asyncio
async def test_get_projects(initialized_api):
    projects = await get_projects()
    assert len(projects) == 1
    assert projects[0]['id'] == '456'
    assert projects[0]['name'] == 'Test Project'
    initialized_api.get_projects.assert_called_once()

@pytest.mark.asyncio
async def test_get_sections_no_filter(initialized_api):
    sections = await get_sections()
    assert len(sections) == 1
    assert sections[0]['id'] == '789'
    assert sections[0]['name'] == 'Test Section'
    initialized_api.get_sections.assert_called_once()

@pytest.mark.asyncio
async def test_get_sections_with_project_filter(initialized_api):
    sections = await get_sections(project_id='456')
    assert len(sections) == 1
    assert sections[0]['project_id'] == '456'

@pytest.mark.asyncio
async def test_complete_task(initialized_api):
    success = await complete_task('123')
    assert success is True
    initialized_api.complete_task.assert_called_once_with(task_id='123')

@pytest.mark.asyncio
async def test_update_task_basic(initialized_api):
    task = await update_task(
        task_id='123',
        content='Updated task',
        priority=2
    )
    assert task['id'] == '123'
    initialized_api.update_task.assert_called_once_with(
        task_id='123',
        content='Updated task',
        priority=2
    )

@pytest.mark.asyncio
async def test_update_task_with_labels(initialized_api):
    task = await update_task(
        task_id='123',
        labels=['new', 'labels']
    )
    assert task['id'] == '123'
    initialized_api.update_task.assert_called_once_with(
        task_id='123',
        labels=['new', 'labels']
    )

@pytest.mark.asyncio
async def test_search_tasks_basic(initialized_api):
    mock_task = MockTask(**MOCK_TASK_DATA)
    initialized_api.get_tasks.return_value = [mock_task]

    tasks = await search_tasks('test')
    assert len(tasks) == 1
    assert tasks[0]['id'] == '123'
    assert 'relevance_score' in tasks[0]
    initialized_api.get_tasks.assert_called_once()

@pytest.mark.asyncio
async def test_search_tasks_with_filter_string(initialized_api):
    await search_tasks('test', filter_string='today & p1')
    initialized_api.get_tasks.assert_called_once_with(filter='today & p1')

@pytest.mark.asyncio
async def test_search_tasks_with_date_filters(initialized_api):
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    mock_task = MockTask(**{
        **MOCK_TASK_DATA,
        'due': MockDue(today)
    })
    initialized_api.get_tasks.return_value = [mock_task]

    # Test due_after filter
    tasks = await search_tasks('test', due_after=today)
    assert len(tasks) == 1

    # Test due_before filter
    tasks = await search_tasks('test', due_before=tomorrow)
    assert len(tasks) == 1

    # Test both filters
    tasks = await search_tasks('test', due_after=today, due_before=tomorrow)
    assert len(tasks) == 1

@pytest.mark.asyncio
async def test_search_tasks_with_priority(initialized_api):
    mock_task = MockTask(**{**MOCK_TASK_DATA, 'priority': 4, 'content': 'Test task'})
    initialized_api.get_tasks.return_value = [mock_task]

    tasks = await search_tasks('test', priority=4)
    assert len(tasks) == 1
    assert tasks[0]['priority'] == 4

@pytest.mark.asyncio
async def test_search_tasks_with_labels(initialized_api):
    mock_task = MockTask(**{**MOCK_TASK_DATA, 'labels': ['test', 'important']})
    initialized_api.get_tasks.return_value = [mock_task]

    tasks = await search_tasks('test', labels=['test'])
    assert len(tasks) == 1

    tasks = await search_tasks('test', labels=['nonexistent'])
    assert len(tasks) == 0

@pytest.mark.asyncio
async def test_search_tasks_with_completed(initialized_api):
    mock_task = MockTask(**{**MOCK_TASK_DATA, 'is_completed': True, 'content': 'Test task'})
    initialized_api.get_tasks.return_value = [mock_task]

    # Should not include completed tasks by default
    tasks = await search_tasks('test', include_completed=False)
    assert len(tasks) == 0

    # Should include completed tasks when specified
    tasks = await search_tasks('test', include_completed=True)
    assert len(tasks) == 1
    assert tasks[0]['is_completed'] is True

@pytest.mark.asyncio
async def test_search_tasks_fuzzy_matching(initialized_api):
    mock_task = MockTask(**{**MOCK_TASK_DATA, 'content': 'Buy groceries'})
    initialized_api.get_tasks.return_value = [mock_task]

    # Should match with default threshold
    tasks = await search_tasks('buy groseries', fuzzy_threshold=60.0)  # Lower threshold for test
    assert len(tasks) == 1
    assert tasks[0]['content'] == 'Buy groceries'
    assert tasks[0]['relevance_score'] >= 60.0

@pytest.mark.asyncio
async def test_search_tasks_relevance_scoring(initialized_api):
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    task1 = MockTask(**{
        **MOCK_TASK_DATA,
        'content': 'Test task 1',
        'priority': 4,
        'due': MockDue(today)
    })
    task2 = MockTask(**{
        **MOCK_TASK_DATA,
        'id': '124',
        'content': 'Test task 2',
        'priority': 1,
        'due': MockDue(next_week)
    })
    initialized_api.get_tasks.return_value = [task1, task2]

    tasks = await search_tasks('test', fuzzy_threshold=60.0)
    assert len(tasks) == 2
    assert tasks[0]['relevance_score'] > tasks[1]['relevance_score']  # Higher priority task should score better

@pytest.mark.asyncio
async def test_search_tasks_error_handling(initialized_api):
    initialized_api.get_tasks.side_effect = Exception("API error")
    with pytest.raises(TodoistError, match="Failed to search tasks"):
        await search_tasks('test')

@pytest.mark.asyncio
async def test_uninitialized_api():
    # Reset the API to None
    import plugins.todoist.server as server
    server.api = None

    with pytest.raises(TodoistError, match="Todoist API not initialized"):
        await list_tasks()

    with pytest.raises(TodoistError, match="Todoist API not initialized"):
        await add_task(content="Test")

    with pytest.raises(TodoistError, match="Todoist API not initialized"):
        await complete_task("123")

    with pytest.raises(TodoistError, match="Todoist API not initialized"):
        await update_task("123", content="Test")

    with pytest.raises(TodoistError, match="Todoist API not initialized"):
        await search_tasks("test")

    with pytest.raises(TodoistError, match="Todoist API not initialized"):
        await get_projects()

    with pytest.raises(TodoistError, match="Todoist API not initialized"):
        await get_sections()

@pytest.mark.asyncio
async def test_reschedule_task_success(initialized_api):
    task = await reschedule_task(
        task_id='123',
        due_string='tomorrow at 3pm'
    )
    assert task['id'] == '123'
    initialized_api.update_task.assert_called_once_with(
        task_id='123',
        due_string='tomorrow at 3pm'
    )

@pytest.mark.asyncio
async def test_reschedule_task_empty_task_id(initialized_api):
    with pytest.raises(TodoistError, match="task_id cannot be empty"):
        await reschedule_task(task_id='', due_string='tomorrow')

@pytest.mark.asyncio
async def test_reschedule_task_empty_due_string(initialized_api):
    with pytest.raises(TodoistError, match="due_string cannot be empty"):
        await reschedule_task(task_id='123', due_string='')

@pytest.mark.asyncio
async def test_reschedule_task_not_found(initialized_api):
    initialized_api.get_task.side_effect = Exception("Task not found")
    with pytest.raises(TodoistError, match="Failed to reschedule task"):
        await reschedule_task(task_id='123', due_string='tomorrow')

@pytest.mark.asyncio
async def test_reschedule_task_api_error(initialized_api):
    initialized_api.update_task.side_effect = Exception("API error")
    with pytest.raises(TodoistError, match="Failed to reschedule task"):
        await reschedule_task(task_id='123', due_string='tomorrow')

@pytest.mark.asyncio
async def test_add_project(initialized_api):
    project = await add_project(
        name='New Project',
        color='red',
        is_favorite=True
    )
    assert project['name'] == 'Test Project'  # Using mock data
    initialized_api.add_project.assert_called_once_with(
        name='New Project',
        parent_id=None,
        color='red',
        is_favorite=True
    )

@pytest.mark.asyncio
async def test_update_project(initialized_api):
    project = await update_project(
        project_id='456',
        name='Updated Project',
        color='blue',
        is_favorite=True
    )
    assert project['id'] == '456'
    initialized_api.update_project.assert_called_once_with(
        project_id='456',
        name='Updated Project',
        color='blue',
        is_favorite=True
    )

@pytest.mark.asyncio
async def test_delete_project(initialized_api):
    success = await delete_project('456')
    assert success is True
    initialized_api.delete_project.assert_called_once_with(project_id='456')

@pytest.mark.asyncio
async def test_get_labels(initialized_api):
    labels = await get_labels()
    assert len(labels) == 1
    assert labels[0]['id'] == '456'
    assert labels[0]['name'] == 'test'
    initialized_api.get_labels.assert_called_once()

@pytest.mark.asyncio
async def test_add_label(initialized_api):
    label = await add_label(
        name='New Label',
        color='red',
        is_favorite=True
    )
    assert label['name'] == 'test'  # Using mock data
    initialized_api.add_label.assert_called_once_with(
        name='New Label',
        color='red',
        is_favorite=True
    )

@pytest.mark.asyncio
async def test_update_label(initialized_api):
    label = await update_label(
        label_id='456',
        name='Updated Label',
        color='blue',
        is_favorite=True
    )
    assert label['id'] == '456'
    initialized_api.update_label.assert_called_once_with(
        label_id='456',
        name='Updated Label',
        color='blue',
        is_favorite=True
    )

@pytest.mark.asyncio
async def test_delete_label(initialized_api):
    success = await delete_label('456')
    assert success is True
    initialized_api.delete_label.assert_called_once_with(label_id='456')

@pytest.mark.asyncio
async def test_add_comment(initialized_api):
    comment = await add_comment(
        task_id='123',
        content='Test comment'
    )
    assert comment['task_id'] == '123'
    assert comment['content'] == 'Test comment'
    initialized_api.add_comment.assert_called_once_with(
        task_id='123',
        content='Test comment'
    )

@pytest.mark.asyncio
async def test_get_task_comments(initialized_api):
    comments = await get_task_comments('123')
    assert len(comments) == 1
    assert comments[0]['task_id'] == '123'
    assert comments[0]['content'] == 'Test comment'
    initialized_api.get_comments.assert_called_once_with(task_id='123')

@pytest.mark.asyncio
async def test_add_recurring_task(initialized_api):
    task = await add_recurring_task(
        content='Weekly meeting',
        due_string='every monday at 10am',
        project_id='456',
        priority=4,
        labels=['meeting']
    )
    assert task['id'] == '123'  # Using mock data
    initialized_api.add_task.assert_called_once_with(
        content='Weekly meeting',
        due_string='every monday at 10am',
        project_id='456',
        section_id=None,
        priority=4,
        labels=['meeting']
    )

@pytest.mark.asyncio
async def test_add_comment_empty_task_id(initialized_api):
    with pytest.raises(TodoistError, match="task_id cannot be empty"):
        await add_comment(task_id='', content='Test comment')

@pytest.mark.asyncio
async def test_add_comment_empty_content(initialized_api):
    with pytest.raises(TodoistError, match="content cannot be empty"):
        await add_comment(task_id='123', content='')

@pytest.mark.asyncio
async def test_get_task_comments_empty_task_id(initialized_api):
    with pytest.raises(TodoistError, match="task_id cannot be empty"):
        await get_task_comments(task_id='')
