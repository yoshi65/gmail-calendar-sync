#!/usr/bin/env python3
"""Script to get OAuth2 refresh token for Google APIs."""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

# OAuth2 scopes for Gmail and Calendar
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]


def get_refresh_token():
    """Get OAuth2 refresh token for Google APIs."""
    # Read client credentials from environment or .env file
    from dotenv import load_dotenv

    load_dotenv()

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env file"
        )
        return

    # Create OAuth2 flow
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    # Run the OAuth2 flow
    print("Starting OAuth2 flow...")
    print("A browser window will open for authentication.")
    print("Please complete the authentication and authorize the application.")

    credentials = flow.run_local_server(port=8080)

    print("\nSuccess! Your refresh token is:")
    print(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}")
    print("\nAdd this to your .env file to complete the setup.")

    return credentials.refresh_token


if __name__ == "__main__":
    get_refresh_token()
