"""
Automated YouTube Uploader & Scheduler Module
Integrates directly with YouTube Data API v3 using OAuth 2.0 (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
to upload full 1080p documentary videos, set high-ranking metadata,
upload custom 2D animated thumbnails, and track channel history.
"""

import os
import sys
import json
import time
import re
from pathlib import Path

# Google API client imports
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

from config import settings

def sanitize_youtube_tags(raw_tags) -> list:
    """Strict YouTube API tag validation."""
    if isinstance(raw_tags, str):
        raw_tags = [t.strip() for t in re.split(r'[,;\n]+', raw_tags)]
    
    clean = []
    total_chars = 0
    for t in raw_tags:
        cleaned = re.sub(r'[<>#\*\[\]"\'`]', '', str(t)).strip()
        if len(cleaned) < 2 or len(cleaned) > 40:
            continue
        if total_chars + len(cleaned) + 1 > 380:
            break
        if cleaned.lower() not in [c.lower() for c in clean]:
            clean.append(cleaned)
            total_chars += len(cleaned) + 1
            
    return clean if clean else ["2D Documentary", "True Crime Hindi", "AniDoc", "History"]

class YouTubePublisher:
    def __init__(self, client_id=None, client_secret=None, refresh_token=None):
        self.client_id = client_id or os.environ.get("CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("CLIENT_SECRET", "")
        self.refresh_token = refresh_token or os.environ.get("REFRESH_TOKEN", "")
        self.history_file = settings.BASE_DIR / "documentary_history.json"

    def get_authenticated_service(self):
        """Constructs authenticated YouTube Data API v3 client."""
        if not GOOGLE_API_AVAILABLE:
            raise RuntimeError("Google API client packages are not installed. Run: pip install google-api-python-client google-auth google-auth-oauthlib")

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            token_file = settings.CONFIG_DIR / "youtube_token.json"
            if token_file.exists():
                try:
                    with open(token_file, "r") as f:
                        tdata = json.load(f)
                        self.client_id = self.client_id or tdata.get("client_id")
                        self.client_secret = self.client_secret or tdata.get("client_secret")
                        self.refresh_token = self.refresh_token or tdata.get("refresh_token")
                except Exception:
                    pass

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError(
                "Missing YouTube OAuth credentials. Please set CLIENT_ID, CLIENT_SECRET, and REFRESH_TOKEN in your environment or GitHub Secrets."
            )

        creds = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"Token refresh notice: {e}")

        return build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        thumbnail_path: str = None,
        category_id: str = "27", # Education / Entertainment / Film
        privacy_status: str = "public",
        topic_name: str = None
    ) -> dict:
        """
        Uploads documentary video to YouTube with resumable stream,
        sets metadata, uploads custom thumbnail, and logs to history.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Clean title & tags
        clean_title = re.sub(r'[\*#_`]', '', str(title)).strip()[:95]
        valid_tags = sanitize_youtube_tags(tags)

        print(f"\n=======================================================")
        print(f"  [YOUTUBE UPLOAD] Uploading Documentary to YouTube...")
        print(f"  Title: {clean_title}")
        print(f"  Tags ({len(valid_tags)}): {', '.join(valid_tags[:5])}...")
        print(f"  Privacy: {privacy_status} | Category: {category_id}")
        print(f"=======================================================")

        meta_export = {
            "title": clean_title,
            "description": str(description)[:4000],
            "tags": valid_tags,
            "privacyStatus": privacy_status,
            "categoryId": category_id,
            "videoFile": str(video_path),
            "thumbnailFile": str(thumbnail_path) if thumbnail_path and Path(thumbnail_path).exists() else None,
            "uploaded_at": int(time.time()),
            "topic_name": topic_name or clean_title
        }

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            export_json = video_path.parent / "youtube_upload_metadata.json"
            with open(export_json, "w", encoding="utf-8") as f:
                json.dump(meta_export, f, indent=2, ensure_ascii=False)
            print(f"[!] CLIENT_ID / REFRESH_TOKEN not found in environment.")
            return {
                "status": "metadata_saved",
                "metadata_file": str(export_json),
                "video_id": None,
                "url": None
            }

        youtube = self.get_authenticated_service()

        body = {
            "snippet": {
                "title": meta_export["title"],
                "description": meta_export["description"],
                "tags": meta_export["tags"],
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        print("Initiating resumable upload stream...")
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  Uploaded {int(status.progress() * 100)}%...")

        video_id = response.get("id")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"\n🎉 SUCCESS! Video uploaded to YouTube: {video_url}")

        # Upload custom thumbnail if available
        if thumbnail_path and Path(thumbnail_path).exists() and video_id:
            try:
                print(f"Uploading custom thumbnail: {thumbnail_path}...")
                thumb_media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
                youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                print("🎉 Custom 2D thumbnail uploaded successfully!")
            except Exception as e:
                print(f"⚠️ Thumbnail upload notice: {e}")

        # Record to history
        meta_export["youtube_id"] = video_id
        meta_export["youtube_url"] = video_url
        self._record_history(meta_export)

        return {
            "status": "success",
            "video_id": video_id,
            "url": video_url
        }

    def _record_history(self, entry: dict):
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
        history.append(entry)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
