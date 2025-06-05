import os


def load_settings():
    """Load settings from environment variables"""
    return {
        "github_token": os.environ.get("GITHUB_TOKEN"),
        "obsidian_notes_path": os.environ.get("OBSIDIAN_NOTES_PATH", "notes"),
        "chunk_size": int(os.environ.get("CHUNK_SIZE", 1000)),
        "chunk_overlap": int(os.environ.get("CHUNK_OVERLAP", 200)),
        "index_tracker_sqlite_db": os.environ.get(
            "INDEX_TRACKER_SQLITE_DB", "index_tracker.sqlite3"
        ),
        "obsidian_repo_url": os.environ.get(
            "OBSIDIAN_REPO_URL", "https://github.com/ebetancourt/obsidian.git"
        ),
        "vector_db_type": os.environ.get("VECTOR_DB_TYPE", "chromadb"),
    }
