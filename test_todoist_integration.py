#!/usr/bin/env python3
"""
Test script for Todoist API integration.

This script allows you to test the Todoist functionality directly with an API token.
You can get a test token from: https://todoist.com/app/settings/integrations/developer
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from tools.todoist_tools import (
        # Basic API functions
        get_all_tasks,
        get_all_projects,
        get_all_labels,
        get_task_by_id,
        test_connection,
        get_user_info,
        # Task management
        create_task,
        complete_task,
        # Recurring tasks
        is_recurring_task,
        get_recurring_pattern,
        get_recurring_task_summary,
        # Error handling & monitoring
        check_todoist_health,
        get_cache_stats,
        get_todoist_status_summary,
        reset_circuit_breaker,
        clear_cache,
        # Fallback functions
        get_all_projects_with_fallback,
        get_all_tasks_with_fallback,
        safe_api_call,
    )

    # Mock OAuth service for testing
    from unittest.mock import Mock
    from tools import todoist_tools

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class MockOAuthService:
    """Mock OAuth service for testing with API token."""

    def __init__(self, api_token: str):
        self.api_token = api_token

    def get_token(self, service: str, user_id: str):
        """Return mock token with the provided API token."""
        mock_token = Mock()
        mock_token.access_token = self.api_token
        return mock_token

    def _is_token_valid(self, token):
        """Always return True for testing."""
        return True


def setup_mock_oauth(api_token: str):
    """Set up mock OAuth service for testing."""
    mock_service = MockOAuthService(api_token)

    # Patch the get_oauth_service function
    todoist_tools.get_oauth_service = lambda: mock_service

    print(f"✅ Mock OAuth service set up with token: {api_token[:10]}...")


def test_basic_functionality(user_id: str = "test_user"):
    """Test basic Todoist functionality."""
    print("\n🔍 Testing Basic Functionality")
    print("=" * 40)

    try:
        # Test connection
        print("🔗 Testing connection...")
        connection_ok = test_connection(user_id)
        print(f"   Connection: {'✅ Success' if connection_ok else '❌ Failed'}")

        # Get user info
        print("👤 Getting user info...")
        user_info = get_user_info(user_id)
        if user_info:
            print(
                f"   User: {user_info.get('full_name', 'Unknown')} ({user_info.get('email', 'Unknown')})"
            )

        # Get projects
        print("📁 Getting projects...")
        projects = get_all_projects(user_id)
        print(f"   Found {len(projects)} projects")
        for project in projects[:3]:  # Show first 3
            print(f"   - {project['name']} (ID: {project['id']})")

        # Get labels
        print("🏷️ Getting labels...")
        labels = get_all_labels(user_id)
        print(f"   Found {len(labels)} labels")
        for label in labels[:3]:  # Show first 3
            print(f"   - {label['name']} (ID: {label['id']})")

        # Get tasks
        print("📋 Getting tasks...")
        tasks = get_all_tasks(user_id)
        print(f"   Found {len(tasks)} tasks")
        for task in tasks[:5]:  # Show first 5
            status = "✅" if task.get("completed_at") else "⏳"
            print(
                f"   {status} {task['content'][:50]}{'...' if len(task['content']) > 50 else ''}"
            )

        return True

    except Exception as e:
        print(f"❌ Error in basic functionality test: {e}")
        return False


def test_advanced_features(user_id: str = "test_user"):
    """Test advanced features like error handling and caching."""
    print("\n🚀 Testing Advanced Features")
    print("=" * 40)

    try:
        # Test health monitoring
        print("🏥 Checking Todoist health...")
        health = check_todoist_health(user_id)
        print(f"   Healthy: {health.get('is_healthy', False)}")
        print(f"   Circuit state: {health.get('circuit_breaker_state', 'unknown')}")

        # Test fallback functions
        print("🛡️ Testing fallback functions...")
        projects_fallback = get_all_projects_with_fallback(user_id)
        print(f"   Fallback projects: {len(projects_fallback)} found")

        # Test cache stats
        print("💾 Checking cache stats...")
        cache_stats = get_cache_stats()
        print(f"   Cache entries: {cache_stats.get('total_entries', 0)}")
        print(f"   Cache utilization: {cache_stats.get('utilization_percent', 0):.1f}%")

        # Test comprehensive status
        print("📊 Getting comprehensive status...")
        status = get_todoist_status_summary(user_id)
        print(f"   API base: {status.get('api_base_url', 'unknown')}")
        print(f"   Timestamp: {status.get('timestamp', 'unknown')}")

        return True

    except Exception as e:
        print(f"❌ Error in advanced features test: {e}")
        return False


def test_recurring_tasks(user_id: str = "test_user"):
    """Test recurring task functionality."""
    print("\n🔄 Testing Recurring Tasks")
    print("=" * 40)

    try:
        # Get all tasks and find recurring ones
        tasks = get_all_tasks(user_id)
        recurring_tasks = [task for task in tasks if is_recurring_task(task)]

        print(f"📅 Found {len(recurring_tasks)} recurring tasks")

        for task in recurring_tasks[:3]:  # Show first 3
            pattern = get_recurring_pattern(task)
            summary = get_recurring_task_summary(task)
            print(
                f"   🔄 {task['content'][:40]}{'...' if len(task['content']) > 40 else ''}"
            )
            print(f"      Pattern: {pattern}")
            print(f"      Next due: {summary.get('next_due', 'unknown')}")

        return True

    except Exception as e:
        print(f"❌ Error in recurring tasks test: {e}")
        return False


def interactive_mode(user_id: str = "test_user"):
    """Interactive mode for manual testing."""
    print("\n🎮 Interactive Mode")
    print("=" * 40)
    print("Commands:")
    print("  projects - List all projects")
    print("  tasks - List all tasks")
    print("  labels - List all labels")
    print("  health - Check health status")
    print("  cache - Show cache stats")
    print("  clear - Clear cache")
    print("  reset - Reset circuit breaker")
    print("  quit - Exit interactive mode")
    print()

    while True:
        try:
            cmd = input("📝 Command: ").strip().lower()

            if cmd == "quit":
                break
            elif cmd == "projects":
                projects = get_all_projects(user_id)
                for p in projects:
                    print(f"   📁 {p['name']} (ID: {p['id']})")
            elif cmd == "tasks":
                tasks = get_all_tasks(user_id)
                for t in tasks[:10]:  # Limit to 10
                    status = "✅" if t.get("completed_at") else "⏳"
                    print(
                        f"   {status} {t['content'][:60]}{'...' if len(t['content']) > 60 else ''}"
                    )
            elif cmd == "labels":
                labels = get_all_labels(user_id)
                for l in labels:
                    print(f"   🏷️ {l['name']} (ID: {l['id']})")
            elif cmd == "health":
                health = check_todoist_health(user_id)
                print(f"   🏥 Healthy: {health.get('is_healthy', False)}")
                print(
                    f"   🔧 Circuit: {health.get('circuit_breaker_state', 'unknown')}"
                )
            elif cmd == "cache":
                stats = get_cache_stats()
                print(f"   💾 Entries: {stats.get('total_entries', 0)}")
                print(f"   📊 Utilization: {stats.get('utilization_percent', 0):.1f}%")
            elif cmd == "clear":
                clear_cache()
                print("   🗑️ Cache cleared")
            elif cmd == "reset":
                reset_circuit_breaker()
                print("   🔄 Circuit breaker reset")
            else:
                print(f"   ❓ Unknown command: {cmd}")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")


def main():
    """Main test function."""
    print("🎯 Todoist API Integration Test")
    print("=" * 50)

    # Check for API token
    api_token = os.environ.get("TODOIST_API_TOKEN")

    if not api_token:
        print("❌ No Todoist API token found!")
        print()
        print("To test the Todoist integration, you need an API token:")
        print("1. Go to https://todoist.com/app/settings/integrations/developer")
        print("2. Copy your API token")
        print(
            "3. Run this script with: TODOIST_API_TOKEN=your_token_here python test_todoist_integration.py"
        )
        print()
        print("Example:")
        print("  export TODOIST_API_TOKEN=abc123def456")
        print("  python test_todoist_integration.py")
        return

    # Set up mock OAuth
    setup_mock_oauth(api_token)

    user_id = "test_user"

    # Run tests
    print(f"🧪 Running tests for user: {user_id}")

    basic_ok = test_basic_functionality(user_id)
    advanced_ok = test_advanced_features(user_id)
    recurring_ok = test_recurring_tasks(user_id)

    print("\n📊 Test Results")
    print("=" * 40)
    print(f"Basic functionality: {'✅ Pass' if basic_ok else '❌ Fail'}")
    print(f"Advanced features: {'✅ Pass' if advanced_ok else '❌ Fail'}")
    print(f"Recurring tasks: {'✅ Pass' if recurring_ok else '❌ Fail'}")

    if basic_ok:
        print("\n🎮 Starting interactive mode...")
        interactive_mode(user_id)


if __name__ == "__main__":
    main()
