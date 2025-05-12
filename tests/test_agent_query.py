import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch, MagicMock
from core.agent_query import agent_query

# We'll assume agent_query.py will expose a function agent_query(question: str)
# that returns a dict with 'result' and 'sources'.


def patch_agent_query_tools(monkeypatch, notes_return, gmail_return, agent_return):
    monkeypatch.setattr("core.agent_query.search_notes", lambda q: notes_return)
    monkeypatch.setattr("core.agent_query.search_gmail", lambda q: gmail_return)
    agent = MagicMock()
    agent.invoke.return_value = agent_return
    monkeypatch.setattr("core.agent_query.create_agent", lambda: agent)


def test_notes_only_query(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "notes answer", "source_documents": ["note1.md"]},
        {"result": "", "source_documents": []},
        {"tool": "search_notes", "query": "What is in my notes?"},
    )
    from core.agent_query import agent_query

    result = agent_query("What is in my notes?")
    assert "notes answer" in result["result"]
    assert "note1.md" in result["sources"]


def test_gmail_only_query(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "", "source_documents": []},
        {"result": "gmail answer", "source_documents": ["email1"]},
        {"tool": "search_gmail", "query": "What emails did I get?"},
    )
    from core.agent_query import agent_query

    result = agent_query("What emails did I get?")
    assert "gmail answer" in result["result"]
    assert "email1" in result["sources"]


def test_ambiguous_query_calls_both(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "notes info", "source_documents": ["note2.md"]},
        {"result": "gmail info", "source_documents": ["email2"]},
        {"tool": "both", "query": "What did I write or receive about project X?"},
    )
    from core.agent_query import agent_query

    result = agent_query("What did I write or receive about project X?")
    assert "notes info" in result["result"]
    assert "gmail info" in result["result"]
    assert "note2.md" in result["sources"]
    assert "email2" in result["sources"]


def test_unknown_tool(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "", "source_documents": []},
        {"result": "", "source_documents": []},
        {"tool": "unknown_tool", "query": "???"},
    )
    from core.agent_query import agent_query

    result = agent_query("What is this?")
    assert "could not route" in result["result"]
    assert result["sources"] == []


def test_malformed_agent_response(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "", "source_documents": []},
        {"result": "", "source_documents": []},
        {"not_tool": "oops"},
    )
    from core.agent_query import agent_query

    result = agent_query("Malformed?")
    assert "could not route" in result["result"]
    assert result["sources"] == []


def test_search_notes_raises_exception(monkeypatch):
    from core.agent_query import agent_query

    def raise_exc(q):
        raise Exception("notes error")

    monkeypatch.setattr("core.agent_query.search_notes", raise_exc)
    agent = MagicMock()
    agent.invoke.return_value = {"tool": "search_notes", "query": "fail"}
    monkeypatch.setattr("core.agent_query.create_agent", lambda: agent)
    with pytest.raises(Exception):
        agent_query("fail")


def test_search_gmail_raises_exception(monkeypatch):
    from core.agent_query import agent_query

    def raise_exc(q):
        raise Exception("gmail error")

    monkeypatch.setattr("core.agent_query.search_gmail", raise_exc)
    agent = MagicMock()
    agent.invoke.return_value = {"tool": "search_gmail", "query": "fail"}
    monkeypatch.setattr("core.agent_query.create_agent", lambda: agent)
    with pytest.raises(Exception):
        agent_query("fail")


def test_both_tools_with_overlapping_sources(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "notes info", "source_documents": ["shared.md", "note3.md"]},
        {"result": "gmail info", "source_documents": ["shared.md", "email3"]},
        {"tool": "both", "query": "Show me everything about shared.md"},
    )
    from core.agent_query import agent_query

    result = agent_query("Show me everything about shared.md")
    assert "notes info" in result["result"]
    assert "gmail info" in result["result"]
    assert result["sources"].count("shared.md") == 2
    assert "note3.md" in result["sources"]
    assert "email3" in result["sources"]


def test_empty_string_query(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "", "source_documents": []},
        {"result": "", "source_documents": []},
        {"tool": "search_notes", "query": ""},
    )
    from core.agent_query import agent_query

    result = agent_query("")
    assert "result" in result


def test_none_query(monkeypatch):
    patch_agent_query_tools(
        monkeypatch,
        {"result": "", "source_documents": []},
        {"result": "", "source_documents": []},
        {"tool": "search_notes", "query": None},
    )
    from core.agent_query import agent_query

    result = agent_query(None)
    assert "result" in result
