#!/usr/bin/env python3
from dotenv import load_dotenv
import os
import yaml
import glob
from langchain.text_splitter import RecursiveCharacterTextSplitter
from common.get_vector_store import get_vector_store
from plugins.obsidian.indexer import index_obsidian
from plugins.gmail.indexer import index_gmail
from common.db_utils import (
    init_db,
    mark_deleted,
    get_all_items,
)

load_dotenv()

# Set TOKENIZERS_PARALLELISM to false to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_settings():
    """Load settings from settings.yml."""
    with open("settings.yml", "r") as file:
        return yaml.safe_load(file)


def main():
    # Load settings
    settings = load_settings()
    notes_path = settings["obsidian_notes_path"]
    if not os.path.exists(notes_path):
        print(f"Error: Notes directory not found at {notes_path}")
        return
    print(f"Loading documents from {notes_path}...")
    conn = init_db()
    # Track all current files
    current_files = set()
    pattern = os.path.join(notes_path, "**/*.md")
    for file_path in glob.glob(pattern, recursive=True):
        rel_path = os.path.relpath(file_path, notes_path)
        current_files.add(rel_path)
    # Mark deleted files
    indexed_files = get_all_items(conn)
    for item in indexed_files - current_files:
        mark_deleted(conn, item)
        print(f"Marked deleted: {item}")
    # Load and index new/changed files (Obsidian)
    documents = index_obsidian(notes_path, conn)
    # --- Gmail indexing ---
    gmail_docs = index_gmail(conn)
    print(f"Loaded {len(gmail_docs)} Gmail messages across all accounts")
    documents.extend(gmail_docs)
    print(f"Loaded {len(documents)} new or changed documents")
    if not documents:
        print("No new or changed documents to index.")
        return
    # Split documents into chunks
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.get("chunk_size", 1000),
        chunk_overlap=settings.get("chunk_overlap", 200),
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")
    # Initialize vector store
    print("Initializing vector store...")
    vector_store = get_vector_store(
        db_type="chromadb",
        config={
            "persist_directory": "./chroma_db",
            "embedding_model": settings.get(
                "embedding_model", "sentence-transformers/all-mpnet-base-v2"
            ),
        },
    )
    vector_store.add_documents(chunks)
    print("Database updated successfully!")


if __name__ == "__main__":
    main()
