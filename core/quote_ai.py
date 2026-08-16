"""
AI Quote, Dialogue & SEO Metadata Generator for Marvel & Jujutsu Kaisen Edits.
Powered by OpenCode DeepSeek v4 Flash (Priority 1) with Nemotron & procedural fallbacks.
"""
import os
import re
import json
import random
import shutil
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import NVIDIA_API_KEY, OPENROUTER_API_KEY, CHANNEL_TAGS
from core.clip_manager import CHARACTER_THEMES

FALLBACK_CONCEPTS = {
    "spiderman": {
        "quote": "Mr. Stark, it smells like a new car in here!",
        "title": "Spiderman in infinity war #marvel #spiderman #peterlovers #avengers #4kedit #ironman #shorts #thor",
        "tags": ["spiderman", "infinitywar", "marvel", "peterlovers", "avengers", "4kedit", "ironman", "shorts", "thor"]
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
    "wolverine": {
        "quote": "I'm the best there is at what I do, but what I do isn't very nice.",
        "title": "Wolverine Unleashed In Deadpool & Wolverine 🩸 #wolverine #marvel #4kedit #shorts",
        "tags": ["wolverine", "logan", "deadpool", "marvel", "xmen", "4kedit", "shorts"]
    },
    "loki": {
        "quote": "I know what kind of god I need to be. For all of us.",
        "title": "Loki God Of Stories Sacrifice Was Unmatched 👑 #loki #marvel #4kedit #shorts",
        "tags": ["loki", "godofstories", "marvel", "mcu", "tva", "4kedit", "shorts"]
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
    },
    "megumi": {
        "quote": "With this treasure, I summon... Eight-Handled Sword Divergent Sila Divine General Mahoraga.",
        "title": "Megumi's Mahoraga Summoning Shibuya 🔥 #megumi #mahoraga #jjk #4kedit #shorts",
        "tags": ["megumi", "mahoraga", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
    }
}


def _extract_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Safely extracts JSON dictionary from LLM response text."""
    if not raw_text:
        return None
    clean = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(clean)
    except Exception:
        match = re.search(r'\{[\s\S]*\}', clean)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None


def query_opencode_deepseek_v4_flash(character_name: str, universe: str) -> Optional[Dict[str, Any]]:
    """
    Priority 1: Queries OpenCode DeepSeek v4 Flash (opencode/deepseek-v4-flash-free) via OpenCode CLI.
    """
    opencode_bin = shutil.which("opencode") or str(Path.home() / ".opencode/bin/opencode")
    if not opencode_bin or not (Path(opencode_bin).exists() or shutil.which("opencode")):
        return None
        
    prompt = (
        f"You are a master viral YouTube Shorts creator making a 4K Phonk scene edit for {character_name} ({universe.upper()}). "
        "Generate a JSON object with: "
        "1. 'quote': An iconic, punchy, badass 1-sentence quote or monologue line (under 12 words), "
        "2. 'title': High-CTR YouTube Shorts title with emoji and hashtags (under 65 chars), "
        "3. 'tags': List of 8 viral trending hashtags without hash symbols. "
        "Output ONLY raw JSON with keys 'quote', 'title', 'tags'."
    )
    
    try:
        print(f"🧠 [QuoteAI] Querying OpenCode DeepSeek v4 Flash (opencode/deepseek-v4-flash-free)...")
        res = subprocess.run(
            [opencode_bin, "run", "-m", "opencode/deepseek-v4-flash-free", prompt],
            capture_output=True,
            text=True,
            timeout=15
        )
        if res.returncode == 0 and res.stdout:
            parsed = _extract_json_response(res.stdout)
            if parsed and "quote" in parsed and "title" in parsed:
                print(f"✅ [QuoteAI] DeepSeek v4 Flash successfully generated quote: \"{parsed['quote']}\"")
                return parsed
    except Exception as e:
        print(f"[QuoteAI] Notice querying OpenCode CLI: {e}")
        
    return None


def query_nvidia_nemotron(character_name: str, universe: str) -> Optional[Dict[str, Any]]:
    """
    Priority 2: Queries NVIDIA Nemotron 3 Ultra if API key is present.
    """
    if not NVIDIA_API_KEY:
        return None
        
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"You are an elite YouTube Shorts editor creating viral 4K Phonk edits for {character_name} ({universe.upper()}). "
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
            parsed = _extract_json_response(raw_text)
            if parsed and "quote" in parsed:
                return parsed
    except Exception as e:
        print(f"[QuoteAI] Notice querying NVIDIA NIM: {e}")
        
    return None


def generate_edit_metadata(character_key: str = None) -> Dict[str, Any]:
    """
    Generates quote, title, description, and tags for a character edit using DeepSeek v4 Flash hierarchy.
    """
    if not character_key or character_key not in CHARACTER_THEMES:
        character_key = random.choice(list(CHARACTER_THEMES.keys()))
        
    theme = CHARACTER_THEMES[character_key]
    fallback = FALLBACK_CONCEPTS.get(character_key, FALLBACK_CONCEPTS["gojo"])
    
    # 1. Try OpenCode DeepSeek v4 Flash (Priority 1)
    ai_meta = query_opencode_deepseek_v4_flash(theme["name"], theme["universe"])
    
    # 2. Try NVIDIA Nemotron (Priority 2)
    if not ai_meta:
        ai_meta = query_nvidia_nemotron(theme["name"], theme["universe"])
        
    quote = (ai_meta.get("quote") if ai_meta else None) or fallback["quote"]
    title = (ai_meta.get("title") if ai_meta else None) or fallback["title"]
    tags = (ai_meta.get("tags") if ai_meta else None) or fallback["tags"]
    
    return {
        "character_key": character_key,
        "character_name": theme["name"],
        "universe": theme["universe"],
        "quote": quote,
        "title": title,
        "tags": tags,
        "description": (
            f"{title}\n\n"
            f"\"{quote}\"\n\n"
            "Disclaimer: This video is a transformative fan edit created for entertainment purposes. "
            "All rights belong to their respective copyright owners.\n\n"
            + " ".join(f"#{t.lstrip('#')}" for t in tags)
        )
    }
