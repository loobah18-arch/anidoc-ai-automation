# Upload Destination Configuration Guide

This guide explains how to configure anidoc to upload rendered videos to YouTube, Google Drive, or both.

## Quick Start

### Upload to YouTube (default)
```bash
python main.py --character gojo --upload --upload-to youtube
```

### Upload to Google Drive
```bash
python main.py --character gojo --upload --upload-to gdrive
```

### Upload to Both
```bash
python main.py --character gojo --upload --upload-to both
```

---

## Google Drive Setup

### Option 1: Service Account (Recommended for automation)

1. **Create a Service Account:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create or select a project
   - Navigate to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "anidoc-uploader")
   - Grant it no roles (we'll share the folder with it)

2. **Enable Google Drive API:**
   - In Cloud Console, go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

3. **Create and Download Key:**
   - In Service Accounts, click on your new account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose JSON format
   - Download the JSON file

4. **Share Your Upload Folder:**
   - Create a folder in Google Drive where videos will be uploaded
   - Right-click → "Share"
   - Add the service account email (from the JSON file, looks like `xxx@xxx.iam.gserviceaccount.com`)
   - Give it "Editor" permission

5. **Get Folder ID:**
   - Open the folder in Google Drive
   - Copy the ID from the URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`

6. **Configure Environment Variables:**
   ```bash
   export GDRIVE_CREDENTIALS='{"type":"service_account",...}'  # Full JSON content
   export GDRIVE_UPLOAD_FOLDER_ID='your-folder-id-here'
   ```

### Option 2: OAuth2 (For personal use)

1. **Create OAuth2 Credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Google Drive API (same as above)
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Desktop app" or "Web application"
   - Download the JSON file

2. **Get Refresh Token:**
   - Use [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
   - Configure to use your own credentials
   - Authorize Google Drive API v3
   - Exchange authorization code for tokens
   - Copy the refresh token

3. **Configure Environment Variables:**
   ```bash
   export GDRIVE_CREDENTIALS='{"token":"...","refresh_token":"...","client_id":"...","client_secret":"..."}'
   export GDRIVE_UPLOAD_FOLDER_ID='your-folder-id-here'
   ```

---

## GitHub Actions Setup

### Add Secrets to Your Repository

1. Go to your repository on GitHub
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Add the following secrets:

**For Google Drive:**
- `GDRIVE_CREDENTIALS` - Full JSON content from service account key file
- `GDRIVE_UPLOAD_FOLDER_ID` - The folder ID where videos should be uploaded

**For YouTube (if needed):**
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

### Use in Workflow

When manually triggering the workflow:
1. Go to "Actions" tab
2. Select "Daily 4K Phonk / Scene Edit Generator & YouTube Auto-Upload"
3. Click "Run workflow"
4. Choose upload destination from dropdown:
   - `youtube` - Upload only to YouTube
   - `gdrive` - Upload only to Google Drive
   - `both` - Upload to both platforms

---

## Security Notes

⚠️ **Important:**
- **Never commit credentials to git** - Always use environment variables or GitHub Secrets
- Service account JSON files contain private keys - keep them secure
- For GitHub Actions, only use repository secrets, never hardcode credentials

✅ **What's Safe:**
- Only `.mp4` video files are uploaded
- Source code is **never** uploaded to YouTube or Google Drive
- The workflow artifact upload (GitHub) only includes `output/*.mp4` and `scratch/*.ass` files

---

## Troubleshooting

### "No credentials" error
- Ensure `GDRIVE_CREDENTIALS` environment variable is set
- Check that the JSON is valid (use `python -m json.tool < credentials.json`)

### "Permission denied" error
- Make sure the service account email has been shared with the upload folder
- Grant "Editor" permission to the service account

### "Invalid credentials" error
- Verify the service account JSON is complete and valid
- Ensure Google Drive API is enabled in your Cloud project
- Check that the credentials haven't expired (OAuth2 tokens)

---

## Examples

### Local CLI Usage
```bash
# Upload Gojo edit to Google Drive only
python main.py --character gojo --duration 22 --upload --upload-to gdrive

# Upload to specific folder
python main.py --character sukuna --duration 22 --upload --upload-to gdrive --gdrive-upload-folder "1ABC123XYZ"

# Upload to both YouTube and Google Drive
python main.py --character spiderman --duration 22 --upload --upload-to both --privacy unlisted
```

### GitHub Actions
The workflow automatically uploads based on your configuration. By default, scheduled runs upload to YouTube. You can change this by modifying the workflow file or using manual dispatch with different options.
