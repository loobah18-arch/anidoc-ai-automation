#!/bin/bash
# Google Drive Setup Script for AniDoc
# This script helps you set up Google Drive credentials for uploading videos

echo "🔧 Google Drive Setup for AniDoc"
echo "=================================="
echo ""
echo "This script will help you configure Google Drive uploads."
echo ""
echo "⚠️  You need:"
echo "   1. A Google Cloud Project with Drive API enabled"
echo "   2. Service Account credentials (JSON file)"
echo ""
echo "📚 Follow the guide: anidoc/docs/UPLOAD_SETUP.md"
echo ""

# Check if credentials file exists
if [ -f ~/gdrive-service-account.json ]; then
    echo "✅ Found: ~/gdrive-service-account.json"
    echo ""
    read -p "Use this file? (y/n): " use_existing

    if [ "$use_existing" = "y" ]; then
        CREDS_FILE=~/gdrive-service-account.json
    else
        read -p "Enter path to your credentials JSON file: " CREDS_FILE
    fi
else
    echo "📁 No credentials file found at ~/gdrive-service-account.json"
    echo ""
    read -p "Enter path to your credentials JSON file: " CREDS_FILE
fi

# Validate file exists
if [ ! -f "$CREDS_FILE" ]; then
    echo "❌ Error: File not found: $CREDS_FILE"
    exit 1
fi

# Validate JSON
if ! python3 -m json.tool "$CREDS_FILE" > /dev/null 2>&1; then
    echo "❌ Error: Invalid JSON file"
    exit 1
fi

echo "✅ Credentials file is valid JSON"
echo ""

# Extract service account email
SERVICE_ACCOUNT_EMAIL=$(python3 -c "import json; f=open('$CREDS_FILE'); d=json.load(f); print(d.get('client_email', 'N/A'))")

echo "📧 Service Account Email: $SERVICE_ACCOUNT_EMAIL"
echo ""
echo "⚠️  IMPORTANT: Share your Google Drive upload folder with this email!"
echo "   1. Create a folder in Google Drive"
echo "   2. Right-click → Share"
echo "   3. Add: $SERVICE_ACCOUNT_EMAIL"
echo "   4. Give 'Editor' permission"
echo ""

read -p "Have you shared the folder? (y/n): " shared

if [ "$shared" != "y" ]; then
    echo "⚠️  Please share the folder first, then run this script again."
    exit 0
fi

read -p "Enter your Google Drive folder ID (from the URL): " FOLDER_ID

echo ""
echo "📝 Setting up environment variables..."
echo ""

# Export for current session
export GDRIVE_CREDENTIALS="$(cat $CREDS_FILE)"
export GDRIVE_UPLOAD_FOLDER_ID="$FOLDER_ID"

echo "✅ Environment variables set for current session"
echo ""
echo "🔒 To persist these, add to your ~/.bashrc or ~/.zshrc:"
echo ""
echo "export GDRIVE_CREDENTIALS='$GDRIVE_CREDENTIALS'"
echo "export GDRIVE_UPLOAD_FOLDER_ID='$FOLDER_ID'"
echo ""

# Offer to add to GitHub secrets
echo "📤 GitHub Secrets Setup"
echo "======================"
echo ""
echo "To use in GitHub Actions, run:"
echo ""
echo "gh secret set GDRIVE_CREDENTIALS < $CREDS_FILE"
echo "gh secret set GDRIVE_UPLOAD_FOLDER_ID -b\"$FOLDER_ID\""
echo ""

read -p "Add to GitHub secrets now? (y/n): " add_secrets

if [ "$add_secrets" = "y" ]; then
    cd ~/anidoc || exit 1

    echo "Adding GDRIVE_CREDENTIALS..."
    gh secret set GDRIVE_CREDENTIALS < "$CREDS_FILE"

    echo "Adding GDRIVE_UPLOAD_FOLDER_ID..."
    echo "$FOLDER_ID" | gh secret set GDRIVE_UPLOAD_FOLDER_ID

    echo ""
    echo "✅ GitHub secrets added successfully!"
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Test your setup:"
echo "  cd ~/anidoc"
echo "  python main.py --character gojo --duration 15 --upload --upload-to gdrive"
echo ""
