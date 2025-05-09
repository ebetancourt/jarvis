#!/usr/bin/env python3
import os
import yaml
from typing import List
import glob
import xxhash
import sqlite3
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from vector_store import VectorStore
from langchain.schema import Document
from gmail_auth import GmailAuth

# Set TOKENIZERS_PARALLELISM to false to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

SQLITE_DB = "index_tracker.sqlite3"


# --- SQLite Helper ---
def init_db():
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS file_index (
            source TEXT,
            item TEXT PRIMARY KEY,
            hash TEXT,
            created_at TEXT,
            updated_at TEXT,
            deleted INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    return conn


def get_file_record(conn, item):
    c = conn.cursor()
    c.execute("SELECT hash, deleted FROM file_index WHERE item = ?", (item,))
    return c.fetchone()


def upsert_file_record(conn, source, item, hash_value):
    now = datetime.now().isoformat()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO file_index (source, item, hash, created_at, updated_at, deleted)
        VALUES (?, ?, ?, ?, ?, 0)
        ON CONFLICT(item) DO UPDATE SET hash=excluded.hash, \
        updated_at=excluded.updated_at, deleted=0
        """,
        (source, item, hash_value, now, now),
    )
    conn.commit()


def mark_deleted(conn, item):
    c = conn.cursor()
    c.execute("UPDATE file_index SET deleted=1 WHERE item=?", (item,))
    conn.commit()


def get_all_items(conn):
    c = conn.cursor()
    c.execute("SELECT item FROM file_index WHERE deleted=0")
    return set(row[0] for row in c.fetchall())


# --- Main logic ---
def load_settings():
    """Load settings from settings.yml."""
    with open("settings.yml", "r") as file:
        return yaml.safe_load(file)


def hash_file(path):
    h = xxhash.xxh64()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_documents(notes_path: str, conn) -> List[Document]:
    """Load and hash markdown documents, only return new/changed files."""
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


def load_gmail_documents(source_id: str, conn) -> List[Document]:
    """Fetch and prepare Gmail messages from the last week for indexing."""
    gmail_auth = GmailAuth()
    email_address = gmail_auth.get_user_email(source_id)
    messages = gmail_auth.fetch_recent_messages(source_id, days=7)
    documents = []
    for msg in messages:
        # Extract subject and snippet for content
        headers = {
            h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])
        }
        subject = headers.get("Subject", "")
        snippet = msg.get("snippet", "")
        body = subject + "\n" + snippet
        doc = Document(
            page_content=body,
            metadata={
                "source": "Gmail",
                "bucket": email_address,
                "item": msg["id"],
                "deleted": False,
                "subject": subject,
                "snippet": snippet,
                "internalDate": msg.get("internalDate"),
            },
        )
        documents.append(doc)
    return documents


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
    # Load and index new/changed files
    documents = load_documents(notes_path, conn)
    # --- Gmail indexing ---
    gmail_auth = GmailAuth()
    gmail_accounts = gmail_auth.list_gmail_accounts()
    for email_address in gmail_accounts:
        print(f"Fetching Gmail messages for {email_address}...")
        gmail_docs = load_gmail_documents(email_address, conn)
        print(f"Loaded {len(gmail_docs)} Gmail messages for {email_address}")
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
    vector_store = VectorStore(
        persist_directory="./chroma_db",
        embedding_model=settings.get(
            "embedding_model", "sentence-transformers/all-mpnet-base-v2"
        ),
    )
    vector_store.add_documents(chunks)
    print("Database updated successfully!")


if __name__ == "__main__":
    main()
