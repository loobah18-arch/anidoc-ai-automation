#!/usr/bin/env python3
"""
Main Headless / Scriptable Runner for AniDoc AI Automation Pipeline
Example:
  python main.py --topic "The 1971 PAF Prison Escape" --language Hindi --render
"""

import sys
import argparse
from pathlib import Path

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.pipeline import AniDocPipeline

def main():
    parser = argparse.ArgumentParser(description="AniDoc AI 2D Documentary Channel Automation")
    parser.add_argument("--topic", type=str, default=None, help="Documentary Topic (if omitted, generates 10 topics)")
    parser.add_argument("--language", type=str, default="Hindi", help="Target script language (Hindi / English)")
    parser.add_argument("--project", type=str, default=None, help="Custom project output folder name")
    parser.add_argument("--provider", type=str, default=None, help="LLM Provider (openrouter, nvidia, anthropic, openai, free)")
    parser.add_argument("--state", type=int, default=None, help="Run specific state only (1 to 6)")
    parser.add_argument("--render", action="store_true", help="Automatically generate voiceover, images, and render final 1080p video")
    parser.add_argument("--max-images", type=int, default=5, help="Number of 2D images to render for the video")

    args = parser.parse_args()

    pipeline = AniDocPipeline(
        project_name=args.project,
        language=args.language,
        llm_provider=args.provider
    )

    if args.state == 1 or (not args.topic and args.state is None and not args.render):
        topics = pipeline.run_state1_topics()
        print(topics)
        return

    topic = args.topic or "Operation Sindoor: The Untold 1971 RAW Espionage Mission"
    print(f"[*] Executing pipeline for: '{topic}' [{args.language}]")

    if args.state == 2:
        res = pipeline.run_state2_script(topic)
        print(res)
    elif args.state == 3:
        pipeline.run_state2_script(topic)
        res = pipeline.run_state3_image_prompts()
        print(res)
    elif args.state == 4:
        pipeline.run_state2_script(topic)
        pipeline.run_state3_image_prompts()
        res = pipeline.run_state4_motion_prompts()
        print(res)
    elif args.state == 5:
        pipeline.run_state2_script(topic)
        res = pipeline.run_state5_thumbnails()
        print(res)
    elif args.state == 6:
        pipeline.run_state2_script(topic)
        res = pipeline.run_state6_seo()
        print(res)
    else:
        # Full pipeline run
        print("\n--> Running State 2: Cinematic Scriptwriting...")
        pipeline.run_state2_script(topic)

        print("\n--> Running State 3: Batch 2D Image Prompts...")
        pipeline.run_state3_image_prompts()

        print("\n--> Running State 4: Video Motion Prompts...")
        pipeline.run_state4_motion_prompts()

        print("\n--> Running State 5: Thumbnail Concepts...")
        pipeline.run_state5_thumbnails()

        print("\n--> Running State 6: YouTube SEO Package...")
        pipeline.run_state6_seo()

        if args.render:
            print("\n--> Rendering Full Media Package (Voiceover, Images, 1080p Video)...")
            res = pipeline.render_complete_media(max_images=args.max_images)
            print("\n[✔] Final Outputs:")
            for k, v in res.items():
                print(f"  {k.upper()}: {v}")

        print(f"\n[✔] Project saved in: {pipeline.project_dir}")

if __name__ == "__main__":
    main()
