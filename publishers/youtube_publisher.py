"""
YouTube Data API v3 Auto-Publisher for 4K Phonk / Scene Edits.
"""
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN, YOUTUBE_ACCESS_TOKEN

def get_valid_access_token() -> Optional[str]:
    """Exchanges refresh token for a fresh access token if available."""
    if YOUTUBE_ACCESS_TOKEN:
        return YOUTUBE_ACCESS_TOKEN
        
    client_secret_str = YOUTUBE_CLIENT_SECRET
    refresh_token = YOUTUBE_REFRESH_TOKEN
    
    if not client_secret_str or not refresh_token:
        return None
        
    try:
        if Path(client_secret_str).exists():
            with open(client_secret_str, "r") as f:
                data = json.load(f)
        else:
            data = json.loads(client_secret_str)
            
        client_info = data.get("installed") or data.get("web") or {}
        client_id = client_info.get("client_id")
        client_secret = client_info.get("client_secret")
        
        if not client_id or not client_secret:
            return None
            
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }, timeout=10)
        
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            print(f"[YouTube] Token refresh error: {resp.text}")
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
    Uploads a video to YouTube using the Data API v3.
    """
    access_token = get_valid_access_token()
    if not access_token:
        print("[YouTube] ⚠️ YouTube API credentials not configured in environment. Skipping upload.")
        return {"status": "skipped", "reason": "No credentials"}
        
    video_path = Path(video_path)
    if not video_path.exists():
        return {"status": "error", "reason": "Video file not found"}
        
    print(f"🚀 [YouTube] Uploading {video_path.name} to YouTube...")
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        
        creds = Credentials(token=access_token)
        youtube = build("youtube", "v3", credentials=creds)
        
        # Sanitize metadata
        clean_title = title[:95]
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
