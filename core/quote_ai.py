"""
AI Quote, Dialogue & SEO Metadata Generator for Marvel & Jujutsu Kaisen Edits.
Powered by OpenCode DeepSeek v4 Flash with Nemotron, rich viral title catalogs, and non-repeating title rotation.
"""
import os
import re
import json
import random
import shutil
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

from config.settings import NVIDIA_API_KEY, OPENROUTER_API_KEY, CHANNEL_TAGS, SCRATCH_DIR
from core.clip_manager import CHARACTER_THEMES

TITLE_HISTORY_FILE = SCRATCH_DIR / "title_history.json"

CHARACTER_VIRAL_CONCEPTS: Dict[str, List[Dict[str, Any]]] = {
    "gojo": [
        {
            "quote": "Throughout heaven and earth, I alone am the honored one.",
            "title": "Gojo Awakened Mode Is Untouchable 🥶⚡ #gojo #jjk #4kedit #shorts",
            "tags": ["gojo", "satorugojo", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Are you the strongest because you're Satoru Gojo, or are you Satoru Gojo because you're the strongest?",
            "title": "Gojo Proves Why He's The Strongest Sorcerer 💜 #gojo #jjk #shorts",
            "tags": ["gojo", "satorugojo", "jjk", "jujutsukaisen", "hollowpurple", "4kedit", "shorts"]
        },
        {
            "quote": "Don't worry, I'm the strongest.",
            "title": "Gojo's 0.2s Domain Expansion Was Pure Cinema 🥶 #gojo #jujutsukaisen #shorts",
            "tags": ["gojo", "domainexpansion", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "It's taken a bit of work, but I've finally reached this state.",
            "title": "The Exact Moment Toji Realized He Lost 💀 #gojo #toji #jjk #shorts",
            "tags": ["gojo", "toji", "jjk", "jujutsukaisen", "honoredone", "4kedit", "shorts"]
        },
        {
            "quote": "Phase, Paramita, Pillar of Light... Nine Ropes... Hollow Purple.",
            "title": "Gojo Satoru's Hollow Purple Obliteration 💜💥 #jjk #gojo #shorts",
            "tags": ["gojo", "hollowpurple", "jjk", "jujutsukaisen", "anime", "4kedit", "shorts"]
        },
        {
            "quote": "Dying to win and risking death to win are completely different, Megumi.",
            "title": "Throughout Heaven And Earth, Satoru Gojo Is Him 👑 #gojo #jjk #shorts",
            "tags": ["gojo", "satorugojo", "jjk", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Looks like you're having trouble.",
            "title": "Gojo's Speed In Shibuya Was Terrifying ⚡ #gojo #shibuya #jjk #shorts",
            "tags": ["gojo", "shibuyaincident", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "My Six Eyes tell me you're Suguru Geto, but my soul knows otherwise!",
            "title": "When Gojo Removes The Blindfold It's Game Over 👁️ #gojo #jjk #shorts",
            "tags": ["gojo", "sixeyes", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "You're weak, Jogo. It's almost embarrassing.",
            "title": "Gojo vs Disaster Curses Martial Arts Masterclass 🥋 #gojo #jjk #shorts",
            "tags": ["gojo", "jogo", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
        {
            "quote": "Infinite Void. In here, you experience everything, yet you can do nothing.",
            "title": "Gojo Satoru Unlimited Void Pure Art 🌌 #gojo #jujutsukaisen #shorts",
            "tags": ["gojo", "unlimitedvoid", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
    ],
    "sukuna": [
        {
            "quote": "Stand proud. You are strong. But this is my domain.",
            "title": "Sukuna's Malevolent Shrine Hits Different 🩸 #sukuna #jjk #jujutsukaisen #4kedit #shorts",
            "tags": ["sukuna", "ryomensukuna", "jjk", "jujutsukaisen", "malevolentshrine", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "You dare look down on the King of Curses?",
            "title": "Sukuna vs Mahoraga Pure Destruction 💥 #sukuna #mahoraga #jjk #shorts",
            "tags": ["sukuna", "mahoraga", "jjk", "shibuya", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Open. Flame arrow, incinerate everything.",
            "title": "Sukuna's Fire Arrow Obliterates Shibuya 🔥 #sukuna #jjk #anime #shorts",
            "tags": ["sukuna", "firearrow", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Know your place, fool. A brat who knows nothing of true jujutsu.",
            "title": "The King Of Curses Does Not Spare Anyone 💀 #sukuna #jjk #shorts",
            "tags": ["sukuna", "ryomensukuna", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
        {
            "quote": "Let's see if you can entertain me for more than a second.",
            "title": "Sukuna Playing With Jogo Like A Toy 🥶 #sukuna #jogo #jjk #shorts",
            "tags": ["sukuna", "jogo", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
    ],
    "toji": [
        {
            "quote": "Don't get cocky just because you were born with cursed energy.",
            "title": "Toji Fushiguro The Sorcerer Killer 🗡️ #toji #jjk #jujutsukaisen #animeedit #4kedit #shorts",
            "tags": ["toji", "tojifushiguro", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "I rejected the Zen'in clan and walked my own path.",
            "title": "Zero Cursed Energy, Pure Demonic Power 💀 #toji #jjk #shorts",
            "tags": ["toji", "tojifushiguro", "zenin", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
        {
            "quote": "You're fast, kid. But not fast enough.",
            "title": "Toji Speed Blitzing Special Grade Sorcerers ⚡ #toji #jjk #shorts",
            "tags": ["toji", "dagon", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Not Fushiguro... Zen'in. Good for you.",
            "title": "Toji vs Dagon Domain Infiltration 🌊🗡️ #toji #dagon #jjk #shorts",
            "tags": ["toji", "megumi", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
    ],
    "yuji": [
        {
            "quote": "I don't care if it's impossible. I'm going to save everyone I can.",
            "title": "Yuji Itadori's Black Flash Impact 💥 #yuji #jjk #jujutsukaisen #blackflash #animeedit #4kedit #shorts",
            "tags": ["yuji", "yujiitadori", "jjk", "jujutsukaisen", "blackflash", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "I'm a cog. And my role is to destroy curses like you.",
            "title": "Yuji & Todo Double Black Flash Combo 🔥 #yuji #todo #mahito #jjk #shorts",
            "tags": ["yuji", "todo", "mahito", "jjk", "jujutsukaisen", "blackflash", "shorts"]
        },
        {
            "quote": "I'm you, Mahito. Wherever you run, I'll hunt you down.",
            "title": "I'm You — Yuji Hunting Mahito Like A Wolf 🐺 #yuji #mahito #jjk #shorts",
            "tags": ["yuji", "mahito", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Even if I die, I'll take you down with me!",
            "title": "Yuji vs Choso Bathroom Brawl Pure Cinema 🥋 #yuji #choso #jjk #shorts",
            "tags": ["yuji", "choso", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
    ],
    "megumi": [
        {
            "quote": "With this treasure, I summon... Eight-Handled Sword Divergent Sila Divine General Mahoraga.",
            "title": "Megumi's Mahoraga Summoning Shibuya 🔥 #megumi #mahoraga #jjk #4kedit #shorts",
            "tags": ["megumi", "mahoraga", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "I don't care about being right. I just want to save good people.",
            "title": "With This Treasure I Summon... 💀 #megumi #mahoraga #jjk #shorts",
            "tags": ["megumi", "mahoraga", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Chimera Shadow Garden! Expand your imagination!",
            "title": "Megumi Shadow Chimera Domain Expansion 🌑 #megumi #jjk #shorts",
            "tags": ["megumi", "domainexpansion", "jjk", "jujutsukaisen", "shorts"]
        },
    ],
    "spiderman": [
        {
            "quote": "With great power comes great responsibility.",
            "title": "Peter Parker Reclaims His Power 🕷️💥 #spiderman #marvel #4kedit #shorts",
            "tags": ["spiderman", "peterparker", "marvel", "mcu", "4kedit", "shorts"]
        },
        {
            "quote": "I can't save everyone... but I have to try.",
            "title": "Spider-Man In No Way Home Final Battle 🕸️ #spiderman #nowayhome #marvel #shorts",
            "tags": ["spiderman", "nowayhome", "marvel", "avengers", "4kedit", "shorts"]
        },
        {
            "quote": "I wanted to kill him. But that's not who we are.",
            "title": "When Spider-Man Stopped Holding Back 🥶🕷️ #spiderman #marvel #shorts",
            "tags": ["spiderman", "greengoblin", "marvel", "nowayhome", "shorts"]
        },
        {
            "quote": "Hello Peter. You're not Peter Parker!",
            "title": "Spider-Man vs Doc Ock Bridge Fight 4K 💥 #spiderman #marvel #shorts",
            "tags": ["spiderman", "docock", "marvel", "nowayhome", "4kedit", "shorts"]
        },
    ],
    "thor": [
        {
            "quote": "Bring me Thanos! You will die for that!",
            "title": "Thor's Entrance In Wakanda Was Peak MCU ⚡ #thor #marvel #4kedit #shorts",
            "tags": ["thor", "wakanda", "infinitywar", "marvel", "stormbreaker", "4kedit", "shorts"]
        },
        {
            "quote": "I am not the God of Hammers. I am the God of Thunder.",
            "title": "Thor God Of Thunder Awakened In Ragnarok ⚡🔥 #thor #ragnarok #marvel #shorts",
            "tags": ["thor", "ragnarok", "marvel", "mcu", "4kedit", "shorts"]
        },
        {
            "quote": "He's a friend from work!",
            "title": "Thor vs Hulk Gladiator Arena Battle 4K ⚡🔨 #thor #hulk #marvel #shorts",
            "tags": ["thor", "hulk", "ragnarok", "marvel", "shorts"]
        },
    ],
    "ironman": [
        {
            "quote": "And I... am... Iron Man.",
            "title": "The Greatest Sacrifice In MCU History 🦾 #ironman #marvel #4kedit #shorts",
            "tags": ["ironman", "tonystark", "marvel", "endgame", "avengers", "4kedit", "shorts"]
        },
        {
            "quote": "I am Iron Man. The suit and I are one.",
            "title": "Tony Stark Proves He's Earth's Best Defender 🦾🔥 #ironman #marvel #shorts",
            "tags": ["ironman", "tonystark", "marvel", "mcu", "4kedit", "shorts"]
        },
    ],
    "thanos": [
        {
            "quote": "You could not live with your own failure. Where did that bring you? Back to me.",
            "title": "Thanos Was Unstoppable In Infinity War 💥 #thanos #marvel #4kedit #shorts",
            "tags": ["thanos", "marvel", "infinitywar", "endgame", "villain", "4kedit", "shorts"]
        },
    ],
    "wolverine": [
        {
            "quote": "I'm the best there is at what I do, but what I do isn't very nice.",
            "title": "Wolverine Unleashed In Deadpool & Wolverine 🩸 #wolverine #marvel #4kedit #shorts",
            "tags": ["wolverine", "logan", "deadpool", "marvel", "xmen", "4kedit", "shorts"]
        },
    ],
    "loki": [
        {
            "quote": "I know what kind of god I need to be. For all of us.",
            "title": "Loki God Of Stories Sacrifice Was Unmatched 👑 #loki #marvel #4kedit #shorts",
            "tags": ["loki", "godofstories", "marvel", "mcu", "tva", "4kedit", "shorts"]
        },
    ]
}


def _load_title_history() -> List[str]:
    """Loads previously used titles from persistent history."""
    if TITLE_HISTORY_FILE.exists():
        try:
            with open(TITLE_HISTORY_FILE, "r") as f:
                return json.load(f).get("used_titles", [])
        except Exception:
            pass
    return []


def _save_title_history(used: List[str]):
    """Saves used titles to persistent history."""
    try:
        TITLE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TITLE_HISTORY_FILE, "w") as f:
            json.dump({"used_titles": used[-100:]}, f, indent=2)
    except Exception as e:
        print(f"⚠️ [QuoteAI] Failed to save title history: {e}")


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
    Priority 1: Queries OpenCode DeepSeek v4 Flash via OpenCode CLI.
    """
    opencode_bin = shutil.which("opencode") or str(Path.home() / ".opencode/bin/opencode")
    if not opencode_bin or not (Path(opencode_bin).exists() or shutil.which("opencode")):
        return None
        
    prompt = (
        f"You are a master viral YouTube Shorts creator making a 4K Phonk scene edit for {character_name} ({universe.upper()}). "
        "Generate a JSON object with: "
        "1. 'quote': An iconic, punchy, badass 1-sentence quote or monologue line (under 12 words), "
        "2. 'title': Unique High-CTR YouTube Shorts title with emoji and hashtags (under 65 chars), "
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
            "2. 'title': unique viral YouTube Short title with hashtags (under 70 chars), "
            "3. 'tags': array of 8 viral hashtags."
        )
        payload = {
            "model": "nvidia/nemotron-3-super-550b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85,
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
    Generates quote, title, description, and tags with non-repeating title rotation.
    IMPORTANT: Always ensures the title matches the selected character.
    """
    if not character_key or character_key not in CHARACTER_THEMES:
        character_key = random.choice(list(CHARACTER_THEMES.keys()))

    theme = CHARACTER_THEMES[character_key]

    # 1. Try OpenCode DeepSeek v4 Flash (Priority 1)
    ai_meta = query_opencode_deepseek_v4_flash(theme["name"], theme["universe"])

    # 2. Try NVIDIA Nemotron (Priority 2)
    if not ai_meta:
        ai_meta = query_nvidia_nemotron(theme["name"], theme["universe"])

    used_titles = _load_title_history()

    if ai_meta and ai_meta.get("title") and ai_meta.get("title") not in used_titles:
        chosen_concept = ai_meta
    else:
        # 3. Non-repeating rotation from curated rich viral concept catalog
        # CRITICAL FIX: Only use titles from the selected character's catalog
        catalog = CHARACTER_VIRAL_CONCEPTS.get(character_key)

        # Fallback: If character has no catalog, use character theme quote
        if not catalog:
            print(f"⚠️  [QuoteAI] No catalog for {character_key}, using character theme quote")
            chosen_concept = {
                "quote": theme["quote"],
                "title": f"{theme['name']} Epic Moment 🔥 #{character_key} #{theme['universe']} #4kedit #shorts",
                "tags": [character_key, theme['universe'], "animeedit", "4kedit", "shorts"]
            }
        else:
            unused_concepts = [c for c in catalog if c["title"] not in used_titles]

            if not unused_concepts:
                print(f"🔄 [QuoteAI] All catalog titles rotated through for {character_key}. Resetting title history.")
                unused_concepts = catalog
                used_titles = [t for t in used_titles if t not in [c["title"] for c in catalog]]

            chosen_concept = random.choice(unused_concepts)
        
    quote = chosen_concept["quote"]
    title = chosen_concept["title"]
    tags = chosen_concept.get("tags", [character_key, "animeedit", "4kedit", "shorts"])
    
    # Save to history
    used_titles.append(title)
    _save_title_history(used_titles)
    print(f"🎯 [QuoteAI] Selected fresh viral title: '{title}'")
    
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
