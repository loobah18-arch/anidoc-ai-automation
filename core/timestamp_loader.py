"""
Timestamp-aware clip loader for AniDoc.

Uses pre-generated episode timestamp metadata to select high-quality action clips
instead of random slicing.
"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

METADATA_DIR = Path(__file__).resolve().parent.parent / "metadata" / "episodes"


def load_episode_metadata(episode_code: str) -> Optional[Dict[str, Any]]:
    """Load timestamp metadata for a specific episode."""
    filename = f"{episode_code.lower()}_timestamps.json"
    filepath = METADATA_DIR / filename

    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load metadata for {episode_code}: {e}")
        return None


def get_character_clips(
    episode_code: str,
    character: str,
    min_action_score: float = 0.5,
    max_clips: int = 50
) -> List[Dict[str, Any]]:
    """
    Get high-quality clips for a specific character from episode metadata.

    Returns list of clips with:
    - start: timestamp in seconds
    - end: timestamp in seconds
    - action_level: EXPLOSIVE, INTENSE, MODERATE, CALM
    - priority: high, medium, low
    - characters_present: list of characters in scene
    """
    metadata = load_episode_metadata(episode_code)
    if not metadata:
        return []

    # Filter scenes where character is present and action score is high enough
    character_clips = []
    for scene in metadata.get("scenes", []):
        chars_present = scene.get("characters_present", [])
        action_score = scene.get("action_score", 0)

        # Check if character appears and meets action threshold
        if character.lower() in [c.lower() for c in chars_present]:
            if action_score >= min_action_score:
                character_clips.append(scene)

    # Sort by action score (highest first) and priority
    character_clips.sort(key=lambda x: (
        1 if x.get("priority") == "high" else (2 if x.get("priority") == "medium" else 3),
        -x.get("action_score", 0)
    ))

    return character_clips[:max_clips]


def find_best_episode_for_character(character: str) -> Optional[str]:
    """Find the best episode with timestamp metadata for a character."""
    # Check which episodes have metadata
    if not METADATA_DIR.exists():
        return None

    available_episodes = []
    for metadata_file in METADATA_DIR.glob("*_timestamps.json"):
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)

            # Check if character appears in this episode
            char_data = [c for c in data.get("characters", [])
                        if c.get("name", "").lower() == character.lower()]

            if char_data:
                # Count high-action scenes with this character
                high_action_scenes = sum(
                    1 for s in data.get("scenes", [])
                    if character.lower() in [c.lower() for c in s.get("characters_present", [])]
                    and s.get("action_score", 0) > 0.6
                )

                available_episodes.append({
                    "code": data["episode_code"],
                    "role": char_data[0].get("role", "Unknown"),
                    "high_action_count": high_action_scenes,
                    "total_scenes": len(data.get("scenes", []))
                })
        except Exception:
            continue

    if not available_episodes:
        return None

    # Return episode with most high-action character scenes
    best = max(available_episodes, key=lambda x: x["high_action_count"])
    return best["code"]


def list_available_episodes() -> List[str]:
    """List all episodes with timestamp metadata."""
    if not METADATA_DIR.exists():
        return []

    episodes = []
    for metadata_file in METADATA_DIR.glob("*_timestamps.json"):
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                episodes.append(data["episode_code"])
        except Exception:
            continue

    return sorted(episodes)


if __name__ == "__main__":
    # Test the loader
    print("📚 Available Episodes with Timestamp Metadata:")
    for ep in list_available_episodes():
        print(f"  {ep}")

    print("\n🔍 Testing Character Clip Lookup:")
    test_chars = ["yuji", "gojo", "todo"]
    for char in test_chars:
        best_ep = find_best_episode_for_character(char)
        if best_ep:
            clips = get_character_clips(best_ep, char, min_action_score=0.6)
            print(f"\n  {char.upper()}: {best_ep} - {len(clips)} high-action clips")
            if clips:
                print(f"    Top clip: {clips[0]['start']:.1f}s - {clips[0]['end']:.1f}s "
                      f"({clips[0]['action_level']}, score: {clips[0]['action_score']:.2f})")
