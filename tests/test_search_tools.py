import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from common.get_vector_store import get_vector_store
import search_tools
from langchain.schema import Document

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def mock_vector_store():
    vs = get_vector_store(db_type="chromadb", config={})
    vs.db = MagicMock()
    docs = [
        Document(
            page_content="Note 1", metadata={"source": "obsidian", "deleted": False}
        ),
        Document(
            page_content="Note 2", metadata={"source": "obsidian", "deleted": False}
        ),
        Document(
            page_content="Email 1", metadata={"source": "Gmail", "deleted": False}
        ),
        Document(
            page_content="Deleted Note",
            metadata={"source": "obsidian", "deleted": True},
        ),
    ]
    return vs, docs


def test_get_notes_retriever_filters_obsidian(mock_vector_store):
    vs, docs = mock_vector_store
    vs.db.as_retriever = lambda **kwargs: [d for d in docs if kwargs["filter_func"](d)]
    retriever = vs.get_notes_retriever()
    assert all(
        d.metadata["source"] == "obsidian" and not d.metadata["deleted"]
        for d in retriever
    )
    assert len(retriever) == 2


def test_get_gmail_retriever_filters_gmail(mock_vector_store):
    vs, docs = mock_vector_store
    vs.db.as_retriever = lambda **kwargs: [d for d in docs if kwargs["filter_func"](d)]
    retriever = vs.get_gmail_retriever()
    assert all(
        d.metadata["source"] == "Gmail" and not d.metadata["deleted"] for d in retriever
    )
    assert len(retriever) == 1


@patch("search_tools.ChatOpenAI")
@patch("search_tools.load_db")
@patch("search_tools.RetrievalQA")
def test_search_notes_calls_notes_retriever(
    mock_retrievalqa, mock_load_db, mock_chatopenai
):
    mock_vs = MagicMock()
    mock_load_db.return_value = mock_vs
    mock_vs.get_notes_retriever.return_value = "notes_retriever"
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {"result": "answer", "source_documents": []}
    mock_retrievalqa.from_chain_type.return_value = mock_chain
    result = search_tools.search_notes("test query")
    mock_vs.get_notes_retriever.assert_called()
    assert result["result"] == "answer"


@patch("search_tools.ChatOpenAI")
@patch("search_tools.load_db")
@patch("search_tools.RetrievalQA")
def test_search_gmail_calls_gmail_retriever(
    mock_retrievalqa, mock_load_db, mock_chatopenai
):
    mock_vs = MagicMock()
    mock_load_db.return_value = mock_vs
    mock_vs.get_gmail_retriever.return_value = "gmail_retriever"
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {"result": "email answer", "source_documents": []}
    mock_retrievalqa.from_chain_type.return_value = mock_chain
    result = search_tools.search_gmail("test email query")
    mock_vs.get_gmail_retriever.assert_called()
    assert result["result"] == "email answer"
