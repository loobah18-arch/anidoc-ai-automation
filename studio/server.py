#!/usr/bin/env python3
"""
AniDoc Studio - Modern Web Video Editing & Publishing Suite for 4K Shorts.
Runs a zero-dependency local HTTP/REST server for editing, rendering, and publishing Shorts.
"""
import os
import sys
import json
import mimetypes
import threading
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import (
    OUTPUT_DIR, ASSETS_DIR, PHONK_DIR, MARVEL_DIR, JJK_DIR, CC_PRESETS
)
from core.clip_manager import CHARACTER_THEMES, list_available_character_clips
from core.phonk_manager import (
    list_available_phonk_tracks,
    download_phonk_track,
    POPULAR_PHONK_CATALOG
)
from core.subtitle_stylizer import SUBTITLE_STYLE_PRESETS
from core.public_api_fetcher import fetch_character_scenepack, fetch_from_github_repo
from core.quote_ai import generate_edit_metadata
from core.video_assembler import render_cinematic_edit
from publishers.youtube_publisher import upload_video_to_youtube

TEMPLATES_DIR = BASE_DIR / "studio" / "templates"
STATIC_DIR = BASE_DIR / "studio" / "static"

# Track render status
RENDER_STATE = {
    "is_rendering": False,
    "progress": 0,
    "status_message": "Ready",
    "last_result": None,
    "error": None
}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class AniDocStudioHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and disable aggressive caching for local dynamic editing
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Main Studio UI
        if path == "/" or path == "/index.html":
            index_file = TEMPLATES_DIR / "index.html"
            if index_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(index_file, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Template index.html not found")
                return

        # 2. REST API Endpoints
        if path == "/api/status":
            self.send_json_response({
                "render_state": RENDER_STATE,
                "characters": CHARACTER_THEMES,
                "phonk_tracks": list_available_phonk_tracks(),
                "popular_phonk_catalog": POPULAR_PHONK_CATALOG,
                "subtitle_styles": list(SUBTITLE_STYLE_PRESETS.keys()),
                "cc_presets": list(CC_PRESETS.keys()),
                "outputs": self.get_output_videos()
            })
            return

        if path == "/api/characters":
            self.send_json_response({"characters": CHARACTER_THEMES})
            return

        if path == "/api/phonk":
            self.send_json_response({
                "available": list_available_phonk_tracks(),
                "catalog": POPULAR_PHONK_CATALOG
            })
            return

        if path == "/api/clips":
            clips = list_available_character_clips()
            self.send_json_response({"clips": clips})
            return

        if path == "/api/outputs":
            self.send_json_response({"outputs": self.get_output_videos()})
            return

        # 3. Static Media Streaming (Videos, Audios)
        if path.startswith("/media/"):
            rel_path = path[len("/media/"):]
            file_path = BASE_DIR / rel_path
            self.stream_media_file(file_path)
            return

        # Fallback to normal static files
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read JSON body
        content_len = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_len > 0:
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except Exception:
                body = {}

        # 1. Trigger Video Render
        if path == "/api/render":
            if RENDER_STATE["is_rendering"]:
                self.send_json_response({"error": "Render already in progress"}, status=400)
                return

            def run_render():
                global RENDER_STATE
                RENDER_STATE["is_rendering"] = True
                RENDER_STATE["progress"] = 10
                RENDER_STATE["status_message"] = "Initializing render pipeline..."
                RENDER_STATE["error"] = None
                
                try:
                    char_key = body.get("character", "gojo")
                    duration = float(body.get("duration", 15.0))
                    phonk = body.get("phonk_track")
                    sub_style = body.get("subtitle_style", "viral_karaoke")
                    quote = body.get("custom_quote")
                    title = body.get("custom_title")
                    cc = body.get("cc_preset")
                    repo = body.get("github_repo")
                    
                    RENDER_STATE["progress"] = 30
                    RENDER_STATE["status_message"] = f"Sourcing clips & audio for {char_key.upper()}..."
                    
                    res = render_cinematic_edit(
                        character_key=char_key,
                        phonk_track=phonk,
                        target_duration=duration,
                        subtitle_style=sub_style,
                        custom_quote=quote,
                        custom_title=title,
                        cc_preset=cc,
                        github_repo=repo,
                        auto_fetch_clips=True
                    )
                    
                    RENDER_STATE["progress"] = 100
                    RENDER_STATE["status_message"] = "Render Complete!"
                    RENDER_STATE["last_result"] = {
                        "filename": res["output_path"].name,
                        "rel_path": f"output/{res['output_path'].name}",
                        "duration": res["duration"],
                        "cuts_count": res["cuts_count"],
                        "file_size_kb": res["file_size_kb"],
                        "metadata": res["metadata"]
                    }
                except Exception as e:
                    RENDER_STATE["error"] = str(e)
                    RENDER_STATE["status_message"] = f"Render failed: {e}"
                finally:
                    RENDER_STATE["is_rendering"] = False

            threading.Thread(target=run_render, daemon=True).start()
            self.send_json_response({"status": "started", "message": "Render job queued"})
            return

        # 2. Generate AI Quote
        if path == "/api/generate_quote":
            char_key = body.get("character", "spiderman")
            meta = generate_edit_metadata(char_key)
            self.send_json_response({"quote": meta["quote"], "title": meta["title"], "tags": meta["tags"]})
            return

        # 3. Download Phonk Track
        if path == "/api/download_phonk":
            track_id = body.get("track_id", "custom_phonk")
            query = body.get("query")
            
            def run_dl():
                download_phonk_track(track_id, query)
                
            threading.Thread(target=run_dl, daemon=True).start()
            self.send_json_response({"status": "started", "message": f"Downloading {track_id}..."})
            return

        # 4. Fetch Clips from GitHub or Public Streamer
        if path == "/api/fetch_clips":
            char_key = body.get("character", "gojo")
            repo = body.get("github_repo")
            url = body.get("url")
            
            def run_fetch():
                if repo:
                    dest_dir = MARVEL_DIR if CHARACTER_THEMES.get(char_key, {}).get("universe") == "marvel" else JJK_DIR
                    fetch_from_github_repo(repo, dest_dir, character_filter=char_key)
                else:
                    fetch_character_scenepack(char_key, custom_query_or_url=url, max_clips=8)
                    
            threading.Thread(target=run_fetch, daemon=True).start()
            self.send_json_response({"status": "started", "message": f"Fetching clips for {char_key}..."})
            return

        # 5. YouTube Shorts Direct Upload
        if path == "/api/upload_youtube":
            filename = body.get("filename")
            title = body.get("title", "4K Phonk Edit #shorts")
            desc = body.get("description", "Automated 4K Edit Short")
            tags = body.get("tags", ["shorts", "4kedit", "phonk"])
            privacy = body.get("privacy", "public")
            
            if not filename:
                self.send_json_response({"error": "No filename provided"}, status=400)
                return
                
            video_path = OUTPUT_DIR / filename
            if not video_path.exists():
                self.send_json_response({"error": f"Video {filename} not found in output/"}, status=404)
                return
                
            res = upload_video_to_youtube(
                video_path=video_path,
                title=title,
                description=desc,
                tags=tags,
                privacy_status=privacy
            )
            self.send_json_response(res)
            return

        self.send_error(404, "Endpoint not found")

    def send_json_response(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def get_output_videos(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        videos = []
        for v in sorted(OUTPUT_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True):
            videos.append({
                "filename": v.name,
                "rel_path": f"output/{v.name}",
                "size_kb": v.stat().st_size // 1024,
                "modified": os.path.getmtime(v)
            })
        return videos

    def stream_media_file(self, file_path: Path):
        """Streams a local video or audio file with Byte-Range support for smooth HTML5 playback."""
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, f"File not found: {file_path.name}")
            return
            
        file_size = file_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        range_header = self.headers.get("Range")
        if range_header:
            # Parse Range: bytes=start-end
            bytes_range = range_header.replace("bytes=", "").split("-")
            start = int(bytes_range[0])
            end = int(bytes_range[1]) if bytes_range[1] else file_size - 1
            length = end - start + 1

            self.send_response(206)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with open(file_path, "rb") as f:
                f.seek(start)
                self.wfile.write(f.read(length))
        else:
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with open(file_path, "rb") as f:
                self.wfile.write(f.read())


def start_studio_server(host: str = "127.0.0.1", port: int = 7860):
    """Starts the AniDoc Studio web editing server."""
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, AniDocStudioHandler)
    url = f"http://{host}:{port}"
    print(f"\n=======================================================")
    print(f"🎬 [AniDoc Studio] Video Editor & Shorts Publisher Active!")
    print(f"🌐 Access Studio UI: {url}")
    print(f"⚡ Press Ctrl+C to stop server")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down AniDoc Studio Server...")
        httpd.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AniDoc Studio Web Video Editor Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Port number (default: 7860)")
    args = parser.parse_args()
    start_studio_server(args.host, args.port)
