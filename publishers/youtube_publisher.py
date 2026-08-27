"""
YouTube Data API v3 Auto-Publisher for 4K Phonk / Scene Edits.
"""
import os
import json
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

SHORTS_MAX_DURATION_SECONDS = 180.0


def validate_shorts_video(video_path: Path) -> Tuple[bool, str]:
    """Require a square video no longer than YouTube's Shorts limit."""
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height:format=duration",
                "-of", "json", str(video_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        info = json.loads(probe.stdout)
        stream = (info.get("streams") or [{}])[0]
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        duration = float((info.get("format") or {}).get("duration") or 0)
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        return False, f"Could not inspect video for Shorts requirements: {exc}"

    if not width or not height:
        return False, "Video has no readable video dimensions"
    if width != height:
        return False, f"Video must be square (1:1), got {width}x{height}"
    if duration <= 0:
        return False, "Video has no readable duration"
    if duration > SHORTS_MAX_DURATION_SECONDS:
        return False, f"Video must be 3 minutes or shorter, got {duration:.2f}s"

    return True, f"{width}x{height}, {duration:.2f}s"


def _shorts_title(title: str) -> str:
    """Keep the title within YouTube's limit and mark it as a Short."""
    clean_title = " ".join(str(title).split()).strip()
    if "#shorts" not in clean_title.lower():
        suffix = " #Shorts"
        clean_title = f"{clean_title[:100 - len(suffix)].rstrip()}{suffix}"
    return clean_title[:100]


def get_valid_access_token() -> Optional[str]:
    """Exchanges refresh token for a fresh access token if available."""
    access_token = os.environ.get("YOUTUBE_ACCESS_TOKEN") or os.environ.get("ACCESS_TOKEN")
    if access_token:
        return access_token
        
    client_secret_raw = os.environ.get("YOUTUBE_CLIENT_SECRET") or os.environ.get("CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN") or os.environ.get("REFRESH_TOKEN")
    client_id_direct = os.environ.get("YOUTUBE_CLIENT_ID") or os.environ.get("CLIENT_ID")
    
    if not refresh_token:
        return None
        
    client_id = None
    client_secret = None
    
    # 1. Try parsing client_secret_raw as JSON or file path
    if client_secret_raw:
        try:
            if Path(client_secret_raw).exists():
                with open(client_secret_raw, "r") as f:
                    data = json.load(f)
            else:
                data = json.loads(client_secret_raw)
                
            client_info = data.get("installed") or data.get("web") or {}
            client_id = client_info.get("client_id")
            client_secret = client_info.get("client_secret")
        except Exception:
            # client_secret_raw is the plain secret string
            client_secret = client_secret_raw
            
    if not client_id and client_id_direct:
        client_id = client_id_direct
        
    if not client_id or not client_secret:
        return None
        
    try:
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }, timeout=10)
        
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            print(f"[YouTube] Token refresh notice ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[YouTube] Notice refreshing access token: {e}")
        
    return None


def upload_video_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    privacy_status: str = "public"
) -> Dict[str, Any]:
    """
    Uploads a square video to YouTube using the Data API v3.

    YouTube classifies square or vertical videos up to three minutes as Shorts.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return {"status": "error", "reason": "Video file not found"}

    is_valid, validation_reason = validate_shorts_video(video_path)
    if not is_valid:
        print(f"[YouTube] ❌ Shorts validation failed: {validation_reason}")
        return {"status": "error", "reason": validation_reason}

    access_token = get_valid_access_token()
    if not access_token:
        print("[YouTube] ⚠️ YouTube API credentials not configured in environment. Skipping upload.")
        return {"status": "skipped", "reason": "No credentials"}

    print(f"🚀 [YouTube] Uploading square Short {video_path.name} ({validation_reason}) to YouTube...")
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        
        creds = Credentials(token=access_token)
        youtube = build("youtube", "v3", credentials=creds)
        
        clean_title = _shorts_title(title)
        clean_tags = [t.replace("#", "").strip() for t in tags][:15]
        
        body = {
            "snippet": {
                "title": clean_title,
                "description": description,
                "tags": clean_tags,
                "categoryId": "24"  # Entertainment / Animation
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        res = req.execute()
        
        video_id = res.get("id")
        video_url = f"https://youtube.com/shorts/{video_id}"
        print(f"✅ [YouTube] Video uploaded successfully! URL: {video_url}")
        return {
            "status": "success",
            "video_id": video_id,
            "url": video_url
        }
    except Exception as e:
        print(f"❌ [YouTube] Upload failed: {e}")
        return {"status": "error", "error": str(e)}
