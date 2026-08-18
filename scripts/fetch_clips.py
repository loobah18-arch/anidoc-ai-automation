#!/usr/bin/env python3
"""
CLI Tool to fetch & slice action clips from GitHub repos and public sources.
"""
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.public_api_fetcher import (
    fetch_character_scenepack,
    fetch_from_github_repo,
    CURATED_CLIP_QUERIES
)
from core.clip_manager import list_available_character_clips, CHARACTER_THEMES
from config.settings import MARVEL_DIR, JJK_DIR

def main():
    parser = argparse.ArgumentParser(description="Fetch and slice action clips from GitHub Repos or Public APIs")
    parser.add_argument("--character", type=str, default=None, help="Character key (e.g. spiderman, gojo, sukuna, thor, ironman, toji)")
    parser.add_argument("--github-repo", type=str, default=None, help="GitHub repository URL or slug (e.g. 'owner/repo') to fetch clips from")
    parser.add_argument("--url", type=str, default=None, help="Custom public video URL or scenepack link")
    parser.add_argument("--list", action="store_true", help="List all local clips in library")
    parser.add_argument("--all", action="store_true", help="Fetch clips for all main characters")
    
    args = parser.parse_args()
    
    if args.list:
        clips_map = list_available_character_clips()
        print("\n🎬 Local Video Clips Library:")
        for char, clips in clips_map.items():
            print(f"  • [{char.upper()}] ({len(clips)} clips):")
            for c in clips:
                print(f"      - {c['filename']} ({c['size_kb']} KB)")
        if not clips_map:
            print("  (No clips downloaded yet)")
        print()
        return

    if args.github_repo:
        print(f"🐙 Fetching clips from GitHub repository: {args.github_repo}...")
        dest_dir = MARVEL_DIR if (args.character and CHARACTER_THEMES.get(args.character, {}).get("universe") == "marvel") else JJK_DIR
        downloaded = fetch_from_github_repo(args.github_repo, dest_dir, character_filter=args.character)
        print(f"✅ Fetched {len(downloaded)} clips from GitHub.")
        return

    if args.all:
        for char in ["spiderman", "gojo", "sukuna", "ironman"]:
            print(f"\n📥 Sourcing clips for {char.upper()}...")
            fetch_character_scenepack(char, max_clips=8)
        return

    if not args.character:
        print("⚠️ Please specify --character, --github-repo, --list, or --all.")
        print("Available characters:", ", ".join(CHARACTER_THEMES.keys()))
        return

    char_key = args.character.lower()
    fetch_character_scenepack(char_key, custom_query_or_url=args.url, max_clips=10)

if __name__ == "__main__":
    main()
