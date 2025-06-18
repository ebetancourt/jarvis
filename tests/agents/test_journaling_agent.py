"""
Tests for the current tool-based journaling agent implementation.

The journaling agent is now implemented as a set of LangGraph tools rather than
a conversational state management system. These tests validate the tool interfaces
and basic functionality.
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def _import_journaling_agent():
    """Import the journaling agent module dynamically."""
    try:
        # Try direct import first
        import agents.journaling_agent as journaling_agent

        return journaling_agent
    except ImportError:
        # Fallback for when __file__ is not available (e.g., in exec context)
        import importlib.util

        module_path = os.path.join("src", "agents", "journaling_agent.py")
        spec = importlib.util.spec_from_file_location("journaling_agent", module_path)
        journaling_agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(journaling_agent)
        return journaling_agent


journaling_agent = _import_journaling_agent()


@pytest.fixture
def temp_journal_dir():
    """Create a temporary directory for journal files during testing."""
    temp_dir = tempfile.mkdtemp()
    journal_dir = os.path.join(temp_dir, "journal")
    os.makedirs(journal_dir, exist_ok=True)

    # Mock the journal directory
    with patch("tools.journal_tools.get_journal_directory", return_value=journal_dir):
        yield journal_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestJournalingAgentStructure:
    """Test the structure and interface of the journaling agent."""

    def test_agent_exports_tools_list(self):
        """Test that the agent exports a tools list."""
        assert hasattr(journaling_agent, "tools"), "Agent should export tools list"
        tools = journaling_agent.tools
        assert isinstance(tools, list), "Tools should be a list"
        assert len(tools) > 0, "Tools list should not be empty"

    def test_agent_exports_agent_instance(self):
        """Test that the agent exports a journaling_agent instance."""
        assert hasattr(
            journaling_agent, "journaling_agent"
        ), "Should export journaling_agent instance"
        agent = journaling_agent.journaling_agent
        assert agent is not None, "Agent instance should not be None"

    def test_tool_functions_exist(self):
        """Test that expected tool functions are defined."""
        expected_tools = [
            "create_daily_file",
            "add_timestamp_entry",
            "save_journal_entry_with_summary",
            "search_by_date_range",
            "search_by_keywords",
            "search_by_mood",
            "search_by_topics",
            "add_metadata_to_entry",
            "get_journal_metadata",
            "count_words",
        ]

        for tool_name in expected_tools:
            assert hasattr(
                journaling_agent, tool_name
            ), f"Missing tool function: {tool_name}"
            tool_func = getattr(journaling_agent, tool_name)
            assert callable(tool_func), f"Tool {tool_name} should be callable"

    def test_tools_have_langchain_tool_decorator(self):
        """Test that tools have the @tool decorator (LangChain tool interface)."""
        # Check a few key tools for the tool decorator
        key_tools = ["create_daily_file", "add_timestamp_entry", "search_by_keywords"]

        for tool_name in key_tools:
            tool_func = getattr(journaling_agent, tool_name)
            # Check if it has tool attributes (added by @tool decorator)
            assert hasattr(tool_func, "name") or hasattr(
                tool_func, "func"
            ), f"Tool {tool_name} should have @tool decorator"


class TestJournalingAgentTools:
    """Test individual journaling agent tools."""

    def test_create_daily_file_tool(self):
        """Test the create_daily_file tool."""
        create_daily_file = journaling_agent.create_daily_file

        # Test with invalid date format
        result = create_daily_file("invalid-date")
        assert "❌" in result, "Should return error message for invalid date"
        assert "Invalid date format" in result, "Should mention invalid date format"

    def test_add_timestamp_entry_tool(self):
        """Test the add_timestamp_entry tool."""
        add_timestamp_entry = journaling_agent.add_timestamp_entry

        # Test with empty content
        result = add_timestamp_entry("")
        assert "❌" in result, "Should return error message for empty content"
        assert "empty journal entry" in result.lower(), "Should mention empty entry"

    def test_search_by_keywords_tool(self):
        """Test the search_by_keywords tool."""
        search_by_keywords = journaling_agent.search_by_keywords

        # Test with empty keywords
        result = search_by_keywords("")
        assert "❌" in result, "Should return error message for empty keywords"
        assert "keywords" in result.lower(), "Should mention keywords"

    def test_search_by_mood_tool(self):
        """Test the search_by_mood tool."""
        search_by_mood = journaling_agent.search_by_mood

        # Test with empty mood
        result = search_by_mood("")
        assert "❌" in result, "Should return error message for empty mood"
        assert "mood" in result.lower(), "Should mention mood"

    def test_count_words_tool(self):
        """Test the count_words tool."""
        count_words = journaling_agent.count_words

        # Test with sample text
        result = count_words("This is a test sentence.")
        assert "Word count:" in result, "Should return word count"
        assert "5 words" in result, "Should count 5 words correctly"

    def test_add_metadata_to_entry_tool(self):
        """Test the add_metadata_to_entry tool."""
        add_metadata_to_entry = journaling_agent.add_metadata_to_entry

        # Test with non-existent file (should handle gracefully)
        result = add_metadata_to_entry("/non/existent/file.md", mood="happy")
        assert "Error" in result, "Should return error for non-existent file"


class TestJournalingAgentIntegration:
    """Test integration aspects of the journaling agent."""

    @patch("tools.journal_tools._create_daily_file")
    def test_create_daily_file_integration(self, mock_create, temp_journal_dir):
        """Test create_daily_file tool integration."""
        mock_create.return_value = "/path/to/file.md"

        create_daily_file = journaling_agent.create_daily_file
        result = create_daily_file()

        assert "✅" in result, "Should return success message"
        assert "journal file created" in result.lower(), "Should mention file creation"

    @patch("tools.journal_tools._add_timestamp_entry")
    def test_add_timestamp_entry_integration(self, mock_add, temp_journal_dir):
        """Test add_timestamp_entry tool integration."""
        mock_add.return_value = "/path/to/file.md"

        add_timestamp_entry = journaling_agent.add_timestamp_entry
        result = add_timestamp_entry("Test journal entry")

        assert "✅" in result, "Should return success message"
        assert "entry added" in result.lower(), "Should mention entry addition"

    @patch("tools.journal_tools._search_by_keywords")
    def test_search_by_keywords_integration(self, mock_search, temp_journal_dir):
        """Test search_by_keywords tool integration."""
        # Mock empty results
        mock_search.return_value = []

        search_by_keywords = journaling_agent.search_by_keywords
        result = search_by_keywords("test keywords")

        assert "🔍" in result, "Should use search emoji"
        assert "No journal entries found" in result, "Should handle empty results"

    def test_error_handling_patterns(self):
        """Test that tools follow consistent error handling patterns."""
        # Test a few tools to ensure they use consistent error patterns
        tools_to_test = [
            ("create_daily_file", ["invalid-date-format"]),
            ("add_timestamp_entry", [""]),  # Empty content
            ("search_by_keywords", [""]),  # Empty keywords
            ("search_by_mood", [""]),  # Empty mood
        ]

        for tool_name, test_args in tools_to_test:
            tool_func = getattr(journaling_agent, tool_name)
            result = tool_func(*test_args)

            # Should use emoji indicators for errors
            assert any(
                emoji in result for emoji in ["❌", "⚠️"]
            ), f"Tool {tool_name} should use error emoji indicators"

            # Should provide user-friendly error messages
            assert (
                len(result) > 10
            ), f"Tool {tool_name} should provide descriptive error messages"


class TestJournalingAgentValidation:
    """Validation tests for the journaling agent."""

    def test_tools_list_contains_all_functions(self):
        """Test that the tools list contains all expected tool functions."""
        tools = journaling_agent.tools
        tool_names = [
            tool.name if hasattr(tool, "name") else str(tool) for tool in tools
        ]

        expected_tools = [
            "create_daily_file",
            "add_timestamp_entry",
            "save_journal_entry_with_summary",
            "search_by_date_range",
            "search_by_keywords",
            "search_by_mood",
            "search_by_topics",
            "add_metadata_to_entry",
            "get_journal_metadata",
            "count_words",
        ]

        for expected_tool in expected_tools:
            # Check if tool name appears in the tools list (may have different formats)
            tool_present = any(
                expected_tool in str(tool_name) for tool_name in tool_names
            )
            assert tool_present, f"Tool {expected_tool} should be in tools list"

    def test_agent_has_proper_configuration(self):
        """Test that the agent is properly configured."""
        agent = journaling_agent.journaling_agent
        assert agent is not None, "Agent should be configured"

        # The agent should be a LangGraph agent with tools
        # We can't easily test the internal structure without knowing LangGraph internals,
        # but we can at least verify it exists and is not None


if __name__ == "__main__":
    # Basic validation when run directly
    print("🧪 Running basic journaling agent validation...")

    # Test imports
    agent_module = _import_journaling_agent()
    print("✅ Agent module imported successfully")

    # Test structure
    assert hasattr(agent_module, "tools"), "Agent should have tools"
    assert hasattr(agent_module, "journaling_agent"), "Agent should have agent instance"
    print("✅ Agent structure is valid")

    # Test tool functions exist
    expected_tools = ["create_daily_file", "add_timestamp_entry", "search_by_keywords"]
    for tool in expected_tools:
        assert hasattr(agent_module, tool), f"Missing tool: {tool}"
    print("✅ Core tools are present")

    print("🎉 Journaling agent validation completed!")
