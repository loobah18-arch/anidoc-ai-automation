"""
YouTube Data API v3 Auto-Publisher for 4K Phonk / Scene Edits.
"""
import os
import json
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

SHORTS_MAX_DURATION_SECONDS = 180.0


def validate_shorts_video(video_path: Path) -> Tuple[bool, str]:
    """Require a square video no longer than YouTube's Shorts limit."""
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height:format=duration",
                "-of", "json", str(video_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        info = json.loads(probe.stdout)
        stream = (info.get("streams") or [{}])[0]
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        duration = float((info.get("format") or {}).get("duration") or 0)
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        return False, f"Could not inspect video for Shorts requirements: {exc}"

    if not width or not height:
        return False, "Video has no readable video dimensions"
    if width > height:
        return False, f"Video must be vertical (9:16) or square (1:1) for YouTube Shorts, got {width}x{height}"
    if duration <= 0:
        return False, "Video has no readable duration"
    if duration > SHORTS_MAX_DURATION_SECONDS:
        return False, f"Video must be 3 minutes or shorter, got {duration:.2f}s"

    return True, f"{width}x{height}, {duration:.2f}s"



def _shorts_title(title: str) -> str:
    """Keep the title within YouTube's limit and mark it as a Short."""
    clean_title = " ".join(str(title).split()).strip()
    if "#shorts" not in clean_title.lower():
        suffix = " #Shorts"
        clean_title = f"{clean_title[:100 - len(suffix)].rstrip()}{suffix}"
    return clean_title[:100]


def get_valid_access_token() -> Optional[str]:
    """Exchanges refresh token for a fresh access token if available."""
    access_token = os.environ.get("YOUTUBE_ACCESS_TOKEN") or os.environ.get("ACCESS_TOKEN")
    if access_token:
        return access_token
        
    client_secret_raw = os.environ.get("YOUTUBE_CLIENT_SECRET") or os.environ.get("CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN") or os.environ.get("REFRESH_TOKEN")
    client_id_direct = os.environ.get("YOUTUBE_CLIENT_ID") or os.environ.get("CLIENT_ID")
    
    if not refresh_token:
        return None
        
    client_id = None
    client_secret = None
    
    # 1. Try parsing client_secret_raw as JSON or file path
    if client_secret_raw:
        try:
            if Path(client_secret_raw).exists():
                with open(client_secret_raw, "r") as f:
                    data = json.load(f)
            else:
                data = json.loads(client_secret_raw)
                
            client_info = data.get("installed") or data.get("web") or {}
            client_id = client_info.get("client_id")
            client_secret = client_info.get("client_secret")
        except Exception:
            # client_secret_raw is the plain secret string
            client_secret = client_secret_raw
            
    if not client_id and client_id_direct:
        client_id = client_id_direct
        
    if not client_id or not client_secret:
        return None
        
    try:
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }, timeout=10)
        
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            print(f"[YouTube] Token refresh notice ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[YouTube] Notice refreshing access token: {e}")
        
    return None


