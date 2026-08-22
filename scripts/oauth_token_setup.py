#!/usr/bin/env python3
"""One-time local helper: mint a Google refresh token with Drive + YouTube scopes.

Usage (run on your phone):
    python3 scripts/oauth_token_setup.py <CLIENT_ID> <CLIENT_SECRET>

Starts a localhost server, opens the consent page, auto-catches the redirect.
"""
import http.server
import json
import subprocess
import sys
import threading
import urllib.parse
import urllib.request

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]
PORT = 8765
REPO = "loobah18-arch/anidoc-ai-automation"


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    client_id, client_secret = sys.argv[1], sys.argv[2]

    result = {"code": None}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result["code"] = qs.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>OK - you can close this tab.</h1>")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    redirect_uri = f"http://localhost:{PORT}"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    })
    print("Opening consent page in browser...")
    print(f"\n🔗 Consent URL:\n{auth_url}\n")
    subprocess.Popen(["termux-open-url", auth_url],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"Waiting for Google redirect on localhost:{PORT} ...")
    print("(If the browser shows an error or code parameter in URL, you can also paste the code/URL here)")
    
    # Non-blocking wait for HTTP redirect or stdin input
    def read_stdin():
        try:
            line = input("\n👉 Paste authorization code or redirect URL here: ").strip()
            if line:
                if "code=" in line:
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(line).query)
                    result["code"] = qs.get("code", [None])[0]
                else:
                    result["code"] = line
        except (EOFError, KeyboardInterrupt):
            pass

    threading.Thread(target=read_stdin, daemon=True).start()

    while result["code"] is None:
        server.handle_request()
    server.shutdown()
    print("✅ Got authorization code.")

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": result["code"],
        "grant_type": "authorization_code",
        "redirect_uri": f"http://localhost:{PORT}",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=60) as resp:
        payload = json.load(resp)

    if "refresh_token" not in payload:
        print(f"❌ No refresh_token returned: {payload}")
        return 1

    print(f"✅ Scopes granted:\n   {payload.get('scope', '(unknown)')}")
    proc = subprocess.run(
        ["gh", "secret", "set", "GDRIVE_REFRESH_TOKEN", "--repo", REPO,
         "--body", payload["refresh_token"]],
        capture_output=True, text=True)
    if proc.returncode == 0:
        print("✅ GitHub secret GDRIVE_REFRESH_TOKEN updated.")
    else:
        print(f"❌ gh failed: {proc.stderr}\nSet manually: gh secret set GDRIVE_REFRESH_TOKEN")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
