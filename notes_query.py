#!/usr/bin/env python3
import argparse
import os
import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
import json
from datetime import datetime
from common.vector_store import VectorStore
from search_tools import search_notes_with_distance

# Prompt template for both chain and logging
prompt_template = """You are a helpful assistant that answers questions based on the
provided context from the user's notes. Use the context to provide accurate and
relevant answers. If the context doesn't contain enough information to answer the
question, say so.

Context: {context}

Question: {question}

Answer:"""

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


def create_chain():
    """Create a chain that combines retrieval and generation."""
    vector_store = load_db()
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    llm = ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7, max_tokens=1000)

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


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


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Query your Obsidian notes using natural language."
    )
    parser.add_argument(
        "question", type=str, help="The question to ask about your notes"
    )
    args = parser.parse_args()

    # Check for OpenAI API key
    api_key = get_api_key()
    if not api_key:
        print("Error: OpenAI API key not found. Please set it in one of these ways:")
        print("1. Environment variable: export OPENAI_API_KEY='your-key'")
        print("2. .env file: Create a .env file with OPENAI_API_KEY=your-key")
        print("3. settings.yml: Add openai_api_key: your-key to settings.yml")
        return

    try:
        # Get the answer and distances
        results = search_notes_with_distance(args.question, k=5)
        if not results:
            print("No relevant notes found.")
            return
        # Print the answer (use the top result's content as a preview)
        print("\nTop Note Preview:")
        print(results[0]["document"].page_content[:500])
        # Print sources with distances
        print("\nSources (with vector distance):")
        for r in results:
            meta = r["metadata"]
            rel_path = meta.get("item") or meta.get("file_path") or "Unknown file"
            print(f"- Obsidian: {rel_path} (distance: {r['distance']:.3f})")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print("\nDetailed error:")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
