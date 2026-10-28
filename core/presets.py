"""
Anime Shorts Editing Style Presets (Phase 10).
Defines distinct configuration archetypes:
- VIRAL_PHONK: Hyper-energy, bass drops, punch-ins, vibrant glow, loopable.
- CINEMATIC_ANIME: Elegant push/pulls, balanced pacing, richer contrast, clean cuts.
- DARK_ANIME: Cold shadow depth, tense pacing, high contrast, shrine aesthetic.
- HYPE_BATTLE: Hyper pacing, rapid combat clashes, high motion tracking.
- MINIMAL_CINEMATIC: Pure clean cuts, zero flashes, subtle typography, restrained.
"""
from typing import Dict, Any, Optional, List

EDITING_PRESETS: Dict[str, Dict[str, Any]] = {
    "VIRAL_PHONK": {
        "name": "VIRAL_PHONK",
        "description": "Explosive TikTok/Shorts viral phonk with dynamic punch-ins and 808 drop flash.",
        "pacing": "fast",
        "beat_sensitivity": 0.85,
        "crop_intensity": 1.0,
        "camera_movement": "punch_and_pan",
        "caption_preset": "spur_hook",
        "effect_intensity": 1.0,
        "sound_design": True,
        "climax_intensity": 1.0,
        "loop_behavior": True,
        "cc_preset": "vibrant_anime_glow",
        "enable_velocity_ramping": True
    },
    "CINEMATIC_ANIME": {
        "name": "CINEMATIC_ANIME",
        "description": "Film-like pacing with graceful push-ins/pull-outs, clean cuts, and deep blue grading.",
        "pacing": "balanced",
        "beat_sensitivity": 0.65,
        "crop_intensity": 0.85,
        "camera_movement": "push_pull",
        "caption_preset": "cinematic_minimal",
        "effect_intensity": 0.35,
        "sound_design": True,
        "climax_intensity": 0.80,
        "loop_behavior": False,
        "cc_preset": "jjk_void",
        "enable_velocity_ramping": True
    },
    "DARK_ANIME": {
        "name": "DARK_ANIME",
        "description": "Tense and ominous pacing with deep shadows, shrine red accents, and slow creeping zooms.",
        "pacing": "tense",
        "beat_sensitivity": 0.70,
        "crop_intensity": 0.90,
        "camera_movement": "slow_push",
        "caption_preset": "anime_shrine",
        "effect_intensity": 0.60,
        "sound_design": True,
        "climax_intensity": 0.90,
        "loop_behavior": True,
        "cc_preset": "sukuna_shrine",
        "enable_velocity_ramping": True
    },
    "HYPE_BATTLE": {
        "name": "HYPE_BATTLE",
        "description": "Maximum sakuga intensity with rapid micro-cuts, dynamic tracking, and neon cyber glow.",
        "pacing": "hyper",
        "beat_sensitivity": 0.95,
        "crop_intensity": 1.10,
        "camera_movement": "dynamic_tracking",
        "caption_preset": "viral_karaoke",
        "effect_intensity": 1.0,
        "sound_design": True,
        "climax_intensity": 1.0,
        "loop_behavior": True,
        "cc_preset": "cyber_phonk",
        "enable_velocity_ramping": True
    },
    "MINIMAL_CINEMATIC": {
        "name": "MINIMAL_CINEMATIC",
        "description": "Zero flashes, pure clean cuts, subtle typography, and natural anime color.",
        "pacing": "restrained",
        "beat_sensitivity": 0.50,
        "crop_intensity": 0.70,
        "camera_movement": "restrained",
        "caption_preset": "cinematic_minimal",
        "effect_intensity": 0.0,
        "sound_design": False,
        "climax_intensity": 0.60,
        "loop_behavior": False,
        "cc_preset": "cool_blue",
        "enable_velocity_ramping": False
    }
}


def get_editing_preset(preset_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves an editing preset configuration, defaulting to VIRAL_PHONK."""
    if not preset_name:
        return EDITING_PRESETS["VIRAL_PHONK"]
    clean_name = preset_name.strip().upper()
    return EDITING_PRESETS.get(clean_name, EDITING_PRESETS["VIRAL_PHONK"])


def list_available_presets() -> List[Dict[str, Any]]:
    """Returns a summary of all available editing presets."""
    return [
        {
            "id": k,
            "name": v["name"],
            "description": v["description"],
            "pacing": v["pacing"],
            "cc_preset": v["cc_preset"],
            "caption_preset": v["caption_preset"]
        }
        for k, v in EDITING_PRESETS.items()
    ]
