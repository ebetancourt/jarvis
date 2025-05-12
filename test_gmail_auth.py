from common.google_auth import GmailAuth


def main():
    # Initialize the auth manager
    auth = GmailAuth()

    # Test with a Gmail account
    source_id = "gmail:ebetan@gmail.com"

    try:
        # This will trigger the OAuth2 flow if no valid credentials exist
        service = auth.get_gmail_service(source_id)

        # Test the connection by getting the user's profile
        profile = service.users().getProfile(userId="me").execute()
        print(f"Successfully authenticated as: {profile['emailAddress']}")

    except Exception as e:
        print(f"Error during authentication: {str(e)}")


if __name__ == "__main__":
    main()