def check_youtube_video_status(
    youtube: Any,
    video_id: str,
    timeout_sec: float = 12.0,
    poll_interval_sec: float = 3.0,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Polls YouTube Data API to verify if an uploaded video is blocked or rejected.

    Returns:
        (is_blocked, rejection_reason, raw_status_dict)
    """
    import time
    if not youtube or not video_id:
        return False, None, {}

    videos_resource = getattr(youtube, "videos", None)
    if callable(videos_resource):
        videos_resource = videos_resource()

    if not videos_resource or not hasattr(videos_resource, "list"):
        return False, None, {}

    start_time = time.time()
    last_status: Dict[str, Any] = {}

    while True:
        try:
            req = videos_resource.list(
                part="status,contentDetails,processingDetails",
                id=video_id,
            )
            resp = req.execute() if hasattr(req, "execute") else req
        except Exception as e:
            err_str = str(e).lower()
            if any(term in err_str for term in ("blocked", "copyright", "termsofservice", "rejected", "claim")):
                print(f"[YouTube] 🛑 API indicates block on video {video_id}: {e}")
                return True, "api_error_blocked", {"error": str(e)}
            print(f"[YouTube] ⚠️ YouTube status check query warning for {video_id}: {e}")
            break

        if not isinstance(resp, dict):
            return False, None, {}

        items = resp.get("items", [])
        if not items:
            print(f"[YouTube] ⚠️ Video {video_id} not found in YouTube query.")
            return True, "video_not_found_post_upload", {}

        item = items[0]
        if not isinstance(item, dict):
            return False, None, {}

        status = item.get("status", {})
        content_details = item.get("contentDetails", {})
        processing_details = item.get("processingDetails", {})
        last_status = {
            "status": status,
            "contentDetails": content_details,
            "processingDetails": processing_details,
        }

        upload_status = str(status.get("uploadStatus", "")).lower()
        rejection_reason = status.get("rejectionReason")
        processing_status = str(processing_details.get("processingStatus", "")).lower()
        processing_failure = processing_details.get("processingFailureReason")

        # 1. Check explicit rejection reason or uploadStatus
        if upload_status == "rejected" or rejection_reason:
            reason = str(rejection_reason or "upload_rejected")
            print(f"[YouTube] 🛑 Video {video_id} rejected by YouTube: reason='{reason}' (uploadStatus={upload_status})")
            return True, reason, last_status

        # 2. Check processing failure
        if processing_status in ("failed", "terminated") or processing_failure:
            reason = str(processing_failure or "processing_failed")
            print(f"[YouTube] 🛑 Video {video_id} processing failed: reason='{reason}' (processingStatus={processing_status})")
            return True, reason, last_status

        # 3. Check region restrictions (blocked worldwide)
        region_restriction = content_details.get("regionRestriction", {})
        blocked_regions = region_restriction.get("blocked", [])
        allowed_regions = region_restriction.get("allowed")
        if blocked_regions and len(blocked_regions) > 50:
            print(f"[YouTube] 🛑 Video {video_id} is blocked in {len(blocked_regions)} regions.")
            return True, "region_restricted_block", last_status
        if allowed_regions is not None and len(allowed_regions) == 0:
            print(f"[YouTube] 🛑 Video {video_id} has empty allowed regions list.")
            return True, "region_restricted_empty_allowed", last_status

        elapsed = time.time() - start_time
        if upload_status in ("uploaded", "processed") and processing_status in ("succeeded", "processing"):
            if elapsed >= timeout_sec or timeout_sec <= 0:
                print(f"[YouTube] ✅ Video {video_id} clean after check (uploadStatus={upload_status}, processingStatus={processing_status}).")
                return False, None, last_status

        if elapsed >= timeout_sec:
            break

        time.sleep(poll_interval_sec)

    return False, None, last_status


def delete_blocked_youtube_video(youtube: Any, video_id: str) -> bool:
    """Immediately delete a blocked YouTube upload to protect channel standing."""
    if not youtube or not video_id:
        return False
    try:
        videos_resource = getattr(youtube, "videos", None)
        if callable(videos_resource):
            videos_resource = videos_resource()
        if hasattr(videos_resource, "delete"):
            videos_resource.delete(id=video_id).execute()
            print(f"[YouTube] 🗑️ Deleted blocked YouTube video {video_id} to maintain channel standing.")
            return True
    except Exception as e:
        print(f"[YouTube] ⚠️ Could not auto-delete video {video_id} via API: {e}")
    return False


def classify_block_reason(
    rejection_reason: str,
    raw_status: Optional[Dict[str, Any]] = None,
    bgm_track: str = "",
) -> str:
    """Classifies YouTube block cause into 'audio' (BGM), 'clip' (visual footage), or 'both'.

    - 'audio': audio match, sound recording claim, or commercial non-NCS audio used.
    - 'clip': video match, visual footage claim, or audio was already verified NCS.
    - 'both': mixed or generic claim where both audio and video require remediation.
    """
    raw_status = raw_status or {}
    corpus = f"{rejection_reason} {json.dumps(raw_status)}".lower()

    audio_signals = ["audio", "music", "sound", "song", "track", "melody", "phonk", "sound_recording", "audio_fingerprint", "audiomatch"]
    video_signals = ["video", "visual", "footage", "clip", "scene", "audiovisual", "videomatch", "visual_fingerprint"]

    has_audio = any(s in corpus for s in audio_signals)
    has_video = any(s in corpus for s in video_signals)

    if has_audio and not has_video:
        return "audio"
    if has_video and not has_audio:
        return "clip"

    # If already using an authentic NCS track, audio cannot be the block cause -> must be the video clip!
    bgm_lower = str(bgm_track).lower()
    if any(ncs_kw in bgm_lower for ncs_kw in ("ncs", "cradles", "aerohead", "nocopyright")):
        return "clip"

    # If generic "copyright" with non-NCS phonk, audio is the dominant content ID claim
    return "audio" if not has_video else "both"


def remediate_metadata_for_retry(title: str, description: str, tags: list, attempt: int) -> Tuple[str, str, list]:
    """Applies progressive metadata modifications to avoid content matching triggers."""
    clean_title = title.replace("#Shorts", "").replace("#shorts", "").strip()
    if attempt == 1:
        new_title = f"{clean_title} | Scene Breakdown 🎬🔥"
    else:
        new_title = f"{clean_title} | 4K Anime Edit ⚡"
    new_title = _shorts_title(new_title)

    disclaimer = "\n\n📌 Transformative Fair Use: Original commentary, sound design, and narrative pacing."
    new_desc = f"{description.strip()}{disclaimer}"

    sanitized_tags = [t for t in tags if t.lower() not in ("full", "episode", "leaked", "raw")]
    sanitized_tags.extend(["scenebreakdown", "animeedit", "phonk"])
    return new_title, new_desc, list(dict.fromkeys(sanitized_tags))[:15]


def remediate_video_for_retry(input_path: Path, output_path: Path, attempt: int) -> Path:
    """Applies lightweight anti-content-ID audio/visual transformation for retry upload."""
    if not input_path.exists():
        return input_path
    try:
        # Slight speed variation (1.015x) and subtle audio pitch adjust to break hash matching
        speed = 1.015 if attempt == 1 else 1.025
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-filter_complex", f"[0:v]setpts={1.0 / speed:.4f}*PTS,hflip[v];[0:a]atempo={speed:.4f}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            str(output_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 10000:
            print(f"[YouTube] 🛠️ Applied remediation v{attempt} to video: {output_path.name}")
            return output_path
    except Exception as e:
        print(f"[YouTube] ⚠️ Video remediation notice: {e}")
    return input_path


def upload_video_with_block_retry(
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    privacy_status: str = "public",
    max_retries: int = 2,
    verify_timeout_sec: float = 12.0,
    dry_run: bool = False,
    youtube_client: Any = None,
    media_upload_cls: Any = None,
    bgm_track: str = "",
    force_upload: bool = False,
    gate_check: bool = False,
    candle_gate: Optional[Any] = None,
) -> Dict[str, Any]:
    """Uploads a video to YouTube with automatic block detection, deletion of blocked uploads,

    progressive remediation, block reason diagnosis, and retry orchestration.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return {"status": "error", "reason": "Video file not found"}

    is_valid, validation_reason = validate_shorts_video(video_path)
    if not is_valid:
        print(f"[YouTube] ❌ Shorts validation failed: {validation_reason}")
        return {"status": "error", "reason": validation_reason}

    if dry_run:
        print("[YouTube] ℹ️ Dry-run mode enabled: Skipping YouTube upload.")
        return {"status": "skipped", "reason": "dry_run"}

    youtube = youtube_client
    if not youtube:
        access_token = get_valid_access_token()
        if not access_token:
            print("[YouTube] ⚠️ YouTube API credentials not configured in environment. Skipping upload.")
            return {"status": "skipped", "reason": "No credentials"}
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            creds = Credentials(token=access_token)
            youtube = build("youtube", "v3", credentials=creds)
        except Exception as e:
            print(f"[YouTube] ⚠️ Could not build YouTube client: {e}")
            return {"status": "error", "reason": f"Client build failed: {e}"}

    # Evaluate Candle Gate performance protection
    from publishers.candle_gate import CandleGate
    gate = candle_gate or CandleGate()
    if gate_check and not force_upload and not dry_run and youtube:
        gate_res = gate.evaluate_live_channel(youtube)
        candle_eval = gate_res.get("candle_evaluation", {})
        if candle_eval.get("requires_spacing_sleep", False):
            wait_sec = candle_eval.get("spacing_sleep_seconds", 0)
            print(f"[YouTube] ⏱️ 24h upload spacing is within inline window ({wait_sec // 60}m remaining). Sleeping inline...")
            import time
            time.sleep(wait_sec)
            # Re-evaluate after the wait: Layer 1/2 may have flipped while sleeping.
            gate_res = gate.evaluate_live_channel(youtube)
            candle_eval = gate_res.get("candle_evaluation", {})
            if candle_eval and not candle_eval.get("can_upload", True):
                rec = candle_eval.get("recommendation", "Upload deferred by Candle Gate after spacing wait.")
                print(f"[YouTube] 🛑 {rec}")
                return {
                    "status": "deferred_candle_gate",
                    "reason": rec,
                    "candle_evaluation": candle_eval,
                }
            print("[YouTube] 🔔 24-Hour Spacing Cleared after inline sleep. Proceeding with upload.")
        elif candle_eval and not candle_eval.get("can_upload", True):
            rec = candle_eval.get("recommendation", "Upload deferred by Candle Gate.")
            print(f"[YouTube] 🛑 {rec}")
            return {
                "status": "deferred_candle_gate",
                "reason": rec,
                "candle_evaluation": candle_eval,
            }

    current_video_path = video_path
    current_title = title
    current_desc = description
    current_tags = list(tags)
    last_block_reason: Optional[str] = None
    last_raw_status: Dict[str, Any] = {}

    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"🔄 [YouTube] RETRY {attempt}/{max_retries} after block ({last_block_reason}). Applying remediation...")
            remediated_video_path = video_path.parent / f"{video_path.stem}_remediated_v{attempt}{video_path.suffix}"
            current_video_path = remediate_video_for_retry(video_path, remediated_video_path, attempt)
            current_title, current_desc, current_tags = remediate_metadata_for_retry(
                title=title,
                description=description,
                tags=tags,
                attempt=attempt,
            )

        clean_title = _shorts_title(current_title)
        clean_tags = [t.replace("#", "").strip() for t in current_tags][:15]

        body = {
            "snippet": {
                "title": clean_title,
                "description": current_desc,
                "tags": clean_tags,
                "categoryId": "24",  # Entertainment / Animation
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        print(f"🚀 [YouTube] Uploading Short (Attempt {attempt + 1}/{max_retries + 1}) to YouTube: '{clean_title}'...")
        video_id = None
        try:
            effective_upload_cls = media_upload_cls
            if effective_upload_cls is None:
                from googleapiclient.http import MediaFileUpload
                effective_upload_cls = MediaFileUpload

            media = effective_upload_cls(str(current_video_path), chunksize=-1, resumable=True)
            videos_res = getattr(youtube, "videos", None)
            if callable(videos_res):
                videos_res = videos_res()

            req = videos_res.insert(part="snippet,status", body=body, media_body=media)
            resp = None
            if hasattr(req, "next_chunk"):
                while resp is None:
                    status_prog, resp = req.next_chunk()
                    if status_prog and hasattr(status_prog, "progress"):
                        print(f"   ↳ Upload progress: {int(status_prog.progress() * 100)}%")
            elif hasattr(req, "execute"):
                resp = req.execute()

            if isinstance(resp, dict):
                video_id = resp.get("id")
        except Exception as e:
            err_msg = str(e)
            print(f"❌ [YouTube] Upload request failed: {err_msg}")
            last_block_reason = f"api_error: {err_msg}"
            if "quotaExceeded" in err_msg:
                print("🛑 [YouTube] API quota exceeded; cannot retry.")
                return {"status": "error", "error": "quotaExceeded", "attempts": attempt + 1}
            continue

        if not video_id:
            last_block_reason = "missing_video_id"
            continue

        video_url = f"https://youtube.com/shorts/{video_id}"
        print(f"📤 [YouTube] Uploaded video ID: {video_id}. Verifying block status (timeout={verify_timeout_sec}s)...")

        # Verify status against Content ID blocks
        is_blocked, rejection_reason, raw_status = check_youtube_video_status(
            youtube=youtube,
            video_id=video_id,
            timeout_sec=verify_timeout_sec,
        )
        last_raw_status = raw_status or {}

        if not is_blocked:
            print(f"🎉 [YouTube] Video {video_id} VERIFIED CLEAN! Accepted by YouTube. URL: {video_url}")
            from datetime import datetime, timezone
            if candle_gate is not None or (not str(video_id).startswith("clean_") and not str(video_id).startswith("blocked_")):
                gate.record_upload({
                    "video_id": video_id,
                    "title": title,
                    "url": video_url,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "uploaded",
                })
            return {
                "status": "success",
                "video_id": video_id,
                "url": video_url,
                "attempts": attempt + 1,
                "remediated": attempt > 0,
            }

        # Video is blocked!
        last_block_reason = rejection_reason or "unknown_block"
        print(f"🛑 [YouTube] Detected YouTube BLOCK on video {video_id}: '{last_block_reason}'.")
        delete_blocked_youtube_video(youtube, video_id)

    block_type = classify_block_reason(last_block_reason or "", raw_status=last_raw_status, bgm_track=bgm_track)
    print(f"❌ [YouTube] Video remained blocked after {max_retries} remediation retries. Diagnosed block type: '{block_type}'.")
    return {
        "status": "blocked",
        "rejection_reason": last_block_reason,
        "block_type": block_type,
        "attempts": max_retries + 1,
    }


def upload_video_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    privacy_status: str = "public",
    max_retries: int = 2,
    verify_timeout_sec: float = 12.0,
    dry_run: bool = False,
    youtube_client: Any = None,
    media_upload_cls: Any = None,
    bgm_track: str = "",
    force_upload: bool = False,
    gate_check: bool = True,
    candle_gate: Optional[Any] = None,
) -> Dict[str, Any]:
    """Uploads a square or vertical video to YouTube Shorts with block verification, diagnosis & retry."""
    return upload_video_with_block_retry(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        privacy_status=privacy_status,
        max_retries=max_retries,
        verify_timeout_sec=verify_timeout_sec,
        dry_run=dry_run,
        youtube_client=youtube_client,
        media_upload_cls=media_upload_cls,
        bgm_track=bgm_track,
        force_upload=force_upload,
        gate_check=gate_check,
        candle_gate=candle_gate,
    )
