import os
import sqlite3
from datetime import datetime

import xxhash

from common.data import DATA_DIR
from common.load_settings import load_settings

settings = load_settings()
SQLITE_DB = settings["index_tracker_sqlite_db"]


def init_db():
    conn = sqlite3.connect(os.path.join(DATA_DIR, SQLITE_DB))
    c = conn.cursor()
    # Add new fields for email tracking if not present
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS file_index (
            source TEXT,
            item TEXT PRIMARY KEY,
            hash TEXT,
            created_at TEXT,
            updated_at TEXT,
            deleted INTEGER DEFAULT 0,
            account TEXT,
            item_date TEXT
        )
        """
    )
    # Try to add columns if they don't exist (for upgrades)
    try:
        c.execute("ALTER TABLE file_index ADD COLUMN account TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE file_index ADD COLUMN item_date TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn


def get_file_record(conn, item):
    c = conn.cursor()
    c.execute("SELECT hash, deleted FROM file_index WHERE item = ?", (item,))
    return c.fetchone()


def upsert_file_record(conn, source, item, hash_value, account=None, item_date=None):
    now = datetime.now().isoformat()
    c = conn.cursor()
    # If account/item_date are provided, use them; otherwise, fallback to old logic
    if account is not None or item_date is not None:
        c.execute(
            """
            INSERT INTO file_index (source, item, hash, created_at, updated_at, deleted, account, item_date)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(item) DO UPDATE SET hash=excluded.hash, \
            updated_at=excluded.updated_at, deleted=0, account=excluded.account, item_date=excluded.item_date
            """,
            (source, item, hash_value, now, now, account, item_date),
        )
    else:
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


def hash_file(path):
    h = xxhash.xxh64()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
