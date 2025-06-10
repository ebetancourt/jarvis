import os
import glob
from langchain_community.document_loaders import TextLoader
from common.db_utils import (
    upsert_file_record,
    hash_file,
    get_file_record,
    init_db,
    mark_deleted,
    get_all_items,
)
from common.load_settings import load_settings
from common.data import refresh_data, DATA_DIR
from langchain.text_splitter import RecursiveCharacterTextSplitter
from common.get_vector_store import get_vector_store_from_config

settings = load_settings()
OBSIDIAN_NOTES_PATH = settings["obsidian_notes_path"]
OBSIDIAN_REPO_URL = settings["obsidian_repo_url"]


def index_obsidian(conn):
    notes_path = os.path.join(DATA_DIR, OBSIDIAN_NOTES_PATH)
    """Index Obsidian markdown notes and track in the DB."""
    documents = []
    pattern = os.path.join(notes_path, "**/*.md")
    total_files = len(list(glob.glob(pattern, recursive=True)))
    print(f"Found {total_files} markdown files")
    for i, file_path in enumerate(glob.glob(pattern, recursive=True), 1):
        rel_path = os.path.relpath(file_path, notes_path)
        file_hash = hash_file(file_path)
        rec = get_file_record(conn, rel_path)
        if rec and rec[0] == file_hash and rec[1] == 0:
            # Unchanged and not deleted
            continue
        try:
            loader = TextLoader(file_path, encoding="utf-8")
            loaded_docs = loader.load()
            for doc in loaded_docs:
                doc.metadata["source"] = "obsidian"
                doc.metadata["item"] = rel_path
                doc.metadata["deleted"] = False
            documents.extend(loaded_docs)
            upsert_file_record(conn, "obsidian", rel_path, file_hash)
            print(f"[{i}/{total_files}] Indexed: {rel_path}")
        except Exception as e:
            print(f"Error loading {file_path}: {str(e)}")
            continue
    return documents


def run_index():
    notes_path = os.path.join(DATA_DIR, OBSIDIAN_NOTES_PATH)
    refresh_data(OBSIDIAN_REPO_URL, notes_path)
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
    documents = index_obsidian(conn)
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
    vector_store = get_vector_store_from_config()
    # Add documents in batches with progress reporting
    batch_size = 100
    total = len(chunks)
    print("Adding documents to vector store in batches...")
    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        vector_store.add_documents(batch)
        print(f"Added {min(i+batch_size, total)}/{total} chunks")
    print("Database updated successfully!")


def get_full_note_text(item_relative_path):
    note_path = os.path.join(DATA_DIR, OBSIDIAN_NOTES_PATH, item_relative_path)
    try:
        with open(note_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"[Error reading note: {e}]"
