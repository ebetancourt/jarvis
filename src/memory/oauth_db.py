"""
OAuth Database Operations for SQLite

Handles persistent storage of OAuth tokens and calendar preferences
with proper database schema and migration support.
"""

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.settings import settings


class OAuthDatabase:
    """SQLite database manager for OAuth configurations and calendar preferences."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize OAuth database manager."""
        if db_path is None:
            # Use the same directory as the main SQLite database
            main_db_path = Path(settings.SQLITE_DB_PATH)
            self.db_path = str(main_db_path.parent / "oauth_settings.db")
        else:
            self.db_path = db_path

        self._ensure_database_exists()
        self._create_tables()

    def _ensure_database_exists(self):
        """Ensure the database file and directory exist."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            # OAuth tokens table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    token_type TEXT DEFAULT 'Bearer',
                    refresh_token TEXT,
                    expires_at REAL,
                    scope TEXT,
                    user_info_json TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(service, user_id)
                )
            """
            )

            # Calendar preferences table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendar_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    calendar_id TEXT NOT NULL,
                    calendar_summary TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    calendar_data_json TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(user_id, calendar_id)
                )
            """
            )

            # OAuth settings metadata table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """
            )

            # Create indexes for better performance
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_oauth_tokens_service_user
                ON oauth_tokens(service, user_id)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_calendar_prefs_user
                ON calendar_preferences(user_id)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_oauth_metadata_key
                ON oauth_metadata(key)
            """
            )

            conn.commit()

    def store_oauth_token(
        self,
        service: str,
        user_id: str,
        access_token: str,
        token_type: str = "Bearer",
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
        scope: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store or update an OAuth token."""
        try:
            current_time = time.time()
            user_info_json = json.dumps(user_info) if user_info else None

            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO oauth_tokens (
                        service, user_id, access_token, token_type, refresh_token,
                        expires_at, scope, user_info_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        service,
                        user_id,
                        access_token,
                        token_type,
                        refresh_token,
                        expires_at,
                        scope,
                        user_info_json,
                        current_time,
                        current_time,
                    ),
                )
                conn.commit()
                return True

        except sqlite3.Error as e:
            print(f"Error storing OAuth token: {e}")
            return False

    def get_oauth_token(self, service: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an OAuth token."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM oauth_tokens
                    WHERE service = ? AND user_id = ?
                """,
                    (service, user_id),
                )

                row = cursor.fetchone()
                if row:
                    token_data = dict(row)
                    # Parse JSON user info
                    if token_data["user_info_json"]:
                        token_data["user_info"] = json.loads(
                            token_data["user_info_json"]
                        )
                    else:
                        token_data["user_info"] = None
                    del token_data["user_info_json"]
                    return token_data

                return None

        except sqlite3.Error as e:
            print(f"Error retrieving OAuth token: {e}")
            return None

    def get_all_oauth_tokens(self, service: str) -> List[Dict[str, Any]]:
        """Get all OAuth tokens for a service."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM oauth_tokens WHERE service = ?
                """,
                    (service,),
                )

                tokens = []
                for row in cursor.fetchall():
                    token_data = dict(row)
                    # Parse JSON user info
                    if token_data["user_info_json"]:
                        token_data["user_info"] = json.loads(
                            token_data["user_info_json"]
                        )
                    else:
                        token_data["user_info"] = None
                    del token_data["user_info_json"]
                    tokens.append(token_data)

                return tokens

        except sqlite3.Error as e:
            print(f"Error retrieving OAuth tokens: {e}")
            return []

    def remove_oauth_token(self, service: str, user_id: str) -> bool:
        """Remove an OAuth token."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM oauth_tokens
                    WHERE service = ? AND user_id = ?
                """,
                    (service, user_id),
                )
                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Error removing OAuth token: {e}")
            return False

    def store_calendar_preferences(
        self, user_id: str, calendars: List[Dict[str, Any]]
    ) -> bool:
        """Store calendar preferences for a user."""
        try:
            current_time = time.time()

            with self._get_connection() as conn:
                # First, remove existing preferences for this user
                conn.execute(
                    """
                    DELETE FROM calendar_preferences WHERE user_id = ?
                """,
                    (user_id,),
                )

                # Insert new preferences
                for calendar in calendars:
                    calendar_data_json = json.dumps(calendar)
                    conn.execute(
                        """
                        INSERT INTO calendar_preferences (
                            user_id, calendar_id, calendar_summary, enabled,
                            calendar_data_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            user_id,
                            calendar.get("id", ""),
                            calendar.get("summary", ""),
                            calendar.get("enabled", True),
                            calendar_data_json,
                            current_time,
                            current_time,
                        ),
                    )

                conn.commit()
                return True

        except sqlite3.Error as e:
            print(f"Error storing calendar preferences: {e}")
            return False

    def get_calendar_preferences(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get calendar preferences for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT calendar_data_json FROM calendar_preferences
                    WHERE user_id = ?
                    ORDER BY calendar_summary
                """,
                    (user_id,),
                )

                calendars = []
                for row in cursor.fetchall():
                    calendar_data = json.loads(row["calendar_data_json"])
                    calendars.append(calendar_data)

                return calendars if calendars else None

        except sqlite3.Error as e:
            print(f"Error retrieving calendar preferences: {e}")
            return None

    def update_calendar_enabled_status(
        self, user_id: str, calendar_id: str, enabled: bool
    ) -> bool:
        """Update the enabled status of a specific calendar."""
        try:
            current_time = time.time()

            with self._get_connection() as conn:
                # Get current calendar data
                cursor = conn.execute(
                    """
                    SELECT calendar_data_json FROM calendar_preferences
                    WHERE user_id = ? AND calendar_id = ?
                """,
                    (user_id, calendar_id),
                )

                row = cursor.fetchone()
                if not row:
                    return False

                # Update calendar data
                calendar_data = json.loads(row["calendar_data_json"])
                calendar_data["enabled"] = enabled
                calendar_data_json = json.dumps(calendar_data)

                # Update database
                conn.execute(
                    """
                    UPDATE calendar_preferences
                    SET enabled = ?, calendar_data_json = ?, updated_at = ?
                    WHERE user_id = ? AND calendar_id = ?
                """,
                    (enabled, calendar_data_json, current_time, user_id, calendar_id),
                )

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Error updating calendar enabled status: {e}")
            return False

    def remove_calendar_preferences(self, user_id: str) -> bool:
        """Remove all calendar preferences for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM calendar_preferences WHERE user_id = ?
                """,
                    (user_id,),
                )
                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Error removing calendar preferences: {e}")
            return False

    def get_oauth_metadata(self, key: str) -> Optional[str]:
        """Get OAuth metadata value by key."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT value FROM oauth_metadata WHERE key = ?
                """,
                    (key,),
                )

                row = cursor.fetchone()
                return row["value"] if row else None

        except sqlite3.Error as e:
            print(f"Error retrieving OAuth metadata: {e}")
            return None

    def set_oauth_metadata(self, key: str, value: str) -> bool:
        """Set OAuth metadata value."""
        try:
            current_time = time.time()

            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO oauth_metadata (key, value, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (key, value, current_time, current_time),
                )
                conn.commit()
                return True

        except sqlite3.Error as e:
            print(f"Error setting OAuth metadata: {e}")
            return False

    def migrate_from_files(
        self,
        tokens_file: str = "oauth_tokens.json",
        prefs_file: str = "calendar_preferences.json",
    ) -> Tuple[int, int]:
        """
        Migrate OAuth data from JSON files to database.

        Returns:
            tuple: (tokens_migrated, preferences_migrated)
        """
        tokens_migrated = 0
        preferences_migrated = 0

        # Migrate tokens
        tokens_path = Path(tokens_file)
        if tokens_path.exists():
            try:
                with open(tokens_path, "r") as f:
                    tokens_data = json.load(f)

                for service, users in tokens_data.items():
                    for user_id, token_info in users.items():
                        success = self.store_oauth_token(
                            service=service,
                            user_id=user_id,
                            access_token=token_info.get("access_token", ""),
                            token_type=token_info.get("token_type", "Bearer"),
                            refresh_token=token_info.get("refresh_token"),
                            expires_at=token_info.get("expires_at"),
                            scope=token_info.get("scope"),
                            user_info=token_info.get("user_info"),
                        )
                        if success:
                            tokens_migrated += 1

            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                print(f"Error migrating tokens from file: {e}")

        # Migrate calendar preferences
        prefs_path = Path(prefs_file)
        if prefs_path.exists():
            try:
                with open(prefs_path, "r") as f:
                    prefs_data = json.load(f)

                for user_id, user_prefs in prefs_data.items():
                    calendars = user_prefs.get("calendars", [])
                    if calendars:
                        success = self.store_calendar_preferences(user_id, calendars)
                        if success:
                            preferences_migrated += len(calendars)

            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                print(f"Error migrating calendar preferences from file: {e}")

        return tokens_migrated, preferences_migrated

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for monitoring."""
        try:
            with self._get_connection() as conn:
                stats = {}

                # Token counts
                cursor = conn.execute(
                    """
                    SELECT service, COUNT(*) as count
                    FROM oauth_tokens
                    GROUP BY service
                """
                )
                stats["tokens_by_service"] = dict(cursor.fetchall())

                # Calendar preferences count
                cursor = conn.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as users,
                           COUNT(*) as total_calendars,
                           SUM(CASE WHEN enabled THEN 1 ELSE 0 END) as enabled_calendars
                    FROM calendar_preferences
                """
                )
                prefs_stats = cursor.fetchone()
                stats["calendar_preferences"] = dict(prefs_stats) if prefs_stats else {}

                # Database size
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                stats["database_size_bytes"] = page_count * page_size

                return stats

        except sqlite3.Error as e:
            print(f"Error getting database stats: {e}")
            return {}


# Global database instance
oauth_db = OAuthDatabase()
