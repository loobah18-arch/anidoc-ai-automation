"""
Google Drive Publisher for AniDoc 4K Phonk / Scene Edits.
Uploads rendered videos to a specified Google Drive folder.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


def upload_video_to_gdrive(
    video_path: Path,
    title: str,
    description: str,
    folder_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uploads a video to Google Drive using the Drive API v3.

    Args:
        video_path: Path to the video file
        title: Video title (used as filename)
        description: Video description (stored in file description)
        folder_id: Google Drive folder ID to upload to (optional)

    Returns:
        Dictionary with status and file details
    """
    # Get credentials from environment
    gdrive_creds_raw = os.environ.get("GDRIVE_CREDENTIALS") or os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
    folder_id = folder_id or os.environ.get("GDRIVE_UPLOAD_FOLDER_ID") or os.environ.get("GDRIVE_FOLDER_ID")

    if not gdrive_creds_raw:
        print("[GoogleDrive] ⚠️ Google Drive credentials not configured in environment. Skipping upload.")
        return {"status": "skipped", "reason": "No credentials"}

    video_path = Path(video_path)
    if not video_path.exists():
        return {"status": "error", "reason": "Video file not found"}

    print(f"☁️  [GoogleDrive] Uploading {video_path.name} to Google Drive...")

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials

        # Parse credentials
        creds = None
        try:
            # Try as service account JSON
            if Path(gdrive_creds_raw).exists():
                with open(gdrive_creds_raw, "r") as f:
                    creds_data = json.load(f)
            else:
                creds_data = json.loads(gdrive_creds_raw)

            # Check if it's a service account
            if "type" in creds_data and creds_data["type"] == "service_account":
                creds = service_account.Credentials.from_service_account_info(
                    creds_data,
                    scopes=["https://www.googleapis.com/auth/drive.file"]
                )
            else:
                # OAuth2 credentials
                creds = Credentials(
                    token=creds_data.get("token"),
                    refresh_token=creds_data.get("refresh_token"),
                    token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=creds_data.get("client_id"),
                    client_secret=creds_data.get("client_secret"),
                    scopes=["https://www.googleapis.com/auth/drive.file"]
                )
        except Exception as e:
            print(f"[GoogleDrive] Failed to parse credentials: {e}")
            return {"status": "error", "reason": f"Invalid credentials: {e}"}

        # Build Drive API service
        drive_service = build("drive", "v3", credentials=creds)

        # Prepare file metadata
        file_metadata = {
            "name": f"{title}.mp4",
            "description": description
        }

        # Add to folder if specified
        if folder_id:
            file_metadata["parents"] = [folder_id]

        # Upload file
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True
        )

        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink"
        ).execute()

        file_id = file.get("id")
        file_link = file.get("webViewLink")

        # Make file publicly accessible (optional)
        try:
            drive_service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"}
            ).execute()
            print(f"✅ [GoogleDrive] Video uploaded successfully and made publicly accessible!")
        except Exception:
            print(f"✅ [GoogleDrive] Video uploaded successfully (private)!")

        print(f"📎 [GoogleDrive] View link: {file_link}")

        return {
            "status": "success",
            "file_id": file_id,
            "file_name": file.get("name"),
            "url": file_link,
            "download_link": file.get("webContentLink")
        }

    except ImportError:
        print("❌ [GoogleDrive] Missing required library. Install with: pip install google-api-python-client google-auth")
        return {"status": "error", "reason": "Missing google-api-python-client library"}
    except Exception as e:
        print(f"❌ [GoogleDrive] Upload failed: {e}")
        return {"status": "error", "error": str(e)}
