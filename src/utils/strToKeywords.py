import nltk
from rake_nltk import Rake

nltk.download("stopwords", quiet=True)

# Optionally, you can specify your own stopwords file or use the built-in one
# rake = Rake('path/to/stopwords.txt')
rake = Rake()


def strToKeywords(text: str) -> list[str]:
    """
    Extract keywords from a string using the RAKE algorithm.
    Args:
        text (str): The input string.
    Returns:
        List[str]: A list of extracted keywords, sorted by relevance.
    """
    rake.extract_keywords_from_text(text)
    # rake.get_ranked_phrases() returns a list of keywords sorted by score
    return rake.get_ranked_phrases()
