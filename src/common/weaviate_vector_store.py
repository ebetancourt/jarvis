from typing import List, Optional, Tuple
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_weaviate import WeaviateVectorStore as LangchainWeaviate
from common.vector_store import VectorStore
import weaviate
import logging

logger = logging.getLogger(__name__)


class WeaviateVectorStore(VectorStore):
    def __init__(
        self,
        host: str,
        port: Optional[int] = 8080,
        grpc_host: Optional[str] = None,
        grpc_port: Optional[int] = 50051,
        secure: Optional[bool] = False,
        grpc_secure: Optional[bool] = False,
        auth_client_secret: Optional[str] = None,
        embedding_model: Optional[str] = None,
        index_name: str = "Document",
        text_key: str = "text",
        **kwargs,
    ):
        self.host = host
        self.port = port
        self.grpc_host = grpc_host or host
        self.grpc_port = grpc_port
        self.secure = secure
        self.grpc_secure = grpc_secure
        self.auth_client_secret = auth_client_secret
        self.embedding_model = (
            embedding_model or "sentence-transformers/all-mpnet-base-v2"
        )
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        self.index_name = index_name
        self.text_key = text_key
        print(f"Index name: {self.index_name}")
        print(f"Text key: {self.text_key}")
        if self.index_name == "Document":
            logger.warning(
                "Using default index_name 'Document'. "
                "It is recommended to specify a custom class name "
                "for better data separation."
            )
        logger.info(
            "Connecting to Weaviate with params: "
            "host=%s, port=%s, grpc_host=%s, grpc_port=%s, "
            "secure=%s, grpc_secure=%s, "
            "auth_client_secret_set=%s, kwargs=%s",
            self.host,
            self.port,
            self.grpc_host,
            self.grpc_port,
            self.secure,
            self.grpc_secure,
            bool(self.auth_client_secret),
            kwargs,
        )
        try:
            self.client = weaviate.connect_to_custom(
                http_host=self.host,
                http_port=self.port,
                http_secure=self.secure,
                grpc_host=self.grpc_host,
                grpc_port=self.grpc_port,
                grpc_secure=self.grpc_secure,
                **kwargs,
            )
        except Exception as e:
            logger.error(
                "Failed to connect to Weaviate: %s\nParams: "
                "host=%s, port=%s, grpc_host=%s, grpc_port=%s, "
                "secure=%s, grpc_secure=%s, "
                "auth_client_secret_set=%s, kwargs=%s",
                e,
                self.host,
                self.port,
                self.grpc_host,
                self.grpc_port,
                self.secure,
                self.grpc_secure,
                bool(self.auth_client_secret),
                kwargs,
            )
            raise
        self.db = None

    def from_documents(self, documents: List, **kwargs):
        """Create a new vector store from documents."""
        self.db = LangchainWeaviate.from_documents(
            documents,
            self.embeddings,
            client=self.client,
            index_name=self.index_name,
            text_key=self.text_key,
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
        """Load an existing vector store from Weaviate."""
        self.db = LangchainWeaviate(
            client=self.client,
            embedding=self.embeddings,
            index_name=self.index_name,
            text_key=self.text_key,
        )
        return self

    def as_retriever(self, **kwargs):
        if self.db is None:
            raise ValueError("Vector store is not loaded.")
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
            return doc.metadata.get("source") == "Gmail" and not doc.metadata.get(
                "deleted", False
            )

        return self.as_retriever(filter_func=gmail_filter, **kwargs)

    def similarity_search_with_distance(
        self, query: str, k: int = 5, source: str = "", score_threshold: float = 0.2
    ) -> List[Tuple[Document, float]]:
        """Return top-k (Document, distance) tuples for notes (obsidian only)."""
        if self.db is None:
            raise ValueError("Vector store is not loaded.")
        results = self.db.similarity_search_with_relevance_scores(
            query,
            k=k,  # score_threshold=score_threshold
        )
        filtered = []
        for doc, score in results:
            if doc.metadata.get("deleted", False):
                continue
            if source and doc.metadata.get("source") != source:
                continue
            filtered.append((doc, score))
        return filtered

    def close(self):
        self.client.close()
