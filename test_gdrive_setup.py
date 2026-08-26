#!/usr/bin/env python3
"""
Quick test to verify Google Drive upload credentials are working.
"""
import os
import json
from pathlib import Path

def test_credentials():
    print("🔍 Testing Google Drive Upload Setup...")
    print("=" * 50)

    # Check environment variables
    creds = os.environ.get("GDRIVE_CREDENTIALS")
    folder_id = os.environ.get("GDRIVE_UPLOAD_FOLDER_ID")

    if not creds:
        print("❌ GDRIVE_CREDENTIALS not set")
        return False

    if not folder_id:
        print("❌ GDRIVE_UPLOAD_FOLDER_ID not set")
        return False

    print(f"✅ GDRIVE_CREDENTIALS: Found ({len(creds)} chars)")
    print(f"✅ GDRIVE_UPLOAD_FOLDER_ID: {folder_id}")

    # Parse credentials
    try:
        creds_data = json.loads(creds)
        print(f"✅ Credentials are valid JSON")
        print(f"📧 Service Account: {creds_data.get('client_email', 'N/A')}")
        print(f"📁 Project ID: {creds_data.get('project_id', 'N/A')}")
    except Exception as e:
        print(f"❌ Failed to parse credentials: {e}")
        return False

    # Test Google API libraries
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        print("✅ Google API libraries installed")
    except ImportError as e:
        print(f"❌ Missing Google API libraries: {e}")
        return False

    # Try to authenticate
    try:
        creds_obj = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        print("✅ Service account authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

    # Try to connect to Drive API
    try:
        service = build("drive", "v3", credentials=creds_obj)
        print("✅ Successfully connected to Google Drive API")
    except Exception as e:
        print(f"❌ Failed to connect to Drive API: {e}")
        return False

    print("\n" + "=" * 50)
    print("🎉 All tests passed!")
    print("\nYou can now upload videos to Google Drive:")
    print("  python main.py --character gojo --duration 15 --upload --upload-to gdrive")
    print("\nOr upload to both YouTube and Google Drive:")
    print("  python main.py --character sukuna --duration 20 --upload --upload-to both")

    return True

if __name__ == "__main__":
    success = test_credentials()
    exit(0 if success else 1)
