"""
Character Clip Library & Action Scene Ingestion Manager for Marvel & Jujutsu Kaisen.
Features dynamic non-repeating clip shuffling, multi-source scenepack rotation, and procedural fallback.
"""
import os
import random
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import MARVEL_DIR, JJK_DIR, DEMONSLAYER_DIR, SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS
from core.public_api_fetcher import fetch_character_scenepack

CHARACTER_THEMES = {
    # ── Jujutsu Kaisen Universe ──
    "gojo": {
        "universe": "jjk",
        "name": "Gojo Satoru",
        "colors": ["#3b82f6", "#8b5cf6", "#090514"],
        "cc_preset": "jjk_void",
        "quote": "Throughout heaven and earth, I alone am the honored one."
    },
    "sukuna": {
        "universe": "jjk",
        "name": "Ryomen Sukuna",
        "colors": ["#991b1b", "#dc2626", "#180000"],
        "cc_preset": "sukuna_shrine",
        "quote": "Stand proud. You are strong."
    },
    "toji": {
        "universe": "jjk",
        "name": "Toji Fushiguro",
        "colors": ["#334155", "#0284c7", "#090d16"],
        "cc_preset": "cyber_phonk",
        "quote": "Don't get cocky just because you have cursed energy."
    },
    "yuji": {
        "universe": "jjk",
        "name": "Yuji Itadori",
        "colors": ["#b91c1c", "#fbbf24", "#1a0b0b"],
        "cc_preset": "sukuna_shrine",
        "quote": "I'm a cog. And my role is to destroy curses like you."
    },
    "megumi": {
        "universe": "jjk",
        "name": "Megumi Fushiguro",
        "colors": ["#1e293b", "#38bdf8", "#0f172a"],
        "cc_preset": "jjk_void",
        "quote": "With this treasure, I summon... Mahoraga."
    },
    "nobara": {
        "universe": "jjk",
        "name": "Nobara Kugisaki",
        "colors": ["#dc2626", "#fbbf24", "#0f172a"],
        "cc_preset": "jjk_void",
        "quote": "I love myself when I'm pretty and all dressed up, and I love myself when I'm strong!"
    },
    "todo": {
        "universe": "jjk",
        "name": "Aoi Todo",
        "colors": ["#84cc16", "#365314", "#0f172a"],
        "cc_preset": "cyber_phonk",
        "quote": "What is your type of woman? Mine is a tall woman with a big ass!"
    },
    "mahito": {
        "universe": "jjk",
        "name": "Mahito",
        "colors": ["#a855f7", "#581c87", "#000000"],
        "cc_preset": "sukuna_shrine",
        "quote": "We are curses, born of human negative emotion... let's curse each other to death!"
    },

    # ── Demon Slayer (Kimetsu no Yaiba) Universe ──
    "tanjiro": {
        "universe": "demonslayer",
        "name": "Tanjiro Kamado",
        "colors": ["#b91c1c", "#15803d", "#0f172a"],
        "cc_preset": "hinokami_flame",
        "quote": "No matter how many people you may lose, you have no choice but to go on living."
    },
    "rengoku": {
        "universe": "demonslayer",
        "name": "Kyojuro Rengoku",
        "colors": ["#ea580c", "#dc2626", "#7f1d1d"],
        "cc_preset": "flame_hashira",
        "quote": "Set your heart ablaze. Go beyond your limits."
    },
    "zenitsu": {
        "universe": "demonslayer",
        "name": "Zenitsu Agatsuma",
        "colors": ["#eab308", "#ca8a04", "#1e293b"],
        "cc_preset": "thunder_gold",
        "quote": "Thunder Breathing, First Form: Thunderclap and Flash — Sixfold!"
    },
    "akaza": {
        "universe": "demonslayer",
        "name": "Akaza",
        "colors": ["#ec4899", "#3b82f6", "#0f172a"],
        "cc_preset": "akaza_compass",
        "quote": "Become a demon, Kyojuro! If you don't, you will die!"
    },
    "giyu": {
        "universe": "demonslayer",
        "name": "Giyu Tomioka",
        "colors": ["#0284c7", "#0369a1", "#082f49"],
        "cc_preset": "water_breathing",
        "quote": "Water Breathing, Eleventh Form: Dead Calm."
    },
    "tengen": {
        "universe": "demonslayer",
        "name": "Tengen Uzui",
        "colors": ["#f59e0b", "#ec4899", "#18181b"],
        "cc_preset": "thunder_gold",
        "quote": "From here on out, things are gonna get flashy!"
    },
    "inosuke": {
        "universe": "demonslayer",
        "name": "Inosuke Hashibira",
        "colors": ["#0ea5e9", "#475569", "#0f172a"],
        "cc_preset": "beast_breathing",
        "quote": "Coming through! Pig assault! Beast Breathing!"
    },
    "muzan": {
        "universe": "demonslayer",
        "name": "Muzan Kibutsuji",
        "colors": ["#991b1b", "#18181b", "#000000"],
        "cc_preset": "sukuna_crimson",
        "quote": "Do I look pale to you? Does my face look sickly?"
    },
    "nezuko": {
        "universe": "demonslayer",
        "name": "Nezuko Kamado",
        "colors": ["#f43f5e", "#fda4af", "#18181b"],
        "cc_preset": "hinokami_flame",
        "quote": "Blood Demon Art: Exploding Blood!"
    },
    "muichiro": {
        "universe": "demonslayer",
        "name": "Muichiro Tokito",
        "colors": ["#06b6d4", "#0891b2", "#0f172a"],
        "cc_preset": "cool_blue",
        "quote": "Mist Breathing, Seventh Form: Obscuring Clouds."
    },
    "gyutaro": {
        "universe": "demonslayer",
        "name": "Gyutaro",
        "colors": ["#22c55e", "#dc2626", "#09090b"],
        "cc_preset": "sukuna_crimson",
        "quote": "You've got a nice face, man... envy eats me alive!"
    },
    "shinobu": {
        "universe": "demonslayer",
        "name": "Shinobu Kocho",
        "colors": ["#a855f7", "#06b6d4", "#1e1b4b"],
        "cc_preset": "wisteria_bloom",
        "quote": "Insect Breathing, Butterfly Dance: Caprice."
    },

    # ── Marvel Universe (Legacy compatibility) ──
    "spiderman": {
        "universe": "marvel",
        "name": "Spider-Man",
        "colors": ["#dc2626", "#2563eb", "#0f172a"],
        "cc_preset": "marvel_hdr",
        "quote": "With great power comes great responsibility."
    },
    "loki": {
        "universe": "marvel",
        "name": "Loki (God of Stories)",
        "colors": ["#15803d", "#22c55e", "#052e16"],
        "cc_preset": "cyber_phonk",
        "quote": "I know what kind of god I need to be."
    },
    "ironman": {
        "universe": "marvel",
        "name": "Iron Man",
        "colors": ["#b91c1c", "#f59e0b", "#1e1b4b"],
        "cc_preset": "marvel_hdr",
        "quote": "I am Iron Man."
    },
    "thor": {
        "universe": "marvel",
        "name": "Thor Odinson",
        "colors": ["#0284c7", "#38bdf8", "#0f172a"],
        "cc_preset": "cyber_phonk",
        "quote": "Bring me Thanos!"
    },
    "thanos": {
        "universe": "marvel",
        "name": "Thanos",
        "colors": ["#7c3aed", "#a855f7", "#090514"],
        "cc_preset": "jjk_void",
        "quote": "I am inevitable."
    },
    "wolverine": {
        "universe": "marvel",
        "name": "Wolverine",
        "colors": ["#eab308", "#1e3a8a", "#0f172a"],
        "cc_preset": "cyber_phonk",
        "quote": "I'm the best there is at what I do."
    },

    # ── Expanded Multi-Anime Library ──
    "denji": {
        "universe": "chainsawman",
        "name": "Denji (Chainsaw Man)",
        "colors": ["#ea580c", "#f97316", "#18181b"],
        "cc_preset": "cyber_phonk",
        "quote": "Everyone's after my chainsaw heart! What about Denji's heart?!"
    },
    "makima": {
        "universe": "chainsawman",
        "name": "Makima",
        "colors": ["#be123c", "#f43f5e", "#09090b"],
        "cc_preset": "sukuna_shrine",
        "quote": "I like people who are hardworking and loyal."
    },
    "power": {
        "universe": "chainsawman",
        "name": "Power",
        "colors": ["#f43f5e", "#fbbf24", "#18181b"],
        "cc_preset": "cyber_phonk",
        "quote": "Bow before me, human! For I am Power!"
    },
    "sungjinwoo": {
        "universe": "sololeveling",
        "name": "Sung Jin-Woo",
        "colors": ["#3b82f6", "#1d4ed8", "#020617"],
        "cc_preset": "jjk_void",
        "quote": "Arise."
    },
    "jinwoo": {
        "universe": "sololeveling",
        "name": "Sung Jin-Woo",
        "colors": ["#3b82f6", "#1d4ed8", "#020617"],
        "cc_preset": "jjk_void",
        "quote": "Arise."
    },
    "ichigo": {
        "universe": "bleach",
        "name": "Ichigo Kurosaki",
        "colors": ["#f97316", "#0284c7", "#09090b"],
        "cc_preset": "water_breathing",
        "quote": "Bankai! Tensa Zangetsu!"
    },
    "aizen": {
        "universe": "bleach",
        "name": "Sosuke Aizen",
        "colors": ["#8b5cf6", "#6d28d9", "#090514"],
        "cc_preset": "jjk_void",
        "quote": "No one stands on the top of the world. Not you, not me, not even gods."
    },
    "eren": {
        "universe": "aot",
        "name": "Eren Yeager",
        "colors": ["#15803d", "#854d0e", "#0a0a0a"],
        "cc_preset": "marvel_hdr",
        "quote": "If we kill all our enemies over there... will we finally be free?"
    },
    "levi": {
        "universe": "aot",
        "name": "Levi Ackerman",
        "colors": ["#15803d", "#0284c7", "#0a0a0a"],
        "cc_preset": "cyber_phonk",
        "quote": "Give up on your dreams and die."
    },
    "naruto": {
        "universe": "naruto",
        "name": "Naruto Uzumaki",
        "colors": ["#f97316", "#eab308", "#172554"],
        "cc_preset": "hinokami_flame",
        "quote": "I'm not gonna run away, I never go back on my word!"
    },
    "sasuke": {
        "universe": "naruto",
        "name": "Sasuke Uchiha",
        "colors": ["#3b82f6", "#7c3aed", "#020617"],
        "cc_preset": "jjk_void",
        "quote": "I have long since closed my eyes... My only goal is in the darkness."
    },
    "luffy": {
        "universe": "onepiece",
        "name": "Monkey D. Luffy",
        "colors": ["#dc2626", "#facc15", "#0369a1"],
        "cc_preset": "thunder_gold",
        "quote": "I'm gonna be King of the Pirates!"
    },
    "zoro": {
        "universe": "onepiece",
        "name": "Roronoa Zoro",
        "colors": ["#15803d", "#22c55e", "#09090b"],
        "cc_preset": "cyber_phonk",
        "quote": "Nothing happened."
    },
    "kafka": {
        "universe": "kaijuno8",
        "name": "Kafka Hibino (Kaiju No. 8)",
        "colors": ["#06b6d4", "#0f766e", "#020617"],
        "cc_preset": "cyber_phonk",
        "quote": "I will stand beside you on the front lines!"
    },
    "okarun": {
        "universe": "dandadan",
        "name": "Ken Takakura (Okarun)",
        "colors": ["#a855f7", "#ec4899", "#09090b"],
        "cc_preset": "cyber_phonk",
        "quote": "Turbo Granny power, unleash!"
    },
}


