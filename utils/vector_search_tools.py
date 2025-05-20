from typing import Any, Dict, Tuple
from pydantic import BaseModel
from langchain_core.documents import Document
from common.vector_store import VectorStore
from utils.load_settings import load_settings


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
    settings = load_settings()
    vector_store = VectorStore(
        persist_directory="./chroma_db",
        embedding_model=settings.get(
            "embedding_model", "sentence-transformers/all-mpnet-base-v2"
        ),
    )
    vector_store.load()
    return vector_store
