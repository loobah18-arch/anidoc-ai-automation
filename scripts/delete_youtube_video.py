#!/usr/bin/env python3
"""Delete a video from YouTube using repository OAuth credentials."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publishers.youtube_publisher import get_valid_access_token


def delete_video(video_id: str) -> bool:
    access_token = get_valid_access_token()
    if not access_token:
        print("[YouTube] ⚠️ No access token available.")
        return False
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=access_token)
    youtube = build("youtube", "v3", credentials=creds)
    try:
        youtube.videos().delete(id=video_id).execute()
        print(f"[YouTube] 🗑️ Successfully deleted video {video_id}")
        return True
    except Exception as e:
        print(f"[YouTube] ❌ Failed to delete video {video_id}: {e}")
        return False


if __name__ == "__main__":
    vid = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VIDEO_ID", "")
    if not vid:
        sys.exit("Usage: python3 delete_youtube_video.py <video_id>")
    delete_video(vid)
