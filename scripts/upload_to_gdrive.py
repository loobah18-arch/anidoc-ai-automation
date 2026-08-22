#!/usr/bin/env python3
"""Upload rendered edits + code snapshots to Google Drive, one folder per run.

Env:
    CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN  - Google OAuth credentials
    GDRIVE_FOLDER_URL                        - destination Drive folder (URL or ID)

Usage:
    python3 scripts/upload_to_gdrive.py output/*.mp4 code_snapshot.zip --label Run_123_2026-08-22_abc1234
"""
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth2.googleapis.com/token"
FILES_URL = "https://www.googleapis.com/drive/v3/files"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"


def get_access_token() -> str:
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN") or os.environ.get("REFRESH_TOKEN")
    if not refresh_token:
        raise ValueError("Neither GDRIVE_REFRESH_TOKEN nor REFRESH_TOKEN set.")
    data = urllib.parse.urlencode({
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["access_token"]


def extract_folder_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip().rstrip("/")
    match = re.search(r"/folders/([A-Za-z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)
    return url_or_id


def api(token: str, method: str, url: str, payload=None):
    body = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json; charset=UTF-8"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def find_folder(token: str, name: str, parent_id: str):
    try:
        q = (f"name = '{name}' and '{parent_id}' in parents and "
             f"mimeType = '{FOLDER_MIME}' and trashed = false")
        url = FILES_URL + "?" + urllib.parse.urlencode({
            "q": q,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true"
        })
        items = api(token, "GET", url).get("files", [])
        return items[0]["id"] if items else None
    except Exception as err:
        print(f"⚠️ Folder search query notice: {err}")
        return None


def ensure_run_folder(token: str, label: str, parent_id: str) -> str:
    existing = find_folder(token, label, parent_id)
    if existing:
        print(f"📁 Reusing existing folder: {label}")
        return existing
    try:
        created = api(token, "POST", FILES_URL + "?supportsAllDrives=true", {
            "name": label,
            "mimeType": FOLDER_MIME,
            "parents": [parent_id],
        })
        print(f"📁 Created folder: {label}")
        return created["id"]
    except Exception as err:
        print(f"⚠️ Subfolder creation notice under {parent_id}: {err}")
        print(f"📁 Falling back to uploading directly into target Google Drive folder {parent_id}")
        return parent_id


def resumable_upload(token: str, path: str, folder_id: str) -> str:
    size = os.path.getsize(path)
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    meta = {"name": os.path.basename(path), "parents": [folder_id]}

    init_req = urllib.request.Request(
        UPLOAD_URL + "?uploadType=resumable&supportsAllDrives=true",
        data=json.dumps(meta).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime,
            "X-Upload-Content-Length": str(size),
        },
        method="POST",
    )
    with urllib.request.urlopen(init_req, timeout=120) as resp:
        session_url = resp.headers["Location"]

    chunk = 16 * 1024 * 1024
    offset = 0
    with open(path, "rb") as f:
        while offset < size:
            f.seek(offset)
            blob = f.read(chunk)
            put_req = urllib.request.Request(
                session_url,
                data=blob,
                headers={
                    "Content-Length": str(len(blob)),
                    f"Content-Range": f"bytes {offset}-{offset + len(blob) - 1}/{size}",
                },
                method="PUT",
            )
            try:
                with urllib.request.urlopen(put_req, timeout=600) as resp:
                    result = json.load(resp)
                    break
            except urllib.error.HTTPError as err:
                if err.code == 308:
                    rng = err.headers.get("Range", "")
                    offset = int(rng.split("-")[1]) + 1 if rng else offset + len(blob)
                    continue
                raise
            finally:
                pass

    file_id = result["id"]
    print(f"✅ Uploaded {os.path.basename(path)} ({size // (1024 * 1024)} MB)")
    print(f"   🔗 https://drive.google.com/file/d/{file_id}/view")
    return file_id


def main() -> int:
    args = sys.argv[1:]
    label = None
    if "--label" in args:
        idx = args.index("--label")
        label = args[idx + 1]
        del args[idx:idx + 2]

    files = [a for a in args if not a.startswith("-")]
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        print("⚠️ No files to upload.")
        return 0

    dest = os.environ.get("GDRIVE_FOLDER_URL", "").strip()
    if not dest:
        print("⚠️ GDRIVE_FOLDER_URL not set; skipping Google Drive upload.")
        return 0

    parent_id = extract_folder_id(dest)
    token = get_access_token()
    run_folder_id = ensure_run_folder(token, label, parent_id)

    uploaded = []
    for path in files:
        for attempt in range(1, 4):
            try:
                uploaded.append(resumable_upload(token, path, run_folder_id))
                break
            except urllib.error.HTTPError as err:
                body = err.read().decode(errors="replace")
                if err.code == 403:
                    print(f"⚠️ Google Drive upload notice (HTTP 403): refresh token missing drive.file scope. "
                          f"Artifacts preserved in Telegram & Actions.")
                    return 0
                print(f"⚠️ Attempt {attempt}/3 failed for {path}: HTTP {err.code}")
                if attempt == 3:
                    print(f"⚠️ Google Drive upload skipped due to HTTP {err.code}")
                    return 0
                time.sleep(5 * attempt)

    print(f"\n📦 Run archive complete: {len(uploaded)} file(s) in folder "
          f"https://drive.google.com/drive/folders/{run_folder_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
