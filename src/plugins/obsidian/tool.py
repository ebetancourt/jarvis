import os

from langchain_core.tools import tool
from utils.strToKeywords import strToKeywords
from typing import List
from utils.vector_search_tools import (
    SearchResult,
    deduplicate_documents,
    load_db,
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"


@tool
def search_notes(query: str, k: int = 5) -> List[SearchResult]:
    """Search the user's notes for relevant information."""
    keywords = strToKeywords(query)
    keywords_str = " ".join(keywords)
    print(f'Searching for: "{keywords_str}"')

    vector_store = load_db(index_name="Obsidian", text_key="text")
    # First get results with distances
    results = vector_store.similarity_search_with_distance(
        keywords_str, k=k, source="obsidian"
    )
    # results = deduplicate_documents(results)
    vector_store.close()

    print("Raw results:", results)
    for doc, distance in results:
        print("Doc metadata:", doc.metadata)

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
