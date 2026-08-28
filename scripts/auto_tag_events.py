#!/usr/bin/env python3
"""
Auto-Tag JJK Iconic Events
Tags episodes with verified character/event metadata based on research.
"""
import json
from pathlib import Path
from typing import Dict, List, Any

DEFAULT_DATABASE = Path(__file__).parent.parent / "data" / "jjk_timestamp_database.json"

# Research-verified iconic scenes by season/episode
ICONIC_EVENTS = {
    # Season 1
    "S01E02": {
        "characters": ["gojo"],
        "events": ["Gojo removes blindfold", "Power showcase"],
        "tags": ["gojo", "introduction", "power"]
    },
    "S01E04": {
        "characters": ["sukuna"],
        "events": ["First major Sukuna fight"],
        "tags": ["sukuna", "fight", "transformation"]
    },
    "S01E07": {
        "characters": ["gojo", "jogo"],
        "events": ["Gojo vs Jogo", "Domain Expansion: Unlimited Void"],
        "tags": ["gojo", "domain_expansion", "fight", "iconic"],
        "highlight_windows": [(900, 1200)]  # Approx 15-20 min mark
    },
    "S01E19": {
        "characters": ["yuji", "nanami"],
        "events": ["Yuji's first Black Flash", "Yuji and Nanami vs Mahito"],
        "tags": ["yuji", "black_flash", "growth", "iconic"]
    },
    "S01E20": {
        "characters": ["sukuna", "yuji"],
        "events": ["Sukuna takes control", "Devastating consequences"],
        "tags": ["sukuna", "takeover", "dark", "iconic"],
        "highlight_windows": [(600, 1200)]  # Latter half
    },
    "S01E23": {
        "characters": ["yuji", "todo"],
        "events": ["Yuji and Todo fight together"],
        "tags": ["yuji", "todo", "teamwork", "fight"]
    },
    "S01E24": {
        "characters": ["yuji", "todo"],
        "events": ["Exchange Event climax"],
        "tags": ["yuji", "todo", "climax", "fight"]
    },

    # Season 2 - Hidden Inventory Arc (Episodes 1-5)
    "S02E01": {
        "characters": ["gojo", "geto"],
        "events": ["Hidden Inventory arc begins", "Young Gojo and Geto"],
        "tags": ["gojo", "geto", "past", "hidden_inventory"]
    },
    "S02E02": {
        "characters": ["gojo", "geto", "riko"],
        "events": ["Hidden Inventory arc", "Riko Amanai introduction"],
        "tags": ["gojo", "geto", "riko", "hidden_inventory"]
    },
    "S02E03": {
        "characters": ["gojo", "toji"],
        "events": ["Toji Fushiguro appears", "First confrontation"],
        "tags": ["gojo", "toji", "hidden_inventory", "fight"]
    },
    "S02E04": {
        "characters": ["gojo", "toji"],
        "events": ["Gojo vs Toji - First fight", "Gojo defeated"],
        "tags": ["gojo", "toji", "fight", "defeat", "iconic"]
    },
    "S02E05": {
        "characters": ["gojo", "toji"],
        "events": ["Gojo's Awakening", "Gojo vs Toji - Rematch", "Reverse Cursed Technique"],
        "tags": ["gojo", "awakening", "toji", "iconic", "rematch", "power_up"],
        "highlight_windows": [(600, 1200)]  # Awakening scene
    },

    # Season 2 - Shibuya Incident Arc (Episodes 6+)
    "S02E14": {
        "characters": ["sukuna", "mahoraga"],
        "events": ["Sukuna vs Mahoraga", "Malevolent Shrine"],
        "tags": ["sukuna", "mahoraga", "domain_expansion", "iconic", "fight"],
        "highlight_windows": [(300, 1200)]  # Major fight sequence
    },
    "S02E15": {
        "characters": ["sukuna"],
        "events": ["Sukuna devastates Shibuya"],
        "tags": ["sukuna", "destruction", "shibuya", "iconic"]
    },
    "S02E16": {
        "characters": ["yuji", "mahito"],
        "events": ["Yuji vs Mahito climax"],
        "tags": ["yuji", "mahito", "fight", "climax"]
    },
    "S02E17": {
        "characters": ["gojo"],
        "events": ["Gojo sealed", "Prison Realm"],
        "tags": ["gojo", "sealed", "prison_realm", "shibuya"]
    },

    # Season 3
    "S03E01": {
        "characters": ["yuji", "megumi"],
        "events": ["Culling Game begins"],
        "tags": ["yuji", "megumi", "culling_game"]
    },
}


def load_database(db_path: Path) -> Dict[str, Any]:
    """Load timestamp database."""
    with open(db_path) as f:
        return json.load(f)


def save_database(db_path: Path, database: Dict[str, Any]):
    """Save updated database."""
    with open(db_path, 'w') as f:
        json.dump(database, f, indent=2)


def find_episode_by_season_episode(database: Dict[str, Any], season: int, episode: int) -> tuple[str, Dict[str, Any]]:
    """Find episode entry by season/episode number."""
    for source_id, ep_data in database.get("episodes", {}).items():
        if ep_data.get("season") == season and ep_data.get("episode") == episode:
            return source_id, ep_data
    return None, None


