from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from typing import List, Optional


class VectorStore:
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        embedding_model: Optional[str] = None,
    ):
        self.persist_directory = persist_directory
        self.embedding_model = (
            embedding_model or "sentence-transformers/all-mpnet-base-v2"
        )
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        self.db = None

    def from_documents(self, documents: List, **kwargs):
        """Create a new vector store from documents."""
        self.db = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            **kwargs,
        )
        return self

    def add_documents(self, documents: List, **kwargs):
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
