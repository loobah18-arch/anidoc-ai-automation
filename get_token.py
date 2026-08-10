#!/usr/bin/env python3
"""
YouTube OAuth Refresh Token Generator Helper
Run this script if you need to generate a new REFRESH_TOKEN for YouTube Data API v3.
Usage:
  python get_token.py
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def main():
    print("=" * 65)
    print("  YouTube OAuth 2.0 Refresh Token Generator")
    print("=" * 65)

    client_id = input("Enter your CLIENT_ID: ").strip()
    client_secret = input("Enter your CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        print("Error: CLIENT_ID and CLIENT_SECRET are required.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob", "http://127.0.0.1"]
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    try:
        # Try local server first (if in browser)
        creds = flow.run_local_server(port=8088, prompt="consent", access_type="offline")
    except Exception:
        # Fallback to console flow
        creds = flow.run_console()

    print("\n" + "=" * 65)
    print("🎉 SUCCESS! Here are your credentials:")
    print("=" * 65)
    print(f"CLIENT_ID:     {client_id}")
    print(f"CLIENT_SECRET: {client_secret}")
    print(f"REFRESH_TOKEN: {creds.refresh_token}")
    print("=" * 65)

    # Save to config/youtube_token.json
    token_file = os.path.join(os.path.dirname(__file__), "config", "youtube_token.json")
    with open(token_file, "w") as f:
        json.dump({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": creds.refresh_token
        }, f, indent=2)
    print(f"Saved to {token_file}")

if __name__ == "__main__":
    main()
