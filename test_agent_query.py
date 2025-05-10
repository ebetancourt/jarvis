import unittest
from unittest.mock import patch, MagicMock

# We'll assume agent_query.py will expose a function agent_query(question: str)
# that returns a dict with 'result' and 'sources'.


class TestAgentQuery(unittest.TestCase):
    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_notes_only_query(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        # Simulate agent routing to notes only
        mock_search_notes.return_value = {
            "result": "notes answer",
            "source_documents": ["note1.md"],
        }
        mock_search_gmail.return_value = {"result": "", "source_documents": []}
        agent = MagicMock()
        agent.invoke.return_value = {
            "tool": "search_notes",
            "query": "What is in my notes?",
        }
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        result = agent_query("What is in my notes?")
        mock_search_notes.assert_called_once()
        mock_search_gmail.assert_not_called()
        self.assertIn("notes answer", result["result"])
        self.assertIn("note1.md", result["sources"])

    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_gmail_only_query(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        mock_search_notes.return_value = {"result": "", "source_documents": []}
        mock_search_gmail.return_value = {
            "result": "gmail answer",
            "source_documents": ["email1"],
        }
        agent = MagicMock()
        agent.invoke.return_value = {
            "tool": "search_gmail",
            "query": "What emails did I get?",
        }
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        result = agent_query("What emails did I get?")
        mock_search_gmail.assert_called_once()
        mock_search_notes.assert_not_called()
        self.assertIn("gmail answer", result["result"])
        self.assertIn("email1", result["sources"])

    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_ambiguous_query_calls_both(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        mock_search_notes.return_value = {
            "result": "notes info",
            "source_documents": ["note2.md"],
        }
        mock_search_gmail.return_value = {
            "result": "gmail info",
            "source_documents": ["email2"],
        }
        agent = MagicMock()
        agent.invoke.return_value = {
            "tool": "both",
            "query": "What did I write or receive about project X?",
        }
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        result = agent_query("What did I write or receive about project X?")
        mock_search_notes.assert_called_once()
        mock_search_gmail.assert_called_once()
        self.assertIn("notes info", result["result"])
        self.assertIn("gmail info", result["result"])
        self.assertIn("note2.md", result["sources"])
        self.assertIn("email2", result["sources"])

    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_unknown_tool(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        agent = MagicMock()
        agent.invoke.return_value = {"tool": "unknown_tool", "query": "???"}
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        result = agent_query("What is this?")
        self.assertIn("could not route", result["result"])
        self.assertEqual(result["sources"], [])

    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_malformed_agent_response(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        agent = MagicMock()
        agent.invoke.return_value = {"not_tool": "oops"}
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        # Should handle missing 'tool' key gracefully
        result = agent_query("Malformed?")
        self.assertIn("could not route", result["result"])
        self.assertEqual(result["sources"], [])

    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_search_notes_raises_exception(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        mock_search_notes.side_effect = Exception("notes error")
        agent = MagicMock()
        agent.invoke.return_value = {"tool": "search_notes", "query": "fail"}
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        with self.assertRaises(Exception):
            agent_query("fail")

    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_search_gmail_raises_exception(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        mock_search_gmail.side_effect = Exception("gmail error")
        agent = MagicMock()
        agent.invoke.return_value = {"tool": "search_gmail", "query": "fail"}
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        with self.assertRaises(Exception):
            agent_query("fail")

    @patch("agent_query.search_notes")
    @patch("agent_query.search_gmail")
    @patch("agent_query.create_agent")
    def test_both_tools_with_overlapping_sources(
        self, mock_create_agent, mock_search_gmail, mock_search_notes
    ):
        mock_search_notes.return_value = {
            "result": "notes info",
            "source_documents": ["shared.md", "note3.md"],
        }
        mock_search_gmail.return_value = {
            "result": "gmail info",
            "source_documents": ["shared.md", "email3"],
        }
        agent = MagicMock()
        agent.invoke.return_value = {
            "tool": "both",
            "query": "Show me everything about shared.md",
        }
        mock_create_agent.return_value = agent
        from agent_query import agent_query

        result = agent_query("Show me everything about shared.md")
        self.assertIn("notes info", result["result"])
        self.assertIn("gmail info", result["result"])
        # Should include all sources, even if overlapping (current logic)
        self.assertEqual(result["sources"].count("shared.md"), 2)
        self.assertIn("note3.md", result["sources"])
        self.assertIn("email3", result["sources"])

    @patch("agent_query.search_notes")
    @patch("agent_query.create_agent")
    def test_empty_string_query(self, mock_create_agent, mock_search_notes):
        agent = MagicMock()
        agent.invoke.return_value = {"tool": "search_notes", "query": ""}
        mock_create_agent.return_value = agent
        mock_search_notes.return_value = {"result": "", "source_documents": []}
        from agent_query import agent_query

        # Should not raise
        result = agent_query("")
        self.assertIn("result", result)

    @patch("agent_query.search_notes")
    @patch("agent_query.create_agent")
    def test_none_query(self, mock_create_agent, mock_search_notes):
        agent = MagicMock()
        agent.invoke.return_value = {"tool": "search_notes", "query": None}
        mock_create_agent.return_value = agent
        mock_search_notes.return_value = {"result": "", "source_documents": []}
        from agent_query import agent_query

        # Should not raise
        result = agent_query(None)
        self.assertIn("result", result)


if __name__ == "__main__":
    unittest.main()