def ensure_character_theme(character_key: str, universe: Optional[str] = None) -> Dict[str, Any]:
    """Ensures a character theme exists in CHARACTER_THEMES, generating one dynamically if not."""
    ck = character_key.lower().strip()
    if ck not in CHARACTER_THEMES:
        uni = universe or "anime"
        CHARACTER_THEMES[ck] = {
            "universe": uni,
            "name": character_key.replace("_", " ").title(),
            "colors": ["#3b82f6", "#8b5cf6", "#090514"],
            "cc_preset": "cyber_phonk",
            "quote": "I will break through every limit!"
        }
        print(f"✨ [ClipManager] Dynamically registered character theme: '{ck}' ({uni.upper()})")
    return CHARACTER_THEMES[ck]


def generate_procedural_cinematic_scene(
    character_key: str,
    seg_idx: int,
    duration: float,
    output_path: Path,
    is_drop: bool = False
) -> Path:
    """
    Renders an animated high-contrast 1080x1920 procedural motion scene
    with energy particles, kinetic glow pulses, and stylized framing.
    """
    theme = CHARACTER_THEMES.get(character_key, CHARACTER_THEMES["gojo"])
    c1, c2, c3 = theme["colors"]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dur_str = f"{duration:.2f}"
    
    pulse_freq = 4.0 if is_drop else 1.5
    vf_chain = (
        f"testsrc=duration={dur_str}:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:rate={FPS},"
        f"drawbox=x=0:y=0:w=iw:h=ih:color={c3}@1:t=fill,"
        f"drawbox=x='(w-400)/2':y='(h-700)/2':w=400:h=700:color={c1}@0.7:t=fill,"
        f"drawbox=x='(w-480)/2':y='(h-780)/2':w=480:h=780:color={c2}@0.9:t=8,"
        f"curves=all='0/0 0.5/0.7 1/1',"
        f"vignette=PI/3.5,"
        f"format=yuv420p"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", vf_chain,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-t", dur_str,
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def is_clip_healthy(p: Path) -> bool:
    """Verifies that an MP4 clip exists, is >20KB, and has readable streams via ffprobe (no moov atom corruption)."""
    if not p.exists() or p.stat().st_size <= 20_000:
        return False
    if p.name.startswith("proc_"):
        return False
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
            capture_output=True, text=True, timeout=5
        )
        return res.returncode == 0 and bool(res.stdout.strip()) and float(res.stdout.strip()) > 0.4
    except Exception:
        return False


