from langchain.schema import Document
from common.google_auth import GmailAuth
from common.db_utils import upsert_file_record

def index_gmail(conn, gmail_auth=None, max_results=1000):
    """Index Gmail messages for all accounts and track in the DB."""
    if gmail_auth is None:
        gmail_auth = GmailAuth()
    documents = []
    gmail_accounts = gmail_auth.list_gmail_accounts()
    for email_address in gmail_accounts:
        print(f"Fetching Gmail messages for {email_address}...")
        messages = gmail_auth.fetch_recent_messages(email_address, days=365, max_results=max_results)
        print(f"Loaded {len(messages)} Gmail messages for {email_address}")
        for msg in messages:
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "")
            snippet = msg.get("snippet", "")
            body = subject + "\n" + snippet
            sent_date = msg.get("internalDate")
            doc = Document(
                page_content=body,
                metadata={
                    "source": "Gmail",
                    "bucket": email_address,
                    "item": msg["id"],
                    "deleted": False,
                    "subject": subject,
                    "snippet": snippet,
                    "internalDate": sent_date,
                },
            )
            documents.append(doc)
            upsert_file_record(
                conn,
                source="gmail",
                item=subject,
                hash_value="",
                account=email_address,
                item_date=sent_date,
            )
    return documents
