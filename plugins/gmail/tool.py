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
def search_gmail(query: str, k: int = 5) -> List[SearchResult]:
    """
    Search the user's Gmail for relevant information. Great for looking up personal
    information about subscriptions, services, events, contacts, recent conversations,
    purchases, etc.
    Args:
        query: The query to search for.
        k: The maximum number of results to return.
    Returns:
        A list of SearchResult objects.
    """
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
