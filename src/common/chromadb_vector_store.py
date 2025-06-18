from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from common.vector_store import VectorStore


class ChromaDbVectorStore(VectorStore):
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        embedding_model: str | None = None,
    ):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model or "sentence-transformers/all-mpnet-base-v2"
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        self.db = None

    def from_documents(self, documents: list, **kwargs):
        """Create a new vector store from documents."""
        self.db = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            **kwargs,
        )
        return self

    def add_documents(self, documents: list, **kwargs):
        """Add documents to the existing vector store."""
        if self.db is None:
            self.from_documents(documents, **kwargs)
        else:
            self.db.add_documents(documents)

    def load(self):
        """Load an existing vector store from disk."""
        self.db = Chroma(
            persist_directory=self.persist_directory, embedding_function=self.embeddings
        )
        return self

    def as_retriever(self, **kwargs):
        if self.db is None:
            raise ValueError("Vector store is not loaded.")
        # Add a default filter to exclude deleted items
        filter_func = kwargs.pop("filter_func", None)

        def not_deleted_filter(doc):
            return not doc.metadata.get("deleted", False)

        if filter_func:

            def combined_filter(doc):
                return not_deleted_filter(doc) and filter_func(doc)

            kwargs["filter_func"] = combined_filter
        else:
            kwargs["filter_func"] = not_deleted_filter
        return self.db.as_retriever(**kwargs)

    def get_notes_retriever(self, **kwargs):
        """Return a retriever that only searches notes (source == 'obsidian')."""

        def notes_filter(doc):
            return doc.metadata.get("source") == "obsidian" and not doc.metadata.get(
                "deleted", False
            )

        return self.as_retriever(filter_func=notes_filter, **kwargs)

    def get_gmail_retriever(self, **kwargs):
        """Return a retriever that only searches Gmail (source == 'Gmail')."""

        def gmail_filter(doc):
            return doc.metadata.get("source") == "Gmail" and not doc.metadata.get("deleted", False)

        return self.as_retriever(filter_func=gmail_filter, **kwargs)

    def similarity_search_with_distance(
        self, query: str, k: int = 5, source: str = "", score_threshold: float = 0.2
    ) -> list[tuple[Document, float]]:
        """Return top-k (Document, distance) tuples for notes (obsidian only)."""
        # Use the underlying Chroma API for similarity search with scores
        # Filter for obsidian notes only
        filter = {"deleted": False}
        if source:
            filter = {"$and": [{"source": source}, {"deleted": False}]}
        if self.db is None:
            raise ValueError("Vector store is not loaded.")
        # Chroma's similarity_search_with_relevance_scores returns (doc, score) pairs
        results = self.db.similarity_search_with_relevance_scores(
            query, k=k, filter=filter, score_threshold=score_threshold
        )
        return results
