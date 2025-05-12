import os
import sqlite3
import tempfile
import shutil
import pytest
from langchain.schema import Document

@pytest.fixture
def temp_notes_dir():
    temp_dir = tempfile.mkdtemp()
    note_path = os.path.join(temp_dir, "test.md")
    with open(note_path, "w") as f:
        f.write("# Test Note\nThis is a test.")
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_load_documents_indexes_note(temp_notes_dir):
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tf:
        os.environ["JARVIS_SQLITE_DB"] = tf.name
        import index_notes  # Import after setting env var
        conn = index_notes.init_db()
        docs = index_notes.load_documents(temp_notes_dir, conn)
        assert len(docs) > 0
        c = conn.cursor()
        c.execute("SELECT * FROM file_index WHERE source='obsidian'")
        rows = c.fetchall()
        assert len(rows) == 1
        assert rows[0][1].endswith("test.md")
        conn.close()
    del os.environ["JARVIS_SQLITE_DB"]

def test_load_gmail_documents_indexes_email(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tf:
        os.environ["JARVIS_SQLITE_DB"] = tf.name
        import index_notes  # Import after setting env var
        # Mock GmailAuth and fetch_recent_messages
        class DummyGmailAuth:
            def get_user_email(self, source_id):
                return "test@example.com"
            def fetch_recent_messages(self, source_id, days=365, max_results=1000):
                return [{
                    "id": "email1",
                    "payload": {"headers": [{"name": "Subject", "value": "Test Email"}]},
                    "snippet": "This is a test email.",
                    "internalDate": "2024-01-01T00:00:00Z"
                }]
        monkeypatch.setattr("index_notes.GmailAuth", DummyGmailAuth)
        conn = index_notes.init_db()
        docs = index_notes.load_gmail_documents("dummy_id", conn)
        assert len(docs) == 1
        c = conn.cursor()
        c.execute("SELECT * FROM file_index WHERE source='gmail'")
        rows = c.fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "Test Email"
        assert rows[0][6] == "test@example.com"
        assert rows[0][7] == "2024-01-01T00:00:00Z"
        conn.close()
    del os.environ["JARVIS_SQLITE_DB"]
