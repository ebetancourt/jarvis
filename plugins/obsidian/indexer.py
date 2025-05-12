import os
import glob
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from common.db_utils import upsert_file_record, hash_file, get_file_record

def index_obsidian(notes_path, conn):
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
