import os
import sqlite3
from datetime import datetime
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these scopes, delete the token file.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.metadata",
]


class GmailAuth:
    def __init__(self, db_path: str = "index_tracker.sqlite3"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database with the tokens table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gmail_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT UNIQUE NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    token_expiry TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    def get_credentials(self, source_id: str) -> Optional[Credentials]:
        """Get credentials for a specific Gmail account."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT access_token, refresh_token, token_expiry FROM gmail_tokens "
                "WHERE source_id = ?",
                (source_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        access_token, refresh_token, token_expiry = row
        token_expiry = datetime.fromisoformat(token_expiry)

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=SCOPES,
        )

        if credentials.expired:
            credentials.refresh(Request())
            self._save_credentials(source_id, credentials)

        return credentials

    def _save_credentials(self, source_id: str, credentials: Credentials):
        """Save or update credentials in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO gmail_tokens
                (source_id, access_token, refresh_token, token_expiry, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    source_id,
                    credentials.token,
                    credentials.refresh_token,
                    credentials.expiry.isoformat(),
                ),
            )

    def authenticate(self, source_id: str) -> Credentials:
        """Authenticate a Gmail account and return credentials."""
        credentials = self.get_credentials(source_id)

        if credentials and not credentials.expired:
            return credentials

        # If no valid credentials exist, start the OAuth2 flow
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)

        credentials = flow.run_local_server(port=0)
        self._save_credentials(source_id, credentials)
        return credentials

    def get_gmail_service(self, source_id: str):
        """Get an authenticated Gmail service instance."""
        credentials = self.authenticate(source_id)
        return build("gmail", "v1", credentials=credentials)
