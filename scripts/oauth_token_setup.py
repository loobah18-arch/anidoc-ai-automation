#!/usr/bin/env python3
"""One-time local helper: mint a Google refresh token with Drive + YouTube scopes.

Usage (run on your phone, NOT in CI):
    python3 scripts/oauth_token_setup.py <CLIENT_ID> <CLIENT_SECRET>

Then update the GitHub secret when prompted (requires gh CLI logged in).
"""
import json
import sys
import urllib.parse
import urllib.request

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/youtube.upload",
]
REDIRECT_URI = "urn:ietf:wg:oob"  # paste-the-code flow, works anywhere


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    client_id, client_secret = sys.argv[1], sys.argv[2]

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    })
    print("\n1. Open this URL in your browser and approve ALL permissions:\n")
    print(auth_url)
    code = input("\n2. Paste the authorization code here: ").strip()

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=60) as resp:
        payload = json.load(resp)

    if "refresh_token" not in payload:
        print("❌ No refresh_token returned. Re-run and make sure 'prompt=consent' screen shows all checkboxes ticked.")
        return 1

    print(f"\n✅ Got refresh token with scopes:\n   {payload.get('scope', '(unknown)')}")
    answer = input("\nUpdate GitHub secret REFRESH_TOKEN now? [y/N] ").strip().lower()
    if answer == "y":
        import subprocess
        proc = subprocess.run(
            ["gh", "secret", "set", "REFRESH_TOKEN", "--repo",
             "loobah18-arch/anidoc-ai-automation", "--body", payload["refresh_token"]],
            capture_output=True, text=True)
        if proc.returncode == 0:
            print("✅ Secret REFRESH_TOKEN updated.")
        else:
            print(f"❌ gh failed: {proc.stderr}")
            print("Set it manually: gh secret set REFRESH_TOKEN")
    else:
        print("\nRefresh token (set it later):\n" + payload["refresh_token"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