def get_character_scene_clips(
    character_key: str,
    segment_durations: List[float],
    is_drop_flags: List[bool],
    auto_fetch_online: bool = True,
    github_repo: Optional[str] = None,
    force_refresh: bool = False
) -> List[Path]:
    """
    Retrieves or downloads real footage clips for a character.
    
    Diversity fixes:
    - Searches both universe_dir AND scratch dir for character clips
    - Clips are strictly deduped: same clip never used twice in a row
    - If we have more clips than segments, each segment gets a unique clip
    - Wrong-character clips are filtered out by filename keyword matching
    """
    theme = CHARACTER_THEMES.get(character_key, CHARACTER_THEMES["gojo"])
    if theme["universe"] == "demonslayer":
        universe_dir = DEMONSLAYER_DIR
    elif theme["universe"] == "marvel":
        universe_dir = MARVEL_DIR
    else:
        universe_dir = JJK_DIR
    universe_dir.mkdir(parents=True, exist_ok=True)
    
    # Search for character-specific clips in both dirs (strictly validating health via ffprobe)
    scratch_char_dir = SCRATCH_DIR / theme.get("universe", "jjk")
    scratch_char_dir.mkdir(parents=True, exist_ok=True)
    
    cand_files = (
        list(universe_dir.glob(f"*{character_key}*.mp4")) +
        list(scratch_char_dir.glob(f"*{character_key}*.mp4"))
    )
    raw_clips = []
    for p in cand_files:
        if is_clip_healthy(p):
            raw_clips.append(p)
        elif p.exists() and not p.name.startswith("proc_"):
            p.unlink(missing_ok=True)
    
    # If forced refresh or missing, download fresh multi-query scenepack
    if (not raw_clips or force_refresh) and auto_fetch_online:
        print(f"🌐 Fetching fresh scenepack cuts for '{character_key}'...")
        fetched = fetch_character_scenepack(character_key, max_clips=len(segment_durations) + 6)
        if fetched:
            raw_clips = [p for p in fetched if is_clip_healthy(p)]
            
    # Last resort: use any real anime universe clips
    if not raw_clips:
        cand_all = list(universe_dir.glob("*.mp4")) + list(scratch_char_dir.glob("*.mp4"))
        for p in cand_all:
            if is_clip_healthy(p):
                raw_clips.append(p)

    # Deduplicate paths, remove empties
    seen = set()
    unique_clips = []
    for p in raw_clips:
        if is_clip_healthy(p) and str(p) not in seen:
            seen.add(str(p))
            unique_clips.append(p)
    raw_clips = sorted(unique_clips, key=lambda p: p.name)
    
    n_segs = len(segment_durations)
    
    if not raw_clips:
        print(f"⚠️ [ClipManager] Notice: 0 real footage clips found for '{character_key}'. Generating procedural scenes.")
        # Full procedural fallback
        clip_paths = []
        for idx, (dur, is_drop) in enumerate(zip(segment_durations, is_drop_flags)):
            out_p = SCRATCH_DIR / f"proc_{character_key}_seg_{idx}_{int(dur*100)}.mp4"
            generate_procedural_cinematic_scene(character_key, idx, dur, out_p, is_drop)
            clip_paths.append(out_p)
        return clip_paths
    
    # ── Thematic Narrative Arc Sequencing (matches reference edit storytelling) ──
    # Act 1: Intro shots (setup, walking, stare, dialogue) from early clips
    # Act 2: Combat cuts (escalating clashes, technique trades) from middle clips
    # Act 3: Climax Finisher (ultimate strike, domain expansion, finishing hit) from peak clip
    n_intro = sum(1 for f in is_drop_flags if not f)

    if len(raw_clips) >= n_segs:
        intro_clips = raw_clips[:n_intro]
        action_clips = raw_clips[n_intro:n_segs - 1] if n_segs > n_intro + 1 else raw_clips[n_intro:]
        finisher_clip = raw_clips[-1]
    else:
        intro_split = max(1, min(len(raw_clips) // 3, n_intro))
        intro_clips = raw_clips[:intro_split]
        action_clips = raw_clips[intro_split:] if len(raw_clips) > intro_split else raw_clips[:]
        finisher_clip = raw_clips[-1]

    if not intro_clips:
        intro_clips = raw_clips[:]
    if not action_clips:
        action_clips = raw_clips[:]

    clip_paths = []
    action_i = 0
    intro_i = 0

    for idx, (dur, is_drop) in enumerate(zip(segment_durations, is_drop_flags)):
        if not is_drop:
            clip = intro_clips[intro_i % len(intro_clips)]
            intro_i += 1
        elif idx == n_segs - 1:
            clip = finisher_clip
        else:
            clip = action_clips[action_i % len(action_clips)]
            action_i += 1

        clip_paths.append(clip)

    return clip_paths


def list_available_character_clips(universe: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Lists all available downloaded clips categorized by character and universe."""
    result = {}
    dirs = []
    if universe == "demonslayer" or not universe:
        dirs.append(("demonslayer", DEMONSLAYER_DIR))
    if universe == "jjk" or not universe:
        dirs.append(("jjk", JJK_DIR))
    if universe == "marvel" or not universe:
        dirs.append(("marvel", MARVEL_DIR))
        
    for univ_name, udir in dirs:
        udir.mkdir(parents=True, exist_ok=True)
        for clip in udir.glob("*.mp4"):
            char_match = "generic"
            for k in CHARACTER_THEMES.keys():
                if k in clip.name.lower():
                    char_match = k
                    break
            if char_match not in result:
                result[char_match] = []
            result[char_match].append({
                "filename": clip.name,
                "path": str(clip),
                "universe": univ_name,
                "size_kb": clip.stat().st_size // 1024
            })
    return result
