import os

from langchain_core.tools import tool

from common.data import DATA_DIR
from common.load_settings import load_settings
from utils.strToKeywords import strToKeywords
from utils.vector_search_tools import (
    SearchResult,
    deduplicate_documents,
    load_db,
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

settings = load_settings()
OBSIDIAN_NOTES_PATH = settings["obsidian_notes_path"]


def get_full_note_text(item_relative_path):
    note_path = os.path.join(DATA_DIR, OBSIDIAN_NOTES_PATH, item_relative_path)
    try:
        with open(note_path) as f:
            return f.read()
    except Exception as e:
        return f"[Error reading note: {e}]"


@tool
def search_notes(query: str, k: int = 5) -> list[SearchResult]:
    """Search the user's notes for relevant information."""
    keywords = strToKeywords(query)
    keywords_str = " ".join(keywords)
    print(f'Searching for: "{keywords_str}"')

    vector_store = load_db()
    # First get results with distances
    results = vector_store.similarity_search_with_distance(
        keywords_str, k=k, source="obsidian", score_threshold=0.5
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
            "full_text": get_full_note_text(doc.metadata.get("item", "")),
        }
        for doc, distance in results
    ]
