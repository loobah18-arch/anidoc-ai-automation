#!/usr/bin/env python3
"""
Main Entrypoint for AniDoc 4K Phonk / Scene Edit Automated Video Engine.
Supports Marvel & Jujutsu Kaisen 9:16 Shorts Generation & YouTube Auto-Upload.
"""
import sys
import argparse
import random
from pathlib import Path

# Load local .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    import os
                    os.environ[k] = v

from core.clip_manager import CHARACTER_THEMES
from core.video_assembler import render_cinematic_edit
from publishers.youtube_publisher import upload_video_to_youtube

def main():
    parser = argparse.ArgumentParser(description="AniDoc 4K Phonk / Scene Edit Automation Engine (Marvel & JJK)")
    parser.add_argument("--character", type=str, default=None, help="Character key (e.g. spiderman, gojo, sukuna, ironman, thor, toji)")
    parser.add_argument("--universe", type=str, choices=["marvel", "jjk"], default=None, help="Universe filter (marvel or jjk)")
    parser.add_argument("--duration", type=float, default=22.0, help="Target video duration in seconds (default: 22.0)")
    parser.add_argument("--audio", type=str, default=None, help="Path to custom Phonk/dialogue audio file")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 path")
    parser.add_argument("--upload", action="store_true", help="Upload rendered video to YouTube")
    parser.add_argument("--privacy", type=str, choices=["public", "unlisted", "private"], default="public", help="YouTube video privacy status")
    
    args = parser.parse_args()
    
    # Resolve character selection
    chosen_char = args.character
    if not chosen_char:
        if args.universe:
            eligible = [k for k, v in CHARACTER_THEMES.items() if v["universe"] == args.universe]
            chosen_char = random.choice(eligible)
        else:
            chosen_char = random.choice(list(CHARACTER_THEMES.keys()))
            
    print(f"🔥 [AniDoc 4K Edit] Selected Character: {chosen_char} ({CHARACTER_THEMES[chosen_char]['universe'].upper()})")
    
    # Render Video
    result = render_cinematic_edit(
        character_key=chosen_char,
        audio_path=Path(args.audio) if args.audio else None,
        output_path=Path(args.output) if args.output else None,
        target_duration=args.duration
    )
    
    output_path = result["output_path"]
    metadata = result["metadata"]
    
    print("\n=======================================================")
    print("🎉 4K Phonk / Scene Edit Short Rendered Successfully!")
    print(f"📁 Video Path: {output_path}")
    print(f"⏱️  Duration:   {result['duration']:.2f}s ({result['cuts_count']} beat-synced cuts)")
    print(f"💾 File Size:  {result['file_size_kb']} KB")
    print(f"🏷️  Title:      {metadata['title']}")
    print("=======================================================\n")
    
    # Upload to YouTube if requested
    if args.upload:
        upload_res = upload_video_to_youtube(
            video_path=output_path,
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata["tags"],
            privacy_status=args.privacy
        )
        if upload_res.get("status") == "success":
            print(f"🌟 Published to YouTube: {upload_res.get('url')}")
        else:
            print(f"⚠️ YouTube upload status: {upload_res.get('status')} ({upload_res.get('reason') or upload_res.get('error')})")

if __name__ == "__main__":
    main()
