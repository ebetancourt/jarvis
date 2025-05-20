#!/usr/bin/env python3
import os
import yaml
from dotenv import load_dotenv
from common.vector_store import VectorStore

# Set TOKENIZERS_PARALLELISM to false to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_settings():
    """Load settings from settings.yml."""
    with open("settings.yml", "r") as file:
        return yaml.safe_load(file)


def load_db():
    """Load the vector store with embeddings."""
    settings = load_settings()
    vector_store = VectorStore(
        persist_directory="./chroma_db",
        embedding_model=settings.get(
            "embedding_model", "sentence-transformers/all-mpnet-base-v2"
        ),
    )
    vector_store.load()
    return vector_store


def get_api_key():
    """Get OpenAI API key from environment variable, .env file, or settings.yml."""
    # First try environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # Then try .env file
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # Finally try settings.yml
    settings = load_settings()
    api_key = settings.get("openai_api_key")
    if api_key:
        return api_key

    return None


def format_source(source):
    """Format the source path to be more readable."""
    if isinstance(source, str):
        return source
    elif isinstance(source, dict):
        return source.get("source", "Unknown source")
    return "Unknown source"
