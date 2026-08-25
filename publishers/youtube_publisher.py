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


STANDARD_COPYRIGHT_DISCLAIMER = """--------------------------------------------------
© COPYRIGHT DISCLAIMER & FAIR USE NOTICE:
Title 17, US Code (Sections 107-118 of Copyright Law):
This video is a non-commercial, transformative fan edit created for commentary, criticism, and entertainment purposes under Fair Use guidelines.

All visuals, footage, audio, and character trademarks belong to their respective copyright holders:
• Visual Media: MAPPA Co., Ltd., Gege Akutami, TOHO Animation, Shueisha, Marvel Studios, Walt Disney Studios.
• Audio/Music: Respective Phonk Music Producers / Rightsholders.

No copyright infringement intended. If you are a copyright owner and have concerns, please contact us directly for immediate removal or updated attribution.
--------------------------------------------------"""


def format_youtube_metadata(
    title: str,
    description: str,
    tags: Optional[list] = None,
    character_name: Optional[str] = None,
    universe: Optional[str] = None,
) -> tuple:
    """
    Enforces high-converting, policy-compliant YouTube Shorts metadata:
    - Title: max 95 characters, ensures '#shorts' tag included
    - Description: Includes title/details, Fair Use Copyright Disclaimer, and formatted hashtags
    - Tags: max 15 tags, stripped of '#' symbols
    """
    if tags is None:
        tags = []

    # 1. Clean Title
    title_str = (title or "Anime Phonk Edit").strip()
    if "#shorts" not in title_str.lower() and "#short" not in title_str.lower():
        if len(title_str) <= 87:
            title_str = f"{title_str} #shorts"
    clean_title = title_str[:95].strip()

    # 2. Clean & Deduplicate Tags
    base_tags = ["shorts", "anime", "amv", "phonk", "animeedit", "4kedit", "velocityedit", "viral"]
    if universe:
        base_tags.append(universe.lower())
    if character_name:
        base_tags.append(character_name.lower().replace(" ", ""))

    raw_tags = list(tags) + base_tags
    clean_tags = []
    seen = set()
    for t in raw_tags:
        cleaned = str(t).replace("#", "").strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            clean_tags.append(cleaned)
    clean_tags = clean_tags[:15]

    # 3. Clean & Enrich Description
    desc_str = (description or clean_title).strip()

    # Append Copyright Disclaimer if missing
    if "COPYRIGHT DISCLAIMER" not in desc_str.upper() and "FAIR USE" not in desc_str.upper():
        desc_str = f"{desc_str}\n\n{STANDARD_COPYRIGHT_DISCLAIMER}"

    # Build hashtag block
    hashtag_block = " ".join(f"#{t}" for t in clean_tags)
    if hashtag_block not in desc_str:
        desc_str = f"{desc_str}\n\n{hashtag_block}"

    return clean_title, desc_str, clean_tags


def upload_video_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    privacy_status: str = "public"
) -> Dict[str, Any]:
    """
    Uploads a video to YouTube using the Data API v3 with automatic title, hashtag, and copyright formatting.
    """
    access_token = get_valid_access_token()
    if not access_token:
        print("[YouTube] ⚠️ YouTube API credentials not configured in environment. Skipping upload.")
        return {"status": "skipped", "reason": "No credentials"}
        
    video_path = Path(video_path)
    if not video_path.exists():
        return {"status": "error", "reason": "Video file not found"}
        
    clean_title, clean_description, clean_tags = format_youtube_metadata(
        title=title,
        description=description,
        tags=tags,
    )

    print(f"🚀 [YouTube] Uploading {video_path.name} to YouTube...")
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        
        creds = Credentials(token=access_token)
        youtube = build("youtube", "v3", credentials=creds)
        
        body = {
            "snippet": {
                "title": clean_title,
                "description": clean_description,
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
