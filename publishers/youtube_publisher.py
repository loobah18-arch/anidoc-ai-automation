"""
YouTube Data API v3 Auto-Publisher for 4K Phonk / Scene Edits.
"""
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

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
