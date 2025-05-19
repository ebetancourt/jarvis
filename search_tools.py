import os

from pydantic import BaseModel
from common.vector_store import VectorStore
from langchain_core.tools import tool
from typing import Any, Dict, List, Tuple
from langchain_core.documents import Document
from utils.strToKeywords import strToKeywords

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class SearchResult(BaseModel):
    item: str
    bucket: str
    source: str
    document: Document
    distance: float
    metadata: Dict[str, Any]


def get_source_key(doc_result: Tuple[Document, float]):
    # Returns a stable key for deduplication
    doc, distance = doc_result
    source = doc.metadata.get("source", "unknown")

    match source:
        case "obsidian":
            return doc.metadata.get("item", "unknown")
        case "Gmail":
            return doc.metadata.get("subject", "unknown")
        case _:
            return str(doc)


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
def search_notes(query: str, k: int = 5):
    """Search the user's notes for relevant information."""
    keywords = strToKeywords(query)
    keywords_str = " ".join(keywords)
    print(f'Searching for: "{keywords_str}"')

    vector_store = load_db()
    # First get results with distances
    results = vector_store.similarity_search_with_distance(
        keywords_str, k=k, source="obsidian"
    )
    results = deduplicate_documents(results)

    # Return a list of dicts for easier formatting
    return [
        {
            "item": doc.metadata.get("item", ""),
            "bucket": doc.metadata.get("bucket", ""),
            "source": doc.metadata.get("source", ""),
            "document": doc,
            "distance": distance,
            "metadata": getattr(doc, "metadata", {}),
        }
        for doc, distance in results
    ]


@tool
def search_gmail(query: str, k: int = 5) -> List[SearchResult]:
    """Search the user's Gmail for relevant information."""
    keywords = strToKeywords(query)
    keywords_str = " ".join(keywords)
    print(f'Searching for: "{keywords_str}"')
    vector_store = load_db()
    # First get results with distances
    results = vector_store.similarity_search_with_distance(
        keywords_str, k=k, source="Gmail"
    )
    results = deduplicate_documents(results)

    # Return a list of dicts for easier formatting
    return [
        {
            "item": doc.metadata.get("subject", ""),
            "bucket": doc.metadata.get("bucket", ""),
            "source": doc.metadata.get("source", ""),
            "document": doc,
            "distance": distance,
            "metadata": getattr(doc, "metadata", {}),
        }
        for doc, distance in results
    ]
