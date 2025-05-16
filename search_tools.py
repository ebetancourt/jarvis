import os

from pydantic import BaseModel
from common.vector_store import VectorStore
from langchain_core.tools import tool
from typing import Any, Dict, List
from langchain_core.documents import Document

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class SearchResult(BaseModel):
    document: Document
    distance: float
    metadata: Dict[str, Any]


def get_source_key(doc):
    # Returns a stable key for deduplication
    try:
        if hasattr(doc, "metadata"):
            meta = doc.metadata
            if meta.get("source") == "obsidian":
                return (
                    "obsidian",
                    meta.get("item") or meta.get("file_path") or str(doc),
                )
            elif meta.get("source") == "Gmail":
                return ("gmail", meta.get("subject") or meta.get("item") or str(doc))
        if isinstance(doc, dict):
            if doc.get("source") == "obsidian":
                return ("obsidian", doc.get("item") or doc.get("file_path") or str(doc))
            elif doc.get("source") == "Gmail":
                return ("gmail", doc.get("subject") or doc.get("item") or str(doc))
        if isinstance(doc, str):
            return ("str", doc)
    except Exception:
        pass
    return ("other", str(doc))


def deduplicate_documents(documents):
    seen = set()
    unique_docs = []
    for doc in documents:
        key = get_source_key(doc)
        if key not in seen:
            seen.add(key)
            unique_docs.append(doc)
    return unique_docs


def load_db():
    from notes_query import load_settings

    settings = load_settings()
    vector_store = VectorStore(
        persist_directory="./chroma_db",
        embedding_model=settings.get(
            "embedding_model", "sentence-transformers/all-mpnet-base-v2"
        ),
    )
    vector_store.load()
    return vector_store


@tool
def search_notes(query: str, k: int = 5) -> List[SearchResult]:
    """Search the user's notes for relevant information."""
    vector_store = load_db()
    # First get results with distances
    results = vector_store.similarity_search_with_distance(
        query, k=k, source="obsidian"
    )
    results = deduplicate_documents(results)

    # Return a list of dicts for easier formatting
    return [
        {
            "document": doc,
            "distance": distance,
            "metadata": getattr(doc, "metadata", {}),
        }
        for doc, distance in results
    ]


@tool
def search_gmail(query: str, k: int = 5) -> List[SearchResult]:
    """Search the user's Gmail for relevant information."""
    vector_store = load_db()
    # First get results with distances
    results = vector_store.similarity_search_with_distance(query, k=k, source="Gmail")
    results = deduplicate_documents(results)

    # Return a list of dicts for easier formatting
    return [
        {
            "document": doc,
            "distance": distance,
            "metadata": getattr(doc, "metadata", {}),
        }
        for doc, distance in results
    ]