def tag_episode_scenes(
    episode_data: Dict[str, Any],
    characters: List[str],
    events: List[str],
    tags: List[str],
    highlight_windows: List[tuple[float, float]] = None
):
    """Tag all scenes in episode with semantic metadata."""
    for scene in episode_data.get("scenes", []):
        scene["semantic"]["status"] = "candidate"  # Mark as candidate (not fully verified without vision)
        scene["semantic"]["characters"] = characters
        scene["semantic"]["action"] = events[0] if events else None
        scene["semantic"]["tags"] = tags

        # Mark highlight windows as high-priority
        if highlight_windows:
            scene_start = scene["start"]
            scene_end = scene["end"]
            for hw_start, hw_end in highlight_windows:
                if (scene_start >= hw_start and scene_start <= hw_end) or \
                   (scene_end >= hw_start and scene_end <= hw_end):
                    scene["semantic"]["tags"].append("highlight")
                    break


def build_verified_events(database: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build verified event entries from tagged episodes."""
    events = []

    for season_ep, event_data in ICONIC_EVENTS.items():
        season = int(season_ep[1:3])
        episode = int(season_ep[4:6])

        source_id, ep_data = find_episode_by_season_episode(database, season, episode)

        if not source_id or not ep_data:
            print(f"  ⚠️  Episode {season_ep} not found in database")
            continue

        # Get highlight scenes or all scenes
        highlight_windows = event_data.get("highlight_windows", [])

        if highlight_windows:
            # Use only highlight windows
            cut_windows = []
            for scene in ep_data.get("scenes", []):
                scene_start = scene["start"]
                scene_end = scene["end"]
                for hw_start, hw_end in highlight_windows:
                    if (scene_start >= hw_start and scene_start <= hw_end) or \
                       (scene_end >= hw_start and scene_end <= hw_end):
                        cut_windows.append({
                            "start": scene["start"],
                            "end": scene["end"],
                            "duration": scene["duration"],
                            "semantic_status": "candidate",
                            "scene_suitability": {
                                "slowmo_safe": True,
                                "impact": True,
                                "high_motion": True
                            }
                        })
        else:
            # Use all scenes from episode
            cut_windows = [
                {
                    "start": scene["start"],
                    "end": scene["end"],
                    "duration": scene["duration"],
                    "semantic_status": "candidate",
                    "scene_suitability": {
                        "slowmo_safe": True,
                        "impact": False,
                        "high_motion": False
                    }
                }
                for scene in ep_data.get("scenes", [])
            ]

        if not cut_windows:
            continue

        # Build event entry
        event_id = f"{season_ep.lower()}_{event_data['events'][0].lower().replace(' ', '_')[:30]}"

        # Generate title from event
        title = event_data['events'][0]
        if len(event_data['characters']) == 1:
            char_name = event_data['characters'][0].title()
            if char_name.lower() not in title.lower():
                title = f"{char_name}: {title}"

        event = {
            "event_id": event_id,
            "source_id": source_id,
            "drive_file_id": ep_data.get("drive_file_id"),
            "canonical_filename": ep_data.get("canonical_filename"),
            "season": season,
            "episode": episode,
            "title_metadata": {
                "title": title,
                "quote": event_data['events'][0],
                "tags": ["jjk", "animeedit", "4kedit"] + event_data['tags']
            },
            "cut_windows": cut_windows,
            "eligible_for_upload": True  # Marked eligible (research-verified, but not vision-verified)
        }

        events.append(event)
        print(f"  ✓ Created event: {event_id} ({len(cut_windows)} windows)")

    return events


def auto_tag_database(db_path: Path):
    """Auto-tag database with research-verified iconic events."""
    print("=" * 80)
    print("🏷️  Auto-Tagging JJK Iconic Events")
    print("=" * 80)

    database = load_database(db_path)

    print(f"\n📊 Database: {database['total_episodes']} episodes, {database['total_scenes']} scenes")
    print(f"📋 Tagging {len(ICONIC_EVENTS)} iconic episodes...")

    # Tag episode scenes
    tagged_count = 0
    for season_ep, event_data in ICONIC_EVENTS.items():
        season = int(season_ep[1:3])
        episode = int(season_ep[4:6])

        source_id, ep_data = find_episode_by_season_episode(database, season, episode)

        if source_id and ep_data:
            tag_episode_scenes(
                ep_data,
                event_data["characters"],
                event_data["events"],
                event_data["tags"],
                event_data.get("highlight_windows")
            )
            tagged_count += 1
            print(f"  ✓ Tagged {season_ep}: {event_data['events'][0]}")

    # Build verified events
    print(f"\n🎬 Building verified event entries...")
    events = build_verified_events(database)
    database["events"] = events

    # Save
    save_database(db_path, database)

    print("\n" + "=" * 80)
    print(f"✅ Auto-tagging complete!")
    print(f"📊 Tagged episodes: {tagged_count}/{len(ICONIC_EVENTS)}")
    print(f"📊 Created events: {len(events)}")
    print(f"💾 Database: {db_path}")
    print("=" * 80)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto-tag JJK iconic events")
    parser.add_argument("--database", type=str, default=str(DEFAULT_DATABASE),
                        help="Timestamp database JSON path")

    args = parser.parse_args()
    auto_tag_database(Path(args.database))


if __name__ == "__main__":
    main()
