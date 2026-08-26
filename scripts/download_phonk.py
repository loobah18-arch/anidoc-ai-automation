#!/usr/bin/env python3
"""
CLI Tool to download popular Phonk background music for AniDoc edits.
"""
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.phonk_manager import (
    POPULAR_PHONK_CATALOG,
    list_available_phonk_tracks,
    download_phonk_track,
    ensure_popular_phonk_library
)

def main():
    parser = argparse.ArgumentParser(description="Download popular Phonk BGM from the internet")
    parser.add_argument("--all", action="store_true", help="Download all curated popular phonk tracks")
    parser.add_argument("--track", type=str, default=None, help="Specific track ID or name to download")
    parser.add_argument("--query", type=str, default=None, help="Custom search query for phonk music")
    parser.add_argument("--list", action="store_true", help="List currently available phonk tracks")
    
    args = parser.parse_args()
    
    if args.list:
        tracks = list_available_phonk_tracks()
        print(f"\n🎧 Found {len(tracks)} Phonk Tracks in Library:")
        for t in tracks:
            print(f"  • [{t['id']}] {t['title']} ({t['genre']} - {t['bpm']} BPM, Drop: {t['default_drop']}s, Size: {t['size_kb']} KB)")
        print()
        return

    if args.all:
        print("🚀 Downloading full popular Phonk library...")
        ensure_popular_phonk_library(min_tracks=6)
        print("✅ Finished downloading popular Phonk library.")
    elif args.track or args.query:
        track_id = args.track or "custom_phonk"
        download_phonk_track(track_id, args.query)
    else:
        print("🎧 Downloading essential Phonk tracks...")
        ensure_popular_phonk_library(min_tracks=4)

if __name__ == "__main__":
    main()
