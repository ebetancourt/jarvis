# import os
# import sqlite3
# from datetime import datetime
# from typing import Optional

# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from googleapiclient.discovery import build

# # If modifying these scopes, delete the token file.
# SCOPES = [
#     "https://www.googleapis.com/auth/gmail.readonly",
# ]


# class GmailAuth:
#     def __init__(self, db_path: str = "index_tracker.sqlite3"):
#         self.db_path = db_path
#         self._init_db()

#     def _init_db(self):
#         """Initialize the SQLite database with the tokens table if it doesn't exist."""
#         with sqlite3.connect(self.db_path) as conn:
#             conn.execute(
#                 """
#                 CREATE TABLE IF NOT EXISTS gmail_tokens (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     email_address TEXT UNIQUE NOT NULL,
#                     access_token TEXT NOT NULL,
#                     refresh_token TEXT NOT NULL,
#                     token_expiry TIMESTAMP NOT NULL,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     last_indexed_internaldate INTEGER DEFAULT 0
#                 )
#             """
#             )

#     def get_credentials(self, email_address: str) -> Optional[Credentials]:
#         with sqlite3.connect(self.db_path) as conn:
#             cursor = conn.execute(
#                 "SELECT access_token, refresh_token, token_expiry FROM gmail_tokens "
#                 "WHERE email_address = ?",
#                 (email_address,),
#             )
#             row = cursor.fetchone()

#         if not row:
#             return None

#         access_token, refresh_token, token_expiry = row
#         token_expiry = datetime.fromisoformat(token_expiry)

#         credentials = Credentials(
#             token=access_token,
#             refresh_token=refresh_token,
#             token_uri="https://oauth2.googleapis.com/token",
#             client_id=os.getenv("GOOGLE_CLIENT_ID"),
#             client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
#             scopes=SCOPES,
#         )

#         if credentials.expired:
#             credentials.refresh(Request())
#             self._save_credentials(email_address, credentials)

#         return credentials

#     def _save_credentials(self, email_address: str, credentials: Credentials):
#         refresh_token = credentials.refresh_token
#         if not refresh_token:
#             with sqlite3.connect(self.db_path) as conn:
#                 cursor = conn.execute(
#                     "SELECT refresh_token FROM gmail_tokens WHERE email_address = ?",
#                     (email_address,),
#                 )
#                 row = cursor.fetchone()
#                 if row:
#                     refresh_token = row[0]
#         # Fetch the authenticated email address
#         service = build("gmail", "v1", credentials=credentials)
#         profile = service.users().getProfile(userId="me").execute()
#         actual_email = profile["emailAddress"]
#         with sqlite3.connect(self.db_path) as conn:
#             conn.execute(
#                 """
#                 INSERT OR REPLACE INTO gmail_tokens
#                 (email_address, access_token, refresh_token, token_expiry, updated_at)
#                 VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
#             """,
#                 (
#                     actual_email,
#                     credentials.token,
#                     refresh_token,
#                     credentials.expiry.isoformat(),
#                 ),
#             )

#     def authenticate(self, email_address: str = "") -> Credentials:
#         credentials = self.get_credentials(email_address)

#         if credentials and not credentials.expired:
#             return credentials

#         flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
#         credentials = flow.run_local_server(
#             port=0, access_type="offline", prompt="consent"
#         )
#         self._save_credentials(email_address, credentials)
#         return credentials

#     def get_gmail_service(self, email_address: str = ""):
#         credentials = self.authenticate(email_address)
#         return build("gmail", "v1", credentials=credentials)

#     def get_user_email(self, email_address: str = "") -> str:
#         service = self.get_gmail_service(email_address)
#         profile = service.users().getProfile(userId="me").execute()
#         return profile["emailAddress"]

#     def get_last_indexed_internaldate(self, email_address: str) -> int:
#         with sqlite3.connect(self.db_path) as conn:
#             cursor = conn.execute(
#                 "SELECT last_indexed_internaldate FROM gmail_tokens WHERE email_address = ?",  # noqa: E501
#                 (email_address,),
#             )
#             row = cursor.fetchone()
#             return row[0] if row and row[0] else 0

#     def update_last_indexed_internaldate(self, email_address: str, internaldate: int):
#         with sqlite3.connect(self.db_path) as conn:
#             conn.execute(
#                 "UPDATE gmail_tokens SET last_indexed_internaldate = ? WHERE email_address = ?",  # noqa: E501
#                 (internaldate, email_address),
#             )

#     def fetch_recent_messages(
#         self, email_address: str, days: int = 7, max_results: int = 50
#     ):
#         last_internaldate = self.get_last_indexed_internaldate(email_address)
#         service = self.get_gmail_service(email_address)
#         query = f"newer_than:{days}d"
#         if last_internaldate > 0:
#             # Gmail API expects seconds, internalDate is ms
#             after_seconds = last_internaldate // 1000
#             query += f" after:{after_seconds}"
#         results = (
#             service.users()
#             .messages()
#             .list(
#                 userId="me",
#                 q=query,
#                 maxResults=max_results,
#             )
#             .execute()
#         )
#         messages = results.get("messages", [])
#         full_messages = []
#         for msg in messages:
#             msg_detail = (
#                 service.users()
#                 .messages()
#                 .get(
#                     userId="me",
#                     id=msg["id"],
#                 )
#                 .execute()
#             )
#             full_messages.append(msg_detail)
#         return full_messages

#     def list_gmail_accounts(self):
#         """Return a list of all Gmail email addresses in the tokens table."""
#         with sqlite3.connect(self.db_path) as conn:
#             cursor = conn.execute(
#                 "SELECT email_address FROM gmail_tokens WHERE email_address IS NOT NULL"
#             )
#             return [row[0] for row in cursor.fetchall()]
