"""Module containing Todoist filter documentation and helper functions."""

FILTER_DOCUMENTATION = '''# Todoist Filter Syntax Guide

When creating Todoist filter queries, follow these rules:

## Basic Filters
- `today` - Tasks due today
- `overdue` - Overdue tasks
- `no date` - Tasks without a due date
- `7 days` - Tasks due in next 7 days
- `view all` - All active tasks

## Operators
- `|` - OR operator (e.g., `today | overdue`)
- `&` - AND operator (e.g., `today & p1`)
- `!` - NOT operator
- `()` - Group conditions (e.g., `(today | overdue) & @work`)
- `,` - Separate queries into different lists (e.g., `today, overdue`)

## Priority Filters
- `p1` - Priority 1 (highest)
- `p2` - Priority 2
- `p3` - Priority 3
- `p4` - Priority 4 (lowest)

## Common Patterns
- Today's and overdue tasks: `(today | overdue)`
- High priority tasks due soon: `(p1 | p2) & 7 days`
- Work tasks for today: `#Work & today`

## Important Notes
1. Filters only work on active tasks - completed tasks are not included by default
2. Don't use `!completed` or similar completion status filters
3. For date ranges, use `date before:` and `date after:`
4. Labels use @ prefix (e.g., `@work`)
5. Projects use # prefix (e.g., `#Work`)

## Examples
- Tasks due today or overdue in Work project: `(today | overdue) & #Work`
- High priority tasks due this week: `(p1 | p2) & 7 days`
- Tasks with no date in Work project: `#Work & no date`
- Tasks due today with work label: `today & @work`
'''

# Common filter patterns that can be used directly
DEFAULT_FILTERS = {
    'today_and_overdue': '(today | overdue)',
    'high_priority_soon': '(p1 | p2) & 7 days',
    'no_date': 'no date',
    'next_week': '7 days',
    'all_active': 'view all'
}

def get_filter_help() -> str:
    """Return the filter documentation as a formatted string."""
    return FILTER_DOCUMENTATION

def get_default_filter(name: str) -> str:
    """Get a predefined filter by name.

    Args:
        name: Name of the filter pattern to retrieve

    Returns:
        The filter string or None if not found
    """
    return DEFAULT_FILTERS.get(name)
