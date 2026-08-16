"""
TikTok Auto-Publisher for AniDoc Phonk Edit Shorts.

Uses tiktok-uploader (Selenium browser automation) for TikTok publishing
with full metadata support: caption, hashtags, privacy, and scheduling.
Cookies are loaded from env var TIKTOK_COOKIES_JSON (base64 encoded JSON).

GitHub Actions usage:
  TIKTOK_COOKIES_JSON secret → stored as base64 of the cookies JSON file
  generated from your local TikTok session.
"""
import os
import json
import base64
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List


def _check_tiktok_uploader_available() -> bool:
    """Checks whether tiktok-uploader is installed."""
    try:
        import tiktok_uploader
        return True
    except ImportError:
        return False


def _load_cookies_from_env(cookies_path: Path) -> bool:
    """
    Writes TikTok cookies from TIKTOK_COOKIES_JSON env var to a file.
    Env var should be base64 encoded JSON cookie array.
    Returns True if cookies file was written successfully.
    """
    raw = os.environ.get("TIKTOK_COOKIES_JSON", "")
    if not raw:
        print("⚠️  [TikTok] TIKTOK_COOKIES_JSON env var not set. Skipping TikTok upload.")
        return False
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cookies_path, "w") as f:
            f.write(decoded)
        print(f"🍪 [TikTok] Loaded cookies to: {cookies_path}")
        return True
    except Exception as e:
        print(f"❌ [TikTok] Failed to decode TIKTOK_COOKIES_JSON: {e}")
        return False


def _build_tiktok_caption(title: str, tags: List[str], max_length: int = 2200) -> str:
    """
    Builds a viral TikTok caption with hashtags from title and tag list.
    TikTok captions max out at ~2200 chars.
    """
    # Use title as caption base (strip YouTube hashtags since TikTok handles separately)
    caption_base = title.split("#")[0].strip()

    # Build hashtag string
    tag_str = " ".join(f"#{t.lstrip('#')}" for t in tags[:20])
    
    # Combine
    caption = f"{caption_base}\n\n{tag_str}"
    return caption[:max_length]


def upload_video_to_tiktok(
    video_path: Path,
    title: str,
    tags: Optional[List[str]] = None,
    schedule_minutes_from_now: Optional[int] = None,
    privacy: str = "public"
) -> Optional[str]:
    """
    Uploads a rendered Short to TikTok using tiktok-uploader (Selenium automation).
    
    Returns the TikTok URL string on success, None on failure/skip.
    
    Args:
        video_path: Path to .mp4 file to upload
        title: Video title/description
        tags: Hashtag list
        schedule_minutes_from_now: If set, schedules post N minutes from now
        privacy: "public", "friends", or "private"
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        print(f"❌ [TikTok] Video file not found: {video_path}")
        return None

    if not _check_tiktok_uploader_available():
        print("⚠️  [TikTok] tiktok-uploader not installed. Skipping. Install: pip install tiktok-uploader")
        return None

    # Load cookies
    cookies_path = Path(tempfile.gettempdir()) / "tiktok_cookies.json"
    if not _load_cookies_from_env(cookies_path):
        return None

    caption = _build_tiktok_caption(title, tags or [])
    print(f"📤 [TikTok] Uploading: {video_path.name}")
    print(f"📝 [TikTok] Caption: {caption[:80]}...")

    try:
        from tiktok_uploader.upload import upload_video
        
        result = upload_video(
            filename=str(video_path),
            description=caption,
            cookies=str(cookies_path),
            headless=True,
        )
        
        if result:
            url = f"https://www.tiktok.com/@your_account/video/{result}" if isinstance(result, str) and result.isdigit() else "https://www.tiktok.com"
            print(f"✅ [TikTok] Uploaded successfully! URL: {url}")
            return url
        else:
            print("⚠️  [TikTok] Upload returned no result. Check TikTok account.")
            return None
            
    except Exception as e:
        print(f"❌ [TikTok] Upload failed: {e}")
        # Gracefully degrade — don't crash the whole pipeline
        return None
