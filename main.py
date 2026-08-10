#!/usr/bin/env python3
"""
Main Autonomous Runner for AniDoc AI 2D Documentary Creation & YouTube Upload
Supports:
  1. Full Hands-Free Daily Automation:
     python main.py --auto-upload
  2. Custom Topic Creation & Upload:
     python main.py --topic "The 1971 PAF Prison Escape" --language Hindi --upload
  3. Dry-Run / Local Media Generation:
     python main.py --topic "Operation Sindoor" --render
"""

import sys
import os
import argparse
import re
from pathlib import Path

# Ensure root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.pipeline import AniDocPipeline
from core.topic_manager import TopicManager
from publishers.youtube_publisher import YouTubePublisher

def extract_titles_and_desc(seo_text: str, default_topic: str):
    """Parses titles, description, hashtags, and tags from State 6 output."""
    titles = []
    description = ""
    tags = []

    # Title extraction
    title_matches = re.findall(r'Option \d+.*?:?\s*(.+)', seo_text)
    if title_matches:
        for t in title_matches:
            clean_t = t.strip().strip('"\'')
            if len(clean_t) > 5:
                titles.append(clean_t)
    
    if not titles:
        titles = [f"{default_topic} | 2D Documentary #anidoc #shorts"]

    # Description extraction
    if "YOUTUBE DESCRIPTION:" in seo_text:
        desc_part = seo_text.split("YOUTUBE DESCRIPTION:")[1]
        if "VIRAL HASHTAGS" in desc_part:
            description = desc_part.split("VIRAL HASHTAGS")[0].strip()
        else:
            description = desc_part[:800].strip()
    else:
        description = f"An investigative 2D documentary on {default_topic}. Like and subscribe for more untold historical realities."

    # Tags extraction
    if "YOUTUBE SEARCH TAGS" in seo_text or "TAGS" in seo_text:
        tag_part = seo_text.split("TAGS")[-1].replace(":", "").strip()
        tags = [t.strip() for t in tag_part.split(",") if len(t.strip()) > 1][:30]

    if not tags:
        tags = ["2d documentary", "true crime hindi", "animation documentary", "chad grow", "anidoc", "history", "raw espionage"]

    return titles[0], description, tags

def run_pipeline(topic: str, language: str = "Hindi", upload: bool = False, privacy_status: str = "public", max_images: int = 6):
    print("=" * 70)
    print(" 🎬 ANIDOC AI: AUTONOMOUS DOCUMENTARY CREATION & YOUTUBE PIPELINE")
    print("=" * 70)
    print(f"[*] Target Topic:   '{topic}'")
    print(f"[*] Language:       {language}")
    print(f"[*] Auto Upload:    {upload} ({privacy_status})")
    print("-" * 70)

    pipeline = AniDocPipeline(language=language)

    # 1. State 2: Scriptwriting
    print("\n--> [STATE 2] Writing Deep Voiceover Script...")
    script_output = pipeline.run_state2_script(topic)

    # 2. State 3: Batch 2D Image Prompts
    print("\n--> [STATE 3] Generating 2D Illustration Prompts (16:9)...")
    pipeline.run_state3_image_prompts()

    # 3. State 4: Motion Prompts
    print("\n--> [STATE 4] Generating Camera Motion Prompts...")
    pipeline.run_state4_motion_prompts()

    # 4. State 5: Thumbnails
    print("\n--> [STATE 5] Generating High-CTR Thumbnail Concepts...")
    pipeline.run_state5_thumbnails()

    # 5. State 6: YouTube SEO Package
    print("\n--> [STATE 6] Generating YouTube SEO Package...")
    seo_output = pipeline.run_state6_seo()

    # 6. Render Full Media (Audio + Images + Motion Clips + Subtitles + 1080p Video)
    print("\n--> [MEDIA ENGINE] Synthesizing Voiceover & Assembling 1080p Video...")
    media_res = pipeline.render_complete_media(max_images=max_images)

    video_path = media_res["video"]
    thumbnail_path = media_res["thumbnail"]

    # Parse metadata for YouTube
    best_title, description, tags = extract_titles_and_desc(seo_output, topic)

    # 7. Upload to YouTube (if requested or in auto-upload mode)
    if upload:
        print("\n--> [PUBLISHER] Uploading Finished Video & Thumbnail to YouTube...")
        publisher = YouTubePublisher()
        upload_res = publisher.upload_video(
            video_path=video_path,
            title=best_title,
            description=description,
            tags=tags,
            thumbnail_path=thumbnail_path,
            privacy_status=privacy_status,
            topic_name=topic
        )
        print("\n[✔] Upload Status:", upload_res.get("status"))
        if upload_res.get("url"):
            print(f"    Watch on YouTube: {upload_res.get('url')}")
    else:
        print("\n[ℹ] Media generated locally (upload skipped). To upload automatically, pass --upload or --auto-upload.")

    print("\n" + "=" * 70)
    print(f" [✔] SUCCESS! Project Assets saved in: {pipeline.project_dir}")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="AniDoc AI Autonomous Video Creation & YouTube Upload Engine")
    parser.add_argument("--topic", type=str, default=None, help="Documentary Topic (if omitted, automatically selected from catalog/rotation)")
    parser.add_argument("--language", type=str, default="Hindi", help="Script language (Hindi / English)")
    parser.add_argument("--upload", action="store_true", help="Upload rendered video directly to YouTube")
    parser.add_argument("--auto-upload", action="store_true", help="Hands-free mode: auto-selects fresh topic from catalog and uploads to YouTube")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"], help="YouTube privacy status")
    parser.add_argument("--render", action="store_true", help="Render video without uploading")
    parser.add_argument("--max-images", type=int, default=5, help="Number of 2D images to render for video")

    args = parser.parse_args()

    topic_mgr = TopicManager()

    if args.auto_upload:
        # Automated hands-free daily mode
        topic_info = topic_mgr.get_next_topic(custom_topic=args.topic, language=args.language)
        run_pipeline(
            topic=topic_info["topic"],
            language=topic_info.get("language", args.language),
            upload=True,
            privacy_status=args.privacy,
            max_images=args.max_images
        )
    elif args.topic:
        run_pipeline(
            topic=args.topic,
            language=args.language,
            upload=args.upload,
            privacy_status=args.privacy,
            max_images=args.max_images
        )
    else:
        # Default topic selection
        topic_info = topic_mgr.get_next_topic(language=args.language)
        run_pipeline(
            topic=topic_info["topic"],
            language=args.language,
            upload=args.upload,
            privacy_status=args.privacy,
            max_images=args.max_images
        )

if __name__ == "__main__":
    main()
