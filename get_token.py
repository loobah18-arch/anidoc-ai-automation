#!/usr/bin/env python3
"""
YouTube OAuth Refresh Token Generator Helper
Optimized for Termux, Linux, and Cloud environments.
Usage:
  python get_token.py
  OR
  python get_token.py --client-id YOUR_ID --client-secret YOUR_SECRET
"""

import os
import sys
import json
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def main():
    parser = argparse.ArgumentParser(description="YouTube OAuth 2.0 Refresh Token Generator")
    parser.add_argument("--client-id", type=str, default=None, help="OAuth Client ID")
    parser.add_argument("--client-secret", type=str, default=None, help="OAuth Client Secret")
    args = parser.parse_args()

    print("=" * 65)
    print("  🎬 YouTube OAuth 2.0 Permanent Refresh Token Generator")
    print("=" * 65)

    client_id = args.client_id or input("Enter your CLIENT_ID: ").strip()
    client_secret = args.client_secret or input("Enter your CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        print("\n❌ Error: Both CLIENT_ID and CLIENT_SECRET are required.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                "http://localhost:8088/",
                "http://127.0.0.1:8088/",
                "http://localhost",
                "urn:ietf:wg:oauth:2.0:oob"
            ]
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    
    print("\n👉 Choose authentication method:")
    print("  [1] Local Browser (opens automatically on localhost:8088)")
    print("  [2] Manual Link / Console Code Flow (Recommended for Termux/Mobile)")
    mode = input("Enter choice (1 or 2) [Default: 2]: ").strip() or "2"

    creds = None
    if mode == "1":
        try:
            creds = flow.run_local_server(port=8088, prompt="consent", access_type="offline")
        except Exception as e:
            print(f"Local server notice ({e}), falling back to console link...")
            creds = flow.run_console(prompt="consent", access_type="offline")
    else:
        try:
            creds = flow.run_console(prompt="consent", access_type="offline")
        except Exception:
            creds = flow.run_local_server(port=8088, prompt="consent", access_type="offline")

    if not creds or not creds.refresh_token:
        print("\n⚠️ Note: If REFRESH_TOKEN is empty, your Google account had already authorized this app previously.")
        print("To force a new refresh token, re-run and make sure you approve all permissions.")
        return

    print("\n" + "=" * 65)
    print("🎉 SUCCESS! Your Permanent YouTube Credentials:")
    print("=" * 65)
    print(f"CLIENT_ID:     {client_id}")
    print(f"CLIENT_SECRET: {client_secret}")
    print(f"REFRESH_TOKEN: {creds.refresh_token}")
    print("=" * 65)

    # Save to config/youtube_token.json and update .env
    token_dir = os.path.join(os.path.dirname(__file__), "config")
    os.makedirs(token_dir, exist_ok=True)
    token_file = os.path.join(token_dir, "youtube_token.json")
    with open(token_file, "w") as f:
        json.dump({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": creds.refresh_token
        }, f, indent=2)
    print(f"\n[✔] Saved locally to: {token_file}")

    # Automatically set GitHub Secrets if gh is installed and logged in
    try:
        import subprocess
        subprocess.run(["gh", "secret", "set", "CLIENT_ID", "--body", client_id, "--repo", "loobah18-arch/anidoc-ai-automation"], capture_output=True)
        subprocess.run(["gh", "secret", "set", "CLIENT_SECRET", "--body", client_secret, "--repo", "loobah18-arch/anidoc-ai-automation"], capture_output=True)
        subprocess.run(["gh", "secret", "set", "REFRESH_TOKEN", "--body", creds.refresh_token, "--repo", "loobah18-arch/anidoc-ai-automation"], capture_output=True)
        print("[✔] Automatically saved CLIENT_ID, CLIENT_SECRET, and REFRESH_TOKEN to GitHub Actions Secrets!")
    except Exception:
        pass

if __name__ == "__main__":
    main()
