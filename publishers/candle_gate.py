#!/usr/bin/env python3
"""
Jack Craig "Tested&Proved" Candle Gate & Upload Protection Engine for Anime Edits (@Jazzcreatesclips).
Protects well-performing videos from being choked by too-frequent uploads.

Layers:
1. Layer 0 (24-Hour Minimum Spacing Guard):
   Ensures at least 24 hours between uploads to let each video circulate on the algorithm.
2. Layer 1 (Early Momentum Gate):
   If a video reaches >= 2,000 views within its first 24 hours, pause uploads to let early traction run.
   If near threshold (1.7k-1.99k), flags timer.
3. Layer 2 (Viral Velocity Gate - 2k-3k views/hr):
   If hourly velocity exceeds 2,500 views/hr (2k-3k range), block upload until velocity stabilizes.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STATE_FILE = ROOT_DIR / "metadata" / "candle_gate_state.json"
DEFAULT_HISTORY_FILE = ROOT_DIR / "metadata" / "youtube_upload_history.json"

# Layer 2 Constants: Viral Velocity Gate (2k-3k views/hour)
VIEW_THRESHOLD_PER_HOUR = 2500  # Midpoint of 2k-3k views/hr velocity window
VIEW_THRESHOLD_MIN = 2000
VIEW_THRESHOLD_MAX = 3000
SUSTAINED_HOURS_REQUIRED = 24

# Layer 1 Constants: Early Momentum Gate
EARLY_HOURS_WINDOW = 24.0
EARLY_VIEWS_THRESHOLD = 2000
NEAR_THRESHOLD_PERCENT = 0.85
NEAR_THRESHOLD_VIEWS = int(EARLY_VIEWS_THRESHOLD * NEAR_THRESHOLD_PERCENT)
TIMER_DELAY_SECONDS = 3600

# Layer 0 Constants: 24-Hour Minimum Upload Spacing Guard
MIN_UPLOAD_SPACING_HOURS = 24.0


class CandleGate:
    """Evaluates YouTube Shorts hourly candles and multi-layer performance gates."""

    def __init__(
        self,
        state_file: Path = DEFAULT_STATE_FILE,
        history_file: Path = DEFAULT_HISTORY_FILE,
    ):
        self.state_file = state_file
        self.history_file = history_file

    def evaluate_upload_spacing(
        self,
        elapsed_hours: float,
        min_spacing_hours: float = MIN_UPLOAD_SPACING_HOURS,
        max_inline_wait_hours: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Layer 0 - 24-Hour Spacing Gate:
        Ensures next upload triggers after at least 24h of prior upload.
        If within max_inline_wait_hours (<= 4 hours) of the 24h mark, triggers an inline sleep
        to protect against GitHub runner cron drift and avoid an unnecessary daily skip.
        """
        can_upload = elapsed_hours >= min_spacing_hours
        remaining_hours = max(min_spacing_hours - elapsed_hours, 0.0)
        requires_spacing_sleep = (not can_upload) and (0 < remaining_hours <= max_inline_wait_hours)
        spacing_sleep_seconds = int(remaining_hours * 3600.0) + 5 if requires_spacing_sleep else 0

        if not can_upload and not requires_spacing_sleep:
            decision = "UPLOAD_BLOCKED_24H_SPACING"
            recommendation = (
                f"⏳ 24-Hour Spacing Guard: Active video was uploaded {elapsed_hours:.1f}h ago "
                f"(< {min_spacing_hours:.0f}h required). Holding next upload to protect its initial 24h circulation window. "
                f"Next upload permitted in {remaining_hours:.1f}h."
            )
        elif requires_spacing_sleep:
            decision = "SPACING_WAIT_INLINE"
            recommendation = (
                f"⏱️ 24-Hour Spacing Guard: Active video was uploaded {elapsed_hours:.1f}h ago. "
                f"Remaining wait ({remaining_hours * 60:.1f} min) is within inline window ({max_inline_wait_hours * 60:.0f} min). "
                f"Waiting inline for {spacing_sleep_seconds // 60}m before upload to maintain daily cadence."
            )
        else:
            decision = "SPACING_CLEARED"
            recommendation = (
                f"✅ 24-Hour Spacing Cleared: Active video has been up for {elapsed_hours:.1f}h "
                f"(>= {min_spacing_hours:.0f}h). Evaluating performance under Layer 1 & Layer 2."
            )

        return {
            "layer": 0,
            "decision": decision,
            "can_upload": can_upload,
            "requires_spacing_sleep": requires_spacing_sleep,
            "spacing_sleep_seconds": spacing_sleep_seconds,
            "elapsed_hours": round(elapsed_hours, 2),
            "min_spacing_hours": min_spacing_hours,
            "remaining_hours": round(remaining_hours, 2),
            "recommendation": recommendation,
        }

    def evaluate_early_momentum(
        self,
        total_views: int,
        elapsed_hours: float,
        threshold_views: int = EARLY_VIEWS_THRESHOLD,
        window_hours: float = EARLY_HOURS_WINDOW,
        near_threshold_views: int = NEAR_THRESHOLD_VIEWS,
        timer_seconds: int = TIMER_DELAY_SECONDS,
    ) -> Dict[str, Any]:
        """Layer 1 - Early Momentum Gate: Checks >= 2k views in 24h."""
        is_early_window = elapsed_hours <= window_hours
        has_early_momentum = is_early_window and total_views >= threshold_views
        is_near_threshold = is_early_window and (near_threshold_views <= total_views < threshold_views)

        if has_early_momentum:
            decision = "UPLOAD_BLOCKED_EARLY_MOMENTUM"
            can_upload = False
            requires_timer = False
            recommendation = (
                f"🚀 Layer 1 Triggered: Early momentum detected! Video has reached {total_views:,} views "
                f"in {elapsed_hours:.1f}h (>= {threshold_views:,} views in {window_hours:.0f}h). "
                f"Pausing upload to let early algorithmic traction perform before moving to Layer 2."
            )
        elif is_near_threshold:
            decision = "RETRY_TIMER_REQUIRED"
            can_upload = False
            requires_timer = True
            remaining_window = max(window_hours - elapsed_hours, 0.0)
            recommendation = (
                f"⏳ Video is at {total_views:,} views in {elapsed_hours:.1f}h (approaching {threshold_views:,} threshold "
                f"with {remaining_window:.1f}h remaining in the {window_hours:.0f}h window). "
                f"Automatically setting a 1-hour timer ({timer_seconds // 60}m) to re-check before uploading."
            )
        else:
            decision = "LAYER_1_CLEARED"
            can_upload = True
            requires_timer = False
            if is_early_window:
                recommendation = (
                    f"Video has {total_views:,} views in {elapsed_hours:.1f}h (< {threshold_views:,} threshold). "
                    f"Layer 1 cleared; evaluating under Layer 2."
                )
            else:
                recommendation = (
                    f"Video is past the initial {window_hours:.0f}h window ({elapsed_hours:.1f}h elapsed). "
                    f"Layer 1 passed; evaluating under Layer 2."
                )

        return {
            "layer": 1,
            "decision": decision,
            "can_upload": can_upload,
            "requires_timer": requires_timer,
            "timer_seconds": timer_seconds,
            "total_views": total_views,
            "elapsed_hours": round(elapsed_hours, 2),
            "recommendation": recommendation,
        }

    def evaluate_hourly_candles(
        self,
        hourly_views: List[int],
        threshold: int = VIEW_THRESHOLD_PER_HOUR,
        required_hours: int = SUSTAINED_HOURS_REQUIRED,
    ) -> Dict[str, Any]:
        """Layer 2 - Viral Velocity Gate: Evaluates 2k-3k views/hr threshold."""
        if not hourly_views:
            return {
                "decision": "UPLOAD_BLOCKED_NO_DATA",
                "can_upload": False,
                "consecutive_hours_below": 0,
                "current_hourly_rate": 0,
                "peak_hourly_rate": 0,
                "recommendation": "No hourly candle data provided. Initial upload cleared.",
            }

        peak_rate = max(hourly_views)
        current_rate = hourly_views[-1]

        consecutive_below = 0
        for rate in reversed(hourly_views):
            if rate < threshold:
                consecutive_below += 1
            else:
                break

        if peak_rate < threshold:
            can_upload = True
            decision = "UPLOAD_CLEARED"
            recommendation = (
                f"Active video velocity ({current_rate:,} views/hr, peak: {peak_rate:,}/hr) "
                f"is below {threshold:,} views/hr threshold. Cleared to upload next video."
            )
        else:
            can_upload = consecutive_below >= required_hours
            if can_upload:
                decision = "UPLOAD_CLEARED"
                recommendation = (
                    f"Active video has stabilized below {threshold:,} views/hr for {consecutive_below} consecutive hours. "
                    f"Cleared to upload next video without cannibalizing active push."
                )
            else:
                decision = "UPLOAD_BLOCKED_ACTIVE_PUSH"
                recommendation = (
                    f"Active push in progress! Current rate: {current_rate:,} views/hr (Peak: {peak_rate:,}/hr). "
                    f"Only {consecutive_below}/{required_hours} hours below threshold. "
                    f"DO NOT upload yet — rushing now will flatline algorithm momentum."
                )

        return {
            "decision": decision,
            "can_upload": can_upload,
            "consecutive_hours_below": consecutive_below,
            "required_hours": required_hours,
            "threshold": threshold,
            "current_hourly_rate": current_rate,
            "peak_hourly_rate": peak_rate,
            "total_candles": len(hourly_views),
            "recommendation": recommendation,
        }

    def save_state(self, state: Dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def record_upload(self, entry: Dict[str, Any]) -> None:
        history = []
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text(encoding="utf-8"))
            except Exception:
                history = []
        history.append(entry)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def evaluate_live_channel(self, youtube_client=None) -> Dict[str, Any]:
        """Queries live YouTube API for recent video velocity and enforces layers 0, 1, and 2."""
        if youtube_client is None:
            return self.load_state()

        try:
            vid_id = None
            title = "Previous Anime Edit"
            published_at_str = None

            if self.history_file.exists():
                try:
                    records = json.loads(self.history_file.read_text(encoding="utf-8"))
                    if records and isinstance(records, list):
                        for rec in reversed(records):
                            raw_id = rec.get("video_id")
                            if raw_id and not str(raw_id).startswith("dry_run"):
                                vid_id = raw_id
                                title = rec.get("title", title)
                                published_at_str = rec.get("timestamp")
                                break
                except Exception:
                    pass

            if not vid_id:
                try:
                    channels_res = youtube_client.channels().list(mine=True, part="contentDetails").execute()
                    items = channels_res.get("items", [])
                    if items:
                        uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
                        pl_items = youtube_client.playlistItems().list(
                            playlistId=uploads_id, part="snippet", maxResults=1
                        ).execute().get("items", [])
                        if pl_items:
                            vid_id = pl_items[0]["snippet"]["resourceId"]["videoId"]
                            title = pl_items[0]["snippet"]["title"]
                            published_at_str = pl_items[0]["snippet"]["publishedAt"]
                except Exception:
                    pass

            if not vid_id:
                return {"can_upload": True, "reason": "No prior uploads found; initial upload cleared"}

            vid_stats = youtube_client.videos().list(id=vid_id, part="statistics,snippet").execute()
            v_items = vid_stats.get("items", [])
            if not v_items:
                return {"can_upload": True, "reason": f"Could not fetch stats for video {vid_id}"}

            snippet = v_items[0].get("snippet", {})
            title = snippet.get("title", title)
            if not published_at_str or "publishedAt" in snippet:
                published_at_str = snippet.get("publishedAt", published_at_str)

            total_views = int(v_items[0]["statistics"].get("viewCount", 0))
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            elapsed_hours = max((now - published_at).total_seconds() / 3600.0, 0.1)

            state = self.load_state()
            history_candles = state.get("hourly_candles", [])
            last_snapshot = state.get("last_snapshot", {})

            if last_snapshot.get("video_id") == vid_id and "timestamp" in last_snapshot:
                prev_views = last_snapshot.get("total_views", 0)
                try:
                    prev_time = datetime.fromisoformat(last_snapshot["timestamp"])
                    if prev_time.tzinfo is None:
                        prev_time = prev_time.replace(tzinfo=timezone.utc)
                    delta_hours = max((now - prev_time).total_seconds() / 3600.0, 0.1)
                    hourly_velocity = max(int((total_views - prev_views) / delta_hours), 0)
                except Exception:
                    hourly_velocity = int(total_views / elapsed_hours)
            else:
                hourly_velocity = int(total_views / elapsed_hours)

            history_candles.append(hourly_velocity)
            history_candles = history_candles[-48:]

            # Layer 0: 24-Hour Minimum Upload Spacing Guard
            spacing_eval = self.evaluate_upload_spacing(elapsed_hours)

            # Layer 1: Early Momentum Gate (>= 2k views in 12h)
            layer1_eval = self.evaluate_early_momentum(total_views, elapsed_hours)

            # Layer 2: 2k-3k views/hr sustained velocity candle monitoring
            layer2_eval = self.evaluate_hourly_candles(history_candles)
            if elapsed_hours <= 48 and hourly_velocity >= VIEW_THRESHOLD_PER_HOUR:
                layer2_eval["can_upload"] = False
                layer2_eval["decision"] = "UPLOAD_BLOCKED_ACTIVE_PUSH"
                layer2_eval["recommendation"] = (
                    f"🔥 Active anime edit '{title}' is performing well ({hourly_velocity:,} views/hr)! "
                    f"Letting it perform on the algorithm before uploading another."
                )

            requires_timer = layer1_eval.get("requires_timer", False)
            timer_seconds = layer1_eval.get("timer_seconds", 3600)

            # Precedence:
            # 1. Layer 0: 24h spacing guard
            # 2. Layer 1: Early momentum gate
            # 3. Layer 2: Viral velocity gate
            requires_spacing_sleep = spacing_eval.get("requires_spacing_sleep", False)
            spacing_sleep_seconds = spacing_eval.get("spacing_sleep_seconds", 0)

            if not spacing_eval["can_upload"]:
                final_decision = spacing_eval["decision"]
                can_upload = False
                final_recommendation = spacing_eval["recommendation"]
                active_layer = "Layer 0 (24-Hour Spacing: Inline Wait)" if requires_spacing_sleep else "Layer 0 (24-Hour Minimum Spacing Guard)"
            elif not layer1_eval["can_upload"]:
                final_decision = layer1_eval["decision"]
                can_upload = False
                final_recommendation = layer1_eval["recommendation"]
                active_layer = "Layer 1 (Early Momentum: 1-Hour Timer)" if requires_timer else "Layer 1 (Early Momentum Gate: >=2k views in 24h)"
            elif not layer2_eval["can_upload"]:
                final_decision = layer2_eval["decision"]
                can_upload = False
                final_recommendation = layer2_eval["recommendation"]
                active_layer = f"Layer 2 (Viral Velocity Gate: >={VIEW_THRESHOLD_PER_HOUR:,} views/hr)"
            else:
                final_decision = "UPLOAD_CLEARED"
                can_upload = True
                final_recommendation = layer2_eval["recommendation"]
                active_layer = "All Layers Cleared"

            candle_eval = {
                "decision": final_decision,
                "can_upload": can_upload,
                "requires_timer": requires_timer,
                "timer_seconds": timer_seconds,
                "requires_spacing_sleep": requires_spacing_sleep,
                "spacing_sleep_seconds": spacing_sleep_seconds,
                "active_layer": active_layer,
                "recommendation": final_recommendation,
                "layer0": spacing_eval,
                "layer1": layer1_eval,
                "layer2": layer2_eval,
            }

            updated_state = {
                "candle_evaluation": candle_eval,
                "hourly_candles": history_candles,
                "last_snapshot": {
                    "video_id": vid_id,
                    "title": title,
                    "total_views": total_views,
                    "timestamp": now.isoformat(),
                    "hourly_velocity": hourly_velocity,
                    "elapsed_hours": round(elapsed_hours, 2),
                }
            }
            self.save_state(updated_state)
            return updated_state
        except Exception as e:
            return {"can_upload": True, "reason": f"Live channel check failed: {e}; clearing upload"}
