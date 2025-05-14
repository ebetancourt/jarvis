import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from plugins.todoist.plugin import TodoistPlugin
from plugins.todoist.server import TodoistError
from tests.test_todoist_server import MockTask, MockProject, MockLabel, MockComment

@pytest.fixture
def mock_todoist_api():
    with patch('plugins.todoist.server.TodoistAPI') as mock:
        mock_api = mock.return_value
        mock_task = MockTask(**{
            'id': '123',
            'content': 'Test task',
            'project_id': '456',
            'priority': 1,
            'due': MagicMock(date='2024-03-20', dict=lambda: {'date': '2024-03-20'}),
            'url': 'https://todoist.com/task/123',
            'labels': ['test'],
            'is_completed': False
        })
        mock_project = MockProject(**{
            'id': '456',
            'name': 'Test Project',
            'color': 'red',
            'parent_id': None,
            'order': 1,
            'is_shared': False,
            'is_favorite': True,
            'url': 'https://todoist.com/project/456'
        })
        mock_label = MockLabel(**{
            'id': '789',
            'name': 'test',
            'color': 'blue',
            'order': 1,
            'is_favorite': False
        })
        mock_comment = MockComment(**{
            'id': '999',
            'task_id': '123',
            'content': 'Test note',
            'posted_at': '2024-03-20T10:00:00Z'
        })

        # Set up mock responses
        mock_api.get_tasks = AsyncMock(return_value=[mock_task])
        mock_api.add_task = AsyncMock(return_value=mock_task)
        mock_api.get_projects = AsyncMock(return_value=[mock_project])
        mock_api.get_labels = AsyncMock(return_value=[mock_label])
        mock_api.add_comment = AsyncMock(return_value=mock_comment)
        mock_api.complete_task = AsyncMock(return_value=True)
        mock_api.update_task = AsyncMock(return_value=mock_task)
        mock_api.get_task = AsyncMock(return_value=mock_task)

        yield mock_api

@pytest.fixture
def plugin(mock_todoist_api):
    return TodoistPlugin('fake_token')

@pytest.mark.asyncio
async def test_search(plugin):
    results = await plugin.search('test')
    assert len(results) == 1
    assert results[0]['content'] == 'Test task'
    assert results[0]['source'] == 'todoist'
    assert results[0]['source_type'] == 'task'
    assert results[0]['metadata']['task_id'] == '123'

@pytest.mark.asyncio
async def test_create_task_basic(plugin):
    task = await plugin.create_task('New task')
    assert task['task_id'] == '123'
    assert task['content'] == 'Test task'

@pytest.mark.asyncio
async def test_create_task_with_project(plugin):
    task = await plugin.create_task(
        content='New task',
        project_name='Test Project',
        priority=4,
        labels=['test']
    )
    assert task['task_id'] == '123'
    assert task['project_id'] == '456'

@pytest.mark.asyncio
async def test_create_task_with_new_project(plugin, mock_todoist_api):
    new_project = MockProject(**{
        'id': '789',
        'name': 'New Project',
        'color': 'blue',
        'parent_id': None,
        'order': 1,
        'is_shared': False,
        'is_favorite': False,
        'url': 'https://todoist.com/project/789'
    })
    mock_todoist_api.add_project = AsyncMock(return_value=new_project)

    task = await plugin.create_task(
        content='New task',
        project_name='New Project'
    )
    assert task['task_id'] == '123'
    mock_todoist_api.add_project.assert_called_once_with(
        name='New Project',
        parent_id=None,
        color=None,
        is_favorite=False
    )

@pytest.mark.asyncio
async def test_create_recurring_task(plugin):
    task = await plugin.create_task(
        content='Weekly meeting',
        due_string='every monday at 10am',
        is_recurring=True
    )
    assert task['task_id'] == '123'

@pytest.mark.asyncio
async def test_add_note(plugin):
    note = await plugin.add_note('123', 'Test note')
    assert note['comment_id'] == '999'
    assert note['content'] == 'Test note'
    assert note['task_id'] == '123'

@pytest.mark.asyncio
async def test_complete_task(plugin, mock_todoist_api):
    mock_todoist_api.complete_task = AsyncMock(return_value=True)
    success = await plugin.complete_task('123')
    assert success is True
    mock_todoist_api.complete_task.assert_called_once_with(task_id='123')

@pytest.mark.asyncio
async def test_update_task(plugin, mock_todoist_api):
    updated_task = MockTask(**{
        'id': '123',
        'content': 'Updated task',
        'project_id': '456',
        'priority': 4,
        'due': None,
        'url': 'https://todoist.com/task/123',
        'labels': ['test'],
        'is_completed': False
    })
    mock_todoist_api.update_task = AsyncMock(return_value=updated_task)
    mock_todoist_api.get_task = AsyncMock(return_value=updated_task)

    task = await plugin.update_task(
        task_id='123',
        content='Updated task',
        priority=4,
        labels=['test']
    )
    assert task['task_id'] == '123'
    assert task['content'] == 'Updated task'

@pytest.mark.asyncio
async def test_error_handling(plugin, mock_todoist_api):
    # Test search error handling
    mock_todoist_api.get_tasks.side_effect = TodoistError("API error")
    results = await plugin.search('test')
    assert len(results) == 0

    # Test create task error handling
    mock_todoist_api.add_task.side_effect = TodoistError("API error")
    task = await plugin.create_task('New task')
    assert task is None

    # Test add note error handling
    mock_todoist_api.add_comment.side_effect = TodoistError("API error")
    note = await plugin.add_note('123', 'Test note')
    assert note is None

    # Test complete task error handling
    mock_todoist_api.complete_task.side_effect = TodoistError("API error")
    success = await plugin.complete_task('123')
    assert success is False

    # Test update task error handling
    mock_todoist_api.update_task.side_effect = TodoistError("API error")
    task = await plugin.update_task('123', content='Updated task')
    assert task is None

def test_get_tools(plugin):
    tools = plugin.get_tools()
    assert len(tools) == 5
    tool_names = {t['name'] for t in tools}
    assert 'search_todoist' in tool_names
    assert 'create_todoist_task' in tool_names
    assert 'add_todoist_note' in tool_names
    assert 'complete_todoist_task' in tool_names
    assert 'update_todoist_task' in tool_names
