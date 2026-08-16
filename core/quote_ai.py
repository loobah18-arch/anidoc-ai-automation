"""
AI Quote, Dialogue & SEO Metadata Generator for Marvel & Jujutsu Kaisen Edits.
Powered by NVIDIA Nemotron / DeepSeek v4 with rich procedural fallback.
"""
import os
import json
import random
import requests
from typing import Dict, Any
from config.settings import NVIDIA_API_KEY, OPENROUTER_API_KEY, CHANNEL_TAGS
from core.clip_manager import CHARACTER_THEMES

FALLBACK_CONCEPTS = {
    "spiderman": {
        "quote": "I'm a machine. You think I'm afraid of you?",
        "title": "Spiderman In Infinity War ⚡ #marvel #spiderman #4kedit #shorts",
        "tags": ["spiderman", "infinitywar", "marvel", "peterparker", "avengers", "4kedit", "phonk", "shorts"]
    },
    "ironman": {
        "quote": "And I... am... Iron Man.",
        "title": "The Greatest Sacrifice In MCU History 🦾 #ironman #marvel #4kedit #shorts",
        "tags": ["ironman", "tonystark", "marvel", "endgame", "avengers", "4kedit", "shorts"]
    },
    "thor": {
        "quote": "Bring me Thanos! You will die for that!",
        "title": "Thor's Entrance In Wakanda Was Peak MCU ⚡ #thor #marvel #4kedit #shorts",
        "tags": ["thor", "wakanda", "infinitywar", "marvel", "stormbreaker", "4kedit", "shorts"]
    },
    "thanos": {
        "quote": "You could not live with your own failure. Where did that bring you? Back to me.",
        "title": "Thanos Was Unstoppable In Infinity War 💥 #thanos #marvel #4kedit #shorts",
        "tags": ["thanos", "marvel", "infinitywar", "endgame", "villain", "4kedit", "shorts"]
    },
    "gojo": {
        "quote": "Throughout heaven and earth, I alone am the honored one.",
        "title": "Gojo Satoru's Hollow Purple Is Pure Art 💜 #gojo #jjk #jujutsukaisen #4kedit #shorts",
        "tags": ["gojo", "satorugojo", "jjk", "jujutsukaisen", "hollowpurple", "animeedit", "4kedit", "shorts"]
    },
    "sukuna": {
        "quote": "Stand proud. You are strong. But this is my domain.",
        "title": "Sukuna's Malevolent Shrine Hits Different 🩸 #sukuna #jjk #jujutsukaisen #4kedit #shorts",
        "tags": ["sukuna", "ryomensukuna", "jjk", "jujutsukaisen", "malevolentshrine", "animeedit", "4kedit", "shorts"]
    },
    "toji": {
        "quote": "Don't get cocky just because you were born with cursed energy.",
        "title": "Toji Fushiguro The Sorcerer Killer 🗡️ #toji #jjk #jujutsukaisen #4kedit #shorts",
        "tags": ["toji", "tojifushiguro", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
    },
    "yuji": {
        "quote": "I don't care if it's impossible. I'm going to save everyone I can.",
        "title": "Yuji Itadori's Black Flash Impact 💥 #yuji #jjk #jujutsukaisen #4kedit #shorts",
        "tags": ["yuji", "yujiitadori", "jjk", "jujutsukaisen", "blackflash", "animeedit", "4kedit", "shorts"]
    }
}


def generate_edit_metadata(character_key: str = None) -> Dict[str, Any]:
    """
    Generates quote, title, description, and tags for a character edit.
    """
    if not character_key or character_key not in CHARACTER_THEMES:
        character_key = random.choice(list(CHARACTER_THEMES.keys()))
        
    theme = CHARACTER_THEMES[character_key]
    fallback = FALLBACK_CONCEPTS.get(character_key, FALLBACK_CONCEPTS["gojo"])
    
    # Try NVIDIA API if configured
    if NVIDIA_API_KEY:
        try:
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json"
            }
            prompt = (
                f"You are an elite YouTube Shorts editor creating viral 4K Phonk edits for {theme['name']} ({theme['universe'].upper()}). "
                "Generate a JSON object with: "
                "1. 'quote': a legendary 1-sentence badass quote (under 12 words), "
                "2. 'title': viral YouTube Short title with hashtags (under 70 chars), "
                "3. 'tags': array of 8 viral hashtags."
            )
            payload = {
                "model": "nvidia/nemotron-3-super-550b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 200
            }
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["choices"][0]["message"]["content"]
                # Parse JSON
                start_i = raw_text.find("{")
                end_i = raw_text.rfind("}")
                if start_i != -1 and end_i != -1:
                    parsed = json.loads(raw_text[start_i:end_i+1])
                    return {
                        "character_key": character_key,
                        "character_name": theme["name"],
                        "universe": theme["universe"],
                        "quote": parsed.get("quote", fallback["quote"]),
                        "title": parsed.get("title", fallback["title"]),
                        "tags": parsed.get("tags", fallback["tags"]),
                        "description": (
                            f"{parsed.get('title', fallback['title'])}\n\n"
                            f"\"{parsed.get('quote', fallback['quote'])}\"\n\n"
                            "Disclaimer: This video is a transformative fan edit created for entertainment purposes. "
                            "All rights belong to their respective copyright owners.\n\n"
                            + " ".join(f"#{t}" for t in parsed.get("tags", fallback["tags"]))
                        )
                    }
        except Exception as e:
            print(f"[QuoteAI] Notice querying AI: {e}. Using curated master quote.")
            
    # Return curated concept
    return {
        "character_key": character_key,
        "character_name": theme["name"],
        "universe": theme["universe"],
        "quote": fallback["quote"],
        "title": fallback["title"],
        "tags": fallback["tags"],
        "description": (
            f"{fallback['title']}\n\n"
            f"\"{fallback['quote']}\"\n\n"
            "Disclaimer: This video is a transformative fan edit created for entertainment purposes. "
            "All rights belong to their respective copyright owners.\n\n"
            + " ".join(f"#{t}" for t in fallback["tags"])
        )
    }
