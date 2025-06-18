from langchain_core.documents import Document
from pydantic import BaseModel

from common.get_vector_store import get_vector_store_from_config


class SearchResult(BaseModel):
    item: str
    bucket: str
    source: str
    document: Document
    distance: float
    metadata: dict
    full_text: str


def get_source_key(doc_result):
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
    vector_store = get_vector_store_from_config()
    vector_store.load()
    return vector_store
