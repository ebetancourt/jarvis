from gmail_auth import GmailAuth


def main():
    print("Starting Gmail OAuth flow to connect a new account...")
    auth = GmailAuth()
    # This will trigger the OAuth flow and save the credentials and email address
    auth.authenticate("")
    email = auth.get_user_email("")
    print(f"Successfully connected Gmail account: {email}")


if __name__ == "__main__":
    main()
