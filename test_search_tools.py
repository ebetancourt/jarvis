import unittest
from unittest.mock import patch, MagicMock
from vector_store import VectorStore
import search_tools
from langchain.schema import Document


class TestVectorStoreFiltering(unittest.TestCase):
    def setUp(self):
        self.vector_store = VectorStore()
        # Patch the db to a mock
        self.vector_store.db = MagicMock()
        # Create mock documents
        self.docs = [
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

    def test_get_notes_retriever_filters_obsidian(self):
        # Mock as_retriever to just return the filtered docs
        self.vector_store.db.as_retriever = lambda **kwargs: [
            d for d in self.docs if kwargs["filter_func"](d)
        ]
        retriever = self.vector_store.get_notes_retriever()
        self.assertTrue(
            all(
                d.metadata["source"] == "obsidian" and not d.metadata["deleted"]
                for d in retriever
            )
        )
        self.assertEqual(len(retriever), 2)

    def test_get_gmail_retriever_filters_gmail(self):
        self.vector_store.db.as_retriever = lambda **kwargs: [
            d for d in self.docs if kwargs["filter_func"](d)
        ]
        retriever = self.vector_store.get_gmail_retriever()
        self.assertTrue(
            all(
                d.metadata["source"] == "Gmail" and not d.metadata["deleted"]
                for d in retriever
            )
        )
        self.assertEqual(len(retriever), 1)


class TestSearchTools(unittest.TestCase):
    @patch("search_tools.ChatOpenAI")
    @patch("search_tools.load_db")
    @patch("search_tools.RetrievalQA")
    def test_search_notes_calls_notes_retriever(
        self, mock_retrievalqa, mock_load_db, mock_chatopenai
    ):
        mock_vs = MagicMock()
        mock_load_db.return_value = mock_vs
        mock_vs.get_notes_retriever.return_value = "notes_retriever"
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = {"result": "answer", "source_documents": []}
        mock_retrievalqa.from_chain_type.return_value = mock_chain
        result = search_tools.search_notes("test query")
        mock_vs.get_notes_retriever.assert_called()
        self.assertEqual(result["result"], "answer")

    @patch("search_tools.ChatOpenAI")
    @patch("search_tools.load_db")
    @patch("search_tools.RetrievalQA")
    def test_search_gmail_calls_gmail_retriever(
        self, mock_retrievalqa, mock_load_db, mock_chatopenai
    ):
        mock_vs = MagicMock()
        mock_load_db.return_value = mock_vs
        mock_vs.get_gmail_retriever.return_value = "gmail_retriever"
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = {
            "result": "email answer",
            "source_documents": [],
        }
        mock_retrievalqa.from_chain_type.return_value = mock_chain
        result = search_tools.search_gmail("test email query")
        mock_vs.get_gmail_retriever.assert_called()
        self.assertEqual(result["result"], "email answer")


if __name__ == "__main__":
    unittest.main()
