"""
Title-driven scene selector for timestamp-aware clip fetching.

Analyzes YouTube title to determine what scenes to select from episode metadata.
"""
import re
from typing import List, Dict, Optional, Any

from core.timestamp_loader import load_episode_metadata, get_character_clips


# Title keyword mappings to scene types
TITLE_KEYWORDS = {
    # ── Jujutsu Kaisen ────────────────────────────────────────────────────────
    "black flash": {
        "keywords": ["black flash", "blackflash", "divergent fist"],
        "action_keywords": ["black flash", "consecutive", "zone", "barrage", "spark"],
        "min_action_score": 0.85,
        "preferred_episodes": ["S02E21", "S01E24", "S01E20", "S01E13"],
    },
    "domain expansion": {
        "keywords": ["domain expansion", "domain", "infinite void", "malevolent shrine", "chimera shadow"],
        "action_keywords": ["domain", "expansion", "void", "shrine", "coffin", "shadow garden", "horizon"],
        "min_action_score": 0.9,
        "preferred_episodes": ["S02E09", "S02E17", "S02E14", "S01E09", "S02E16"],
    },
    "mahoraga": {
        "keywords": ["mahoraga", "eight-handled", "summon", "shikigami"],
        "action_keywords": ["summon", "mahoraga", "treasure", "adapt", "wheel"],
        "min_action_score": 0.85,
        "preferred_episodes": ["S02E17", "S02E16", "S01E15"],
    },
    "sukuna": {
        "keywords": ["sukuna", "king of curses", "cleave", "dismantle", "fuga", "open"],
        "action_keywords": ["sukuna", "cleave", "dismantle", "fire", "arrow", "mahoraga", "shrine"],
        "min_action_score": 0.8,
        "preferred_episodes": ["S02E17", "S02E16", "S01E04"],
    },
    "gojo": {
        "keywords": ["gojo", "satoru", "six eyes", "limitless", "hollow purple", "purple", "honored one"],
        "action_keywords": ["gojo", "void", "hollow", "purple", "red", "blue", "awakened"],
        "min_action_score": 0.8,
        "preferred_episodes": ["S02E04", "S02E09", "S01E09", "S01E07"],
    },
    "yuji": {
        "keywords": ["yuji", "itadori", "i am you", "divergent fist"],
        "action_keywords": ["yuji", "itadori", "black flash", "choso", "mahito", "combo"],
        "min_action_score": 0.8,
        "preferred_episodes": ["S02E21", "S02E13", "S01E24", "S01E20"],
    },
    "todo": {
        "keywords": ["todo", "aoi", "boogie woogie", "best friend", "brother"],
        "action_keywords": ["todo", "boogie", "swap", "clap", "takada"],
        "min_action_score": 0.75,
        "preferred_episodes": ["S02E21", "S01E20", "S01E13"],
    },
    "toji": {
        "keywords": ["toji", "fushiguro", "heavenly restriction", "sorcerer killer"],
        "action_keywords": ["toji", "dagon", "awakening", "playful cloud", "inverted spear"],
        "min_action_score": 0.8,
        "preferred_episodes": ["S02E04", "S02E14", "S01E04"],
    },
    "mahito": {
        "keywords": ["mahito", "idle transfiguration", "instant spirit body", "curse"],
        "action_keywords": ["mahito", "transfiguration", "soul", "polymorphic", "distorted"],
        "min_action_score": 0.75,
        "preferred_episodes": ["S02E21", "S02E19", "S01E20", "S02E13"],
    },
    "nobara": {
        "keywords": ["nobara", "kugisaki", "resonance", "hairpin", "straw doll"],
        "action_keywords": ["nobara", "resonance", "hairpin", "nail", "mahito", "eso"],
        "min_action_score": 0.8,
        "preferred_episodes": ["S02E19", "S01E24"],
    },
    "choso": {
        "keywords": ["choso", "blood manipulation", "piercing blood", "supernova"],
        "action_keywords": ["choso", "blood", "piercing", "supernova", "bathroom"],
        "min_action_score": 0.8,
        "preferred_episodes": ["S02E13", "S01E24"],
    },

    # ── Demon Slayer (Kimetsu no Yaiba) ───────────────────────────────────────
    "hinokami kagura": {
        "keywords": ["hinokami", "kagura", "sun breathing", "dance of the fire god", "enbu"],
        "action_keywords": ["hinokami", "kagura", "sun", "flame", "dance", "fire god", "rui", "decapitation"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S01E19", "DS_S02E10"],
    },
    "thunder breathing": {
        "keywords": ["thunderclap", "thunder breathing", "godspeed", "sixfold", "zenitsu", "thunder"],
        "action_keywords": ["thunder", "thunderclap", "sixfold", "godspeed", "lightning", "flash", "dismember"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S01E17", "DS_S02E10"],
    },
    "flame breathing": {
        "keywords": ["flame breathing", "rengoku", "ninth form", "esoterica", "set your heart ablaze"],
        "action_keywords": ["flame", "ninth", "annihilation", "rengoku", "akaza", "blaze", "tiger"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S02E06", "DS_S02E07"],
    },
    "akaza destructive death": {
        "keywords": ["akaza", "compass needle", "destructive death", "upper three", "annihilation"],
        "action_keywords": ["akaza", "compass", "destructive", "annihilation", "air type", "disorder"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S02E06", "DS_S02E07"],
    },
    "musical score": {
        "keywords": ["musical score", "sound breathing", "tengen", "uzui", "flashy", "score technique"],
        "action_keywords": ["musical score", "score", "uzui", "tengen", "gyutaro", "sound", "cleaver", "decapitation"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S02E08", "DS_S02E09", "DS_S02E10"],
    },
    "gyutaro blood art": {
        "keywords": ["gyutaro", "blood sickles", "rotating circular slashes", "upper six"],
        "action_keywords": ["gyutaro", "sickle", "slashes", "blood", "poison", "daki"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S02E08", "DS_S02E09", "DS_S02E10"],
    },
    "dead calm": {
        "keywords": ["dead calm", "lull", "water breathing", "eleventh form", "giyu", "tomioka"],
        "action_keywords": ["dead calm", "lull", "eleventh", "water", "rui", "giyu", "calm"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S01E20"],
    },
    "obscuring clouds": {
        "keywords": ["obscuring clouds", "mist breathing", "seventh form", "muichiro", "tokito"],
        "action_keywords": ["obscuring", "clouds", "mist", "seventh", "gyokko", "tokito"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S03E08", "DS_S03E09"],
    },
    "demon slayer mark": {
        "keywords": ["demon slayer mark", "slayer mark", "awakened mark", "mark"],
        "action_keywords": ["mark", "awakening", "tanjiro", "muichiro", "decapitation"],
        "min_action_score": 0.85,
        "preferred_episodes": ["DS_S02E10", "DS_S03E08", "DS_S03E09"],
    },

    # ── General Clashes ───────────────────────────────────────────────────────
    "fight": {
        "keywords": ["vs", "fight", "battle", "combat", "clash"],
        "action_keywords": ["fight", "battle", "vs", "combat", "clash", "punch", "kick"],
        "min_action_score": 0.7,
        "preferred_episodes": None,  # Any episode
    },
}


def parse_title_intent(title: str) -> Dict[str, Any]:
    """
    Parse YouTube title to determine scene selection intent.

    Returns:
        {
            "scene_type": "black flash" | "domain expansion" | etc,
            "characters": ["yuji", "todo"],
            "min_action_score": 0.85,
            "preferred_episodes": ["S01E20"],
            "keywords": ["black flash", "consecutive"]
        }
    """
    title_lower = title.lower()

    # Detect scene type
    scene_type = "fight"  # default
    for scene_name, scene_data in TITLE_KEYWORDS.items():
        for keyword in scene_data["keywords"]:
            if keyword in title_lower:
                scene_type = scene_name
                break
        if scene_type != "fight":
            break

    # Extract characters mentioned
    characters = []
    char_names = {
        # JJK
        "yuji": ["yuji", "itadori"],
        "gojo": ["gojo", "satoru"],
        "sukuna": ["sukuna", "ryomen"],
        "megumi": ["megumi", "fushiguro"],
        "todo": ["todo", "aoi"],
        "nobara": ["nobara", "kugisaki"],
        "toji": ["toji"],
        "mahito": ["mahito"],
        "choso": ["choso"],
        # Demon Slayer
        "tanjiro": ["tanjiro", "kamado"],
        "rengoku": ["rengoku", "kyojuro"],
        "zenitsu": ["zenitsu", "agatsuma"],
        "akaza": ["akaza", "hakuji"],
        "giyu": ["giyu", "tomioka"],
        "tengen": ["tengen", "uzui"],
        "gyutaro": ["gyutaro"],
        "inosuke": ["inosuke", "hashibira"],
        "muzan": ["muzan", "kibutsuji"],
        "nezuko": ["nezuko"],
        "muichiro": ["muichiro", "tokito"],
    }

    for char_key, aliases in char_names.items():
        for alias in aliases:
            if alias in title_lower:
                characters.append(char_key)
                break

    # Get scene config
    scene_config = TITLE_KEYWORDS.get(scene_type, TITLE_KEYWORDS["fight"])

    return {
        "scene_type": scene_type,
        "characters": list(set(characters)),  # dedupe
        "min_action_score": scene_config["min_action_score"],
        "preferred_episodes": scene_config["preferred_episodes"],
        "action_keywords": scene_config["action_keywords"],
    }


def get_title_driven_clips(
    title: str,
    character: str,
    max_clips: int = 50
) -> List[Dict[str, Any]]:
    """
    Get clips based on YouTube title intent.

    Args:
        title: YouTube video title (e.g., "Yuji's 4 Consecutive Black Flashes")
        character: Main character for the video
        max_clips: Maximum number of clips to return

    Returns:
        List of scene dicts with timestamps, descriptions, action levels
    """
    intent = parse_title_intent(title)

    print(f"\n🎯 [TitleDriven] Scene type: {intent['scene_type']}")
    print(f"   Characters: {', '.join(intent['characters']) if intent['characters'] else character}")
    print(f"   Min action score: {intent['min_action_score']}")

    # Try preferred episodes first
    preferred_eps = intent["preferred_episodes"] or []
    all_clips = []

    for ep_code in preferred_eps:
        metadata = load_episode_metadata(ep_code)
        if not metadata:
            continue

        # Filter scenes matching title intent
        for scene in metadata.get("scenes", []):
            desc = scene.get("description", "").lower()
            chars_present = [c.lower() for c in scene.get("characters_present", [])]

            # Check if character is present
            if character.lower() not in chars_present:
                continue

            # Check action score
            if scene.get("action_score", 0) < intent["min_action_score"]:
                continue

            # Check if scene matches title keywords
            keyword_match = any(kw in desc for kw in intent["action_keywords"])
            if keyword_match or intent["scene_type"] == "fight":
                all_clips.append({
                    **scene,
                    "episode": ep_code,
                    "relevance_score": scene.get("action_score", 0) + (0.1 if keyword_match else 0)
                })

    # Sort by relevance
    all_clips.sort(key=lambda x: -x.get("relevance_score", 0))

    # Fall back to character clips if not enough
    if len(all_clips) < max_clips // 2:
        print(f"   ⚠️ Only {len(all_clips)} title-matched clips, adding character clips...")
        from core.timestamp_loader import find_best_episode_for_character
        best_ep = find_best_episode_for_character(character)
        if best_ep:
            char_clips = get_character_clips(best_ep, character, intent["min_action_score"], max_clips)
            all_clips.extend([{**c, "episode": best_ep} for c in char_clips if c not in all_clips])

    result = all_clips[:max_clips]
    print(f"   ✅ Selected {len(result)} clips matching title intent")

    return result


if __name__ == "__main__":
    # Test title-driven selection
    test_titles = [
        "Yuji's 4 Consecutive Black Flashes vs Mahito 🔥 #yuji #blackflash #jjk",
        "Gojo's Domain Expansion: Infinite Void 💀 #gojo #domain #jjk",
        "Sukuna vs Jogo - Malevolent Shrine 🔥 #sukuna #jogo #shibuya",
        "Todo & Yuji Best Friend Combo 💪 #todo #yuji #jjk",
    ]

    for title in test_titles:
        print(f"\n{'='*70}")
        print(f"Title: {title}")
        intent = parse_title_intent(title)
        print(f"Intent: {intent}")

        if intent["characters"]:
            char = intent["characters"][0]
            clips = get_title_driven_clips(title, char, max_clips=5)
            print(f"\nTop 3 clips:")
            for i, clip in enumerate(clips[:3], 1):
                print(f"  {i}. [{clip['episode']}] {clip['start']:.1f}s-{clip['end']:.1f}s: {clip.get('description', 'N/A')}")
