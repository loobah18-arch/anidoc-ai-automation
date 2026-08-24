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

from core.clip_manager import CHARACTER_THEMES
from core.video_assembler import render_cinematic_edit
from core.ranking_assembler import render_ranking_countdown_edit
from core.download_saver import save_to_downloads
from publishers.youtube_publisher import upload_video_to_youtube
from studio.server import start_studio_server
from scripts.gdrive_amv_builder import run_gdrive_amv, SOURCE_FOLDER_ID as _AMV_SRC

def main():
    parser = argparse.ArgumentParser(description="AniDoc 4K Phonk / Scene Edit Automation Engine (Marvel & JJK)")
    parser.add_argument("--mode", type=str, choices=["single", "ranking", "gdrive-amv"], default="single",
                        help="Edit mode: single | ranking | gdrive-amv (hybrid AMV from Drive footage)")
    parser.add_argument("--amv-source-folder", type=str, default=None,
                        help=f"GDrive folder ID/URL with raw footage for gdrive-amv mode (default: {_AMV_SRC})")
    parser.add_argument("--ranking", action="store_true", help="Shortcut for --mode ranking (replicates Top 5 countdown format)")
    parser.add_argument("--character", type=str, default=None, help="Character key (e.g. spiderman, gojo, sukuna, ironman, thor, toji, wolverine, loki, megumi)")
    parser.add_argument("--universe", type=str, choices=["marvel", "jjk"], default="jjk", help="Universe filter (marvel or jjk)")
    parser.add_argument("--duration", type=float, default=38.0, help="Target video duration in seconds (default: 38.0)")
    parser.add_argument("--phonk", type=str, default=None, help="Phonk track name or ID from library")
    parser.add_argument("--subtitle-style", type=str, choices=["viral_karaoke", "cyber_glow", "anime_shrine", "cinematic_minimal"], default="viral_karaoke", help="Dynamic kinetic subtitle preset")
    parser.add_argument("--burn-subtitles", action="store_true", default=False, help="Burn kinetic subtitles onto the video (default: False for clean pure video)")
    parser.add_argument("--quote", type=str, default=None, help="Custom dialogue monologue quote")
    parser.add_argument("--title", type=str, default=None, help="Custom video title")
    parser.add_argument("--cc", type=str, default=None, help="4K HDR Color Grade Preset (marvel_hdr, jjk_void, sukuna_shrine, cyber_phonk)")
    parser.add_argument("--gdrive-folder", type=str, default=None, help="Google Drive folder URL or ID to pull movie/episode footage from")
    parser.add_argument("--github-repo", type=str, default=None, help="GitHub repository URL or slug to fetch video clips from")
    parser.add_argument("--audio", type=str, default=None, help="Path to custom audio file")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 path")
    parser.add_argument("--upload", action="store_true", help="Upload rendered video to YouTube Shorts (default: False, saves to Download folder)")
    parser.add_argument("--privacy", type=str, choices=["public", "unlisted", "private"], default="public", help="YouTube video privacy status")
    parser.add_argument("--refresh-clips", action="store_true", help="Download and slice a fresh scenepack for the character")
    parser.add_argument("--remotion-config", type=str, default="studio/remotion_editor/src/editor-state.json", help="Path to Remotion editor state JSON with visual layout & text overrides")
    parser.add_argument("--studio", action="store_true", help="Launch the AniDoc Studio Web Video Editing Software")
    parser.add_argument("--port", type=int, default=7860, help="Port for AniDoc Studio server (default: 7860)")
    
    args = parser.parse_args()
    
    # ── GDrive AMV mode — hybrid action/cinematic edit from Drive footage ──────
    if args.mode == "gdrive-amv":
        print("🎬 [AniDoc] Mode: GDRIVE AMV — Hybrid Action/Cinematic Edit from Drive")
        run_gdrive_amv(
            source_folder=args.amv_source_folder or _AMV_SRC,
            universe=args.universe,
            character=args.character,
            target_duration=args.duration if args.duration != 38.0 else 75.0,
            upload=args.upload,
            phonk_name=args.phonk,
        )
        return

    # If --studio is specified, launch web video editor
    if args.studio:
        start_studio_server(port=args.port)
        return

    # Handle Top 5 Ranking Countdown Mode
    if args.mode == "ranking" or args.ranking:
        print("🏆 [AniDoc] Mode: TOP 5 RANKING COUNTDOWN EDIT (Replicating viral countdown format)")
        output_name = args.output if args.output else f"{args.universe.upper()}_Best_Edits_Ranking_Countdown.mp4"
        title = args.title if args.title else f"Ranking Best {args.universe.upper()} edits"
        final_video = render_ranking_countdown_edit(
            universe=args.universe,
            title_text=title,
            output_filename=output_name,
            save_to_device_downloads=True
        )
        if args.upload:
            upload_video_to_youtube(
                video_path=final_video,
                title=f"Ranking The Best {args.universe.upper()} Edits 🔥 #anime #jjk #shorts",
                description="Top 5 Viral Anime Edits Ranked with Phonk Soundtrack and 60fps velocity.",
                tags=["jjk", "jujutsukaisen", "animeedit", "ranking", "phonk", "shorts"],
                privacy_status=args.privacy
            )
        return
        
    # Single Character 4K Edit Mode
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
        phonk_track=args.phonk,
        output_path=Path(args.output) if args.output else None,
        target_duration=args.duration,
        subtitle_style=args.subtitle_style,
        burn_subtitles=args.burn_subtitles,
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
    
    # Auto-save to device Download directory
    save_to_downloads(output_path, custom_name=f"{chosen_char}_4k_phonk_edit.mp4")

    # Upload to YouTube ONLY if explicitly requested
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
