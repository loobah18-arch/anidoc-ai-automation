"""
JJK Verified Event Database Query Engine
Loads verified events from timestamp database and provides event-first selection.
NO keyword/intensity guessing - only returns events with verified semantic evidence.
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional


class VerifiedEventDatabase:
    """Query engine for verified JJK events only."""

    def __init__(self, db_path: Optional[Path] = None, history_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "jjk_timestamp_database.json"
        if history_path is None:
            history_path = Path(__file__).parent.parent / "data" / "jjk_render_history.json"

        self.db_path = db_path
        self.history_path = history_path
        self.database = self._load_database()
        self.history = self._load_history()

    def _load_database(self) -> Dict[str, Any]:
        """Load timestamp database."""
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Timestamp database not found at {self.db_path}. "
                f"Run 'Build JJK Timestamp Database' workflow first."
            )

        with open(self.db_path, "r") as f:
            return json.load(f)

    def _load_history(self) -> Dict[str, Any]:
        """Load render history."""
        if self.history_path.exists():
            try:
                with open(self.history_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "version": "1.0.0",
            "last_updated": None,
            "events_rendered": {},
            "events_uploaded": {}
        }

    def _save_history(self):
        """Persist history."""
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_path, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"⚠️ [EventDB] Failed to save history: {e}")

    def get_eligible_events(self) -> List[Dict[str, Any]]:
        """
        Return only verified upload-eligible events.
        Filters by:
        - event.eligible_for_upload == True
        - All cut_windows verified
        - Has stable Drive source_id
        """
        eligible = []

        for event in self.database.get("events", []):
            if not event.get("eligible_for_upload"):
                continue

            # Validate event structure
            if not event.get("event_id") or not event.get("source_id"):
                continue

            if not event.get("cut_windows"):
                continue

            # Check all windows verified
            all_verified = all(
                w.get("semantic_status") == "verified"
                for w in event.get("cut_windows", [])
            )

            if not all_verified:
                continue

            # Check source has Drive ID
            source_id = event.get("source_id")
            episode = self.database.get("episodes", {}).get(source_id)
            if not episode or not episode.get("drive_file_id"):
                continue

            eligible.append(event)

        return eligible

    def select_event_for_render(
        self,
        custom_title: Optional[str] = None,
        prefer_unused: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Select one verified event for rendering.

        If custom_title provided:
        - Must exactly match an eligible event's title_metadata.title
        - Returns matched event or raises ValueError

        Otherwise:
        - Randomly selects from eligible events
        - Prefers events not in render history (if prefer_unused)
        - Returns selected event
        """
        eligible = self.get_eligible_events()

        if not eligible:
            raise RuntimeError(
                "No verified eligible events found. "
                "Run semantic verification workflow to create events."
            )

        # Custom title resolution
        if custom_title:
            matches = [
                e for e in eligible
                if e.get("title_metadata", {}).get("title") == custom_title
            ]

            if not matches:
                raise ValueError(
                    f"Custom title '{custom_title}' does not match any verified event. "
                    f"Available verified titles: {[e.get('title_metadata', {}).get('title') for e in eligible[:5]]}"
                )

            return matches[0]

        # Random selection with history preference
        rendered_events = set(self.history.get("events_rendered", {}).keys())

        if prefer_unused:
            unused = [e for e in eligible if e.get("event_id") not in rendered_events]

            if unused:
                eligible = unused
                print(f"🎯 [EventDB] {len(unused)} unused verified events available")
            else:
                print(f"🔄 [EventDB] All {len(eligible)} verified events used, rotating")

        # Prefer episode diversity
        episode_counts = {}
        for event_id in rendered_events:
            event = next((e for e in self.database.get("events", []) if e.get("event_id") == event_id), None)
            if event:
                ep = event.get("episode")
                episode_counts[ep] = episode_counts.get(ep, 0) + 1

        # Sort by least-used episode
        eligible_sorted = sorted(
            eligible,
            key=lambda e: episode_counts.get(e.get("episode"), 0)
        )

        selected = random.choice(eligible_sorted[:max(1, len(eligible_sorted) // 2)])

        print(f"✅ [EventDB] Selected event: {selected.get('event_id')}")
        print(f"   Title: {selected.get('title_metadata', {}).get('title')}")
        print(f"   Source: S{selected.get('season'):02d}E{selected.get('episode'):02d}")
        print(f"   Windows: {len(selected.get('cut_windows', []))}")

        return selected

    def mark_event_rendered(self, event_id: str, render_metadata: Dict[str, Any]):
        """Record successful render."""
        from datetime import datetime

        self.history["events_rendered"][event_id] = {
            "rendered_at": datetime.utcnow().isoformat() + "Z",
            "output_path": str(render_metadata.get("output_path", "")),
            "duration": render_metadata.get("duration"),
            "clips_count": render_metadata.get("cuts_count")
        }

        self.history["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self._save_history()

        print(f"📝 [EventDB] Marked event {event_id} as rendered")

    def mark_event_uploaded(self, event_id: str, upload_result: Dict[str, Any]):
        """Record successful upload."""
        from datetime import datetime

        self.history["events_uploaded"][event_id] = {
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
            "video_url": upload_result.get("url", ""),
            "video_id": upload_result.get("video_id", ""),
            "platform": upload_result.get("platform", "youtube")
        }

        self.history["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self._save_history()

        print(f"📤 [EventDB] Marked event {event_id} as uploaded")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        episodes = self.database.get("episodes", {})
        events = self.database.get("events", [])
        eligible = self.get_eligible_events()

        return {
            "total_episodes": len([e for e in episodes.values() if e.get("scan_status") == "success"]),
            "total_scenes": self.database.get("total_scenes", 0),
            "total_events": len(events),
            "eligible_events": len(eligible),
            "events_rendered": len(self.history.get("events_rendered", {})),
            "events_uploaded": len(self.history.get("events_uploaded", {})),
            "last_updated": self.database.get("generated_at")
        }
