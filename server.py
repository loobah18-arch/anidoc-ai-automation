"""
Lightweight Backend Web Server for AniDoc AI Automation Studio
Serves the responsive web UI and exposes REST endpoints to trigger pipeline states
and automatic YouTube uploading.
"""

import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config import settings
from core.pipeline import AniDocPipeline
from publishers.youtube_publisher import YouTubePublisher
from main import extract_titles_and_desc

PORT = 8080

class AniDocWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR / "web"), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/projects"):
            self._handle_list_projects()
        elif self.path.startswith("/output/"):
            file_rel = self.path[len("/output/"):]
            target_path = BASE_DIR / "output" / file_rel
            if target_path.exists() and target_path.is_file():
                self.send_response(200)
                if str(target_path).endswith(".mp4"):
                    self.send_header("Content-Type", "video/mp4")
                elif str(target_path).endswith(".mp3"):
                    self.send_header("Content-Type", "audio/mpeg")
                elif str(target_path).endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                elif str(target_path).endswith(".jpg"):
                    self.send_header("Content-Type", "image/jpeg")
                else:
                    self.send_header("Content-Type", "text/plain")
                self.end_headers()
                with open(target_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(body) if body else {}

        if self.path == "/api/generate-topics":
            self._handle_generate_topics(data)
        elif self.path == "/api/run-pipeline":
            self._handle_run_pipeline(data)
        elif self.path == "/api/render-media":
            self._handle_render_media(data)
        elif self.path == "/api/upload-youtube":
            self._handle_upload_youtube(data)
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_generate_topics(self, data):
        lang = data.get("language", "Hindi")
        pipeline = AniDocPipeline(language=lang)
        topics = pipeline.run_state1_topics()
        self._send_json({"status": "success", "topics": topics})

    def _handle_run_pipeline(self, data):
        topic = data.get("topic", "Covert Espionage Mission 1971")
        lang = data.get("language", "Hindi")
        pipeline = AniDocPipeline(language=lang)
        
        script = pipeline.run_state2_script(topic)
        image_prompts = pipeline.run_state3_image_prompts()
        motion = pipeline.run_state4_motion_prompts()
        thumbs = pipeline.run_state5_thumbnails()
        seo = pipeline.run_state6_seo()

        self._send_json({
            "status": "success",
            "project_name": pipeline.project_name,
            "script": script,
            "image_prompts": image_prompts,
            "motion_prompts": motion,
            "thumbnail_concepts": thumbs,
            "seo_package": seo
        })

    def _handle_render_media(self, data):
        project_name = data.get("project_name")
        pipeline = AniDocPipeline(project_name=project_name)
        res = pipeline.render_complete_media(max_images=data.get("max_images", 4))
        self._send_json({"status": "success", "media": res})

    def _handle_upload_youtube(self, data):
        project_name = data.get("project_name")
        privacy = data.get("privacy", "public")
        proj_dir = settings.OUTPUT_DIR / project_name
        
        video_path = proj_dir / "final_documentary.mp4"
        thumb_path = proj_dir / "thumbnail.jpg"
        seo_file = proj_dir / "06_seo_package.txt"
        
        seo_text = ""
        if seo_file.exists():
            with open(seo_file, "r", encoding="utf-8") as f:
                seo_text = f.read()

        title, desc, tags = extract_titles_and_desc(seo_text, project_name)
        publisher = YouTubePublisher()
        res = publisher.upload_video(
            video_path=str(video_path),
            title=title,
            description=desc,
            tags=tags,
            thumbnail_path=str(thumb_path),
            privacy_status=privacy,
            topic_name=project_name
        )
        self._send_json({"status": "success", "upload": res})

    def _handle_list_projects(self):
        projects = []
        if settings.OUTPUT_DIR.exists():
            for p in settings.OUTPUT_DIR.iterdir():
                if p.is_dir():
                    projects.append(p.name)
        self._send_json({"projects": projects})

    def _send_json(self, payload):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, AniDocWebHandler)
    print(f"============================================================")
    print(f"   AniDoc AI Studio Web Dashboard Started!                  ")
    print(f"   URL: http://localhost:{PORT}                            ")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    run_server()
