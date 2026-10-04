#!/usr/bin/env python3
"""
Main Entrypoint for AniDoc 4K Phonk / Scene Edit Automated Video Engine.
Supports Marvel & Jujutsu Kaisen 9:16 Shorts Generation, Web Studio Editor & YouTube Auto-Upload.
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

from config.settings import DEFAULT_DURATION
from core.clip_manager import CHARACTER_THEMES
from core.video_assembler import render_cinematic_edit
from publishers.youtube_publisher import upload_video_to_youtube
from studio.server import start_studio_server

def main():
    parser = argparse.ArgumentParser(description="AniDoc 4K Phonk / Scene Edit Automation Engine (Jujutsu Kaisen & Demon Slayer)")
    parser.add_argument("--character", type=str, default=None, help="Character key (e.g. gojo, sukuna, yuji, toji, tanjiro, rengoku, zenitsu, akaza, giyu, tengen)")
    parser.add_argument("--universe", type=str, choices=["jjk", "demonslayer", "demon_slayer", "marvel"], default=None, help="Universe filter (jjk, demonslayer, or marvel)")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help=f"Target video duration in seconds (default: {DEFAULT_DURATION})")
    parser.add_argument("--phonk", type=str, default=None, help="Phonk track name or ID from library (e.g. tokyo_drift_phonk, brazilian_phonk_montagem, dark_shadow_phonk, cyber_phonk_beat, gigachad_phonk)")
    parser.add_argument("--subtitle-style", type=str, default=None, help="Deprecated (subtitles disabled for 100%% clean video)")
    parser.add_argument("--subtitles", action="store_true", default=False, help="Deprecated (subtitles disabled for 100%% clean video)")
    parser.add_argument("--burn-subtitles", action="store_true", default=False, help="Deprecated (subtitles disabled for 100%% clean video)")
    parser.add_argument("--quote", type=str, default=None, help="Custom dialogue monologue quote")
    parser.add_argument("--title", type=str, default=None, help="Custom video title")
    parser.add_argument("--cc", type=str, default=None, help="4K HDR Color Grade Preset (jjk_void, sukuna_shrine, hinokami_flame, thunder_gold, water_breathing, flame_hashira, akaza_compass, cyber_phonk)")
    parser.add_argument("--gdrive-folder", type=str, default=None, help="Google Drive folder URL or ID to pull movie/episode footage from")
    parser.add_argument("--github-repo", type=str, default=None, help="GitHub repository URL or slug to fetch video clips from")
    parser.add_argument("--audio", type=str, default=None, help="Path to custom audio file")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 path")
    parser.add_argument("--upload", action="store_true", help="Upload rendered video to YouTube Shorts")
    parser.add_argument("--privacy", type=str, choices=["public", "unlisted", "private"], default="public", help="YouTube video privacy status")
    parser.add_argument("--refresh-clips", action="store_true", help="Download and slice a fresh scenepack for the character")
    parser.add_argument("--studio", action="store_true", help="Launch the AniDoc Studio Web Video Editing Software")
    parser.add_argument("--port", type=int, default=7860, help="Port for AniDoc Studio server (default: 7860)")
    
    args = parser.parse_args()
    
    # If --studio is specified, launch web video editor
    if args.studio:
        start_studio_server(port=args.port)
        return
        
    # Resolve character selection
    target_universe = args.universe
    if target_universe == "demon_slayer":
        target_universe = "demonslayer"

    chosen_char = args.character
    if chosen_char:
        if chosen_char not in CHARACTER_THEMES:
            raise ValueError(f"Unknown character '{chosen_char}'. Valid options: {list(CHARACTER_THEMES.keys())}")
        char_uni = CHARACTER_THEMES[chosen_char]["universe"]
        if target_universe and target_universe != char_uni:
            print(f"⚠️ [Main] Character '{chosen_char}' belongs to universe '{char_uni}', adjusting universe filter from '{target_universe}' to '{char_uni}'.")
        target_universe = char_uni
    else:
        if not target_universe:
            # Randomly select between the two supported anime universes
            target_universe = random.choice(["demonslayer", "jjk"])
        eligible = [k for k, v in CHARACTER_THEMES.items() if v["universe"] == target_universe]
        if not eligible:
            raise ValueError(f"No characters found for universe '{target_universe}'")
        chosen_char = random.choice(eligible)
            
    print(f"🔥 [AniDoc 4K Edit] Selected Character: {chosen_char} ({CHARACTER_THEMES[chosen_char]['universe'].upper()})")
    
    # Render Video (100% Clean Pure Video, Zero Subtitles)
    result = render_cinematic_edit(
        character_key=chosen_char,
        audio_path=Path(args.audio) if args.audio else None,
        phonk_track=args.phonk,
        output_path=Path(args.output) if args.output else None,
        target_duration=args.duration,
        subtitle_style="viral_karaoke",
        burn_subtitles=False,
        enable_subtitles=False,
        custom_quote=args.quote,
        custom_title=args.title,
        cc_preset=args.cc,
        github_repo=args.github_repo,
        gdrive_folder=args.gdrive_folder,
        auto_fetch_clips=True,
        force_refresh=args.refresh_clips
    )
    
    output_path = result["output_path"]
    metadata = result["metadata"]
    
    print("\n=======================================================")
    print("🎉 4K Phonk / Scene Edit Short Rendered Successfully!")
    print(f"📁 Video Path: {output_path}")
    print(f"⏱️  Duration:   {result['duration']:.2f}s ({result['cuts_count']} beat-synced cuts)")
    print(f"💾 File Size:  {result['file_size_kb']} KB")
    print(f"🎧 Audio:      {result.get('audio_used', 'Phonk Audio')}")
    print(f"✨ Subtitles:  {result.get('subtitle_style', 'viral_karaoke')}")
    print(f"🎨 Color CC:   {result.get('cc_preset', 'marvel_hdr')}")
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
