#!/usr/bin/env python3
"""
Interactive CLI for AniDoc AI Automation Engine
Run states 1-6 interactively or trigger full autonomous video creation and automatic YouTube upload.
"""

import sys
import os
from pathlib import Path

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from core.pipeline import AniDocPipeline
from publishers.youtube_publisher import YouTubePublisher
from main import extract_titles_and_desc

def print_banner():
    print("""
========================================================================
   ___          _  ___             ___  ___   ___       _             
  / _ \\        (_)/ _ \\           / _ \\|_  | |   \\     | |            
 / /_\\ \\_ __  _ _| | | |___  ___ / /_\\ \\ | | | |) |___ | |__          
 |  _  | '_ \\| | | | | / __|/ _ \\|  _  | | | |  _// _ \\| '_ \\         
 | | | | | | | | | |_| \\__ \\  __/| | | | | |_| | | (_) | |_) |        
 \\_| |_/_| |_|_|_|\\___/|___/\\___|\\_| |_/\\___/|_|  \\___/|_.__/         
                                                                       
        2D Documentary AI Channel Autonomous Pipeline Engine          
              Based on Chad Grow's AniDoc Blueprint                   
========================================================================
""")

def main_menu():
    print_banner()
    print("Select an operation mode:")
    print("  [1] 🚀 Complete 1-Click Autonomous Production & Auto YouTube Upload")
    print("  [2] State 1: Generate 10 Viral Topics")
    print("  [3] State 2: Generate Script from Custom Topic")
    print("  [4] State 3: Generate 2D Illustration Image Prompts")
    print("  [5] State 4: Generate Video Motion Prompts")
    print("  [6] State 5: Generate 5 High-CTR Thumbnail Concepts")
    print("  [7] State 6: Generate YouTube SEO Package")
    print("  [8] 🎬 Render 1080p Video & Subtitles locally")
    print("  [9] 🌐 Launch Web Studio Dashboard (http://localhost:8080)")
    print("  [0] Exit")
    print("------------------------------------------------------------------------")

def run():
    while True:
        main_menu()
        choice = input("Enter your choice (0-9): ").strip()
        
        if choice == "0":
            print("\nExiting AniDoc AI Automation. Happy creating!\n")
            break
            
        elif choice == "1":
            print("\n--- Autonomous Video Creation & Automatic YouTube Upload ---")
            lang = input("Language (Hindi / English) [Default: Hindi]: ").strip() or "Hindi"
            topic_input = input("Enter topic (or press Enter to auto-generate from catalog): ").strip()
            
            pipeline = AniDocPipeline(language=lang)
            if not topic_input:
                from core.topic_manager import TopicManager
                mgr = TopicManager()
                t_info = mgr.get_next_topic(language=lang)
                topic_input = t_info["topic"]
                    
            print(f"\n[+] Producing Documentary on: '{topic_input}' [{lang}]\n")
            pipeline.run_state2_script(topic_input)
            pipeline.run_state3_image_prompts()
            pipeline.run_state4_motion_prompts()
            pipeline.run_state5_thumbnails()
            seo_output = pipeline.run_state6_seo()
            
            print("\nRendering 1080p Video, Voiceover & 2D Animated Thumbnail...")
            media_res = pipeline.render_complete_media(max_images=5)

            upload_q = input("\nUpload automatically to YouTube now? (y/n) [Default: y]: ").strip().lower()
            if upload_q != "n":
                privacy = input("Privacy status (public / unlisted / private) [Default: public]: ").strip() or "public"
                best_title, description, tags = extract_titles_and_desc(seo_output, topic_input)
                publisher = YouTubePublisher()
                publisher.upload_video(
                    video_path=media_res["video"],
                    title=best_title,
                    description=description,
                    tags=tags,
                    thumbnail_path=media_res["thumbnail"],
                    privacy_status=privacy,
                    topic_name=topic_input
                )
                
            input("\n[SUCCESS] Pipeline finished! Press Enter to return to main menu...")

        elif choice == "2":
            lang = input("Language (Hindi / English) [Default: Hindi]: ").strip() or "Hindi"
            pipeline = AniDocPipeline(language=lang)
            topics = pipeline.run_state1_topics()
            print("\n" + topics)
            input("\nPress Enter to return to menu...")

        elif choice == "3":
            topic = input("Enter topic: ").strip()
            if not topic: topic = "The Rise and Fall of Mumbai Underworld"
            lang = input("Language (Hindi / English) [Default: Hindi]: ").strip() or "Hindi"
            pipeline = AniDocPipeline(language=lang)
            script = pipeline.run_state2_script(topic)
            print("\n" + script)
            input("\nPress Enter to return to menu...")

        elif choice == "4":
            topic = input("Enter topic: ").strip() or "Covert RAW Mission"
            pipeline = AniDocPipeline()
            pipeline.run_state2_script(topic)
            prompts = pipeline.run_state3_image_prompts()
            print("\n" + prompts)
            input("\nPress Enter to return to menu...")

        elif choice == "5":
            topic = input("Enter topic: ").strip() or "Covert RAW Mission"
            pipeline = AniDocPipeline()
            pipeline.run_state2_script(topic)
            pipeline.run_state3_image_prompts()
            motion = pipeline.run_state4_motion_prompts()
            print("\n" + motion)
            input("\nPress Enter to return to menu...")

        elif choice == "6":
            topic = input("Enter topic: ").strip() or "Covert RAW Mission"
            pipeline = AniDocPipeline()
            pipeline.run_state2_script(topic)
            thumbs = pipeline.run_state5_thumbnails()
            print("\n" + thumbs)
            input("\nPress Enter to return to menu...")

        elif choice == "7":
            topic = input("Enter topic: ").strip() or "Covert RAW Mission"
            pipeline = AniDocPipeline()
            pipeline.run_state2_script(topic)
            seo = pipeline.run_state6_seo()
            print("\n" + seo)
            input("\nPress Enter to return to menu...")

        elif choice == "8":
            project_name = input("Enter project folder name in output/ (or press Enter for new): ").strip()
            pipeline = AniDocPipeline(project_name=project_name)
            pipeline.render_complete_media(max_images=4)
            input("\nPress Enter to return to menu...")

        elif choice == "9":
            print("\nLaunching AniDoc Web Dashboard at http://localhost:8080 ...")
            os.system(f"python3 {settings.BASE_DIR}/server.py")

        else:
            print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    run()
