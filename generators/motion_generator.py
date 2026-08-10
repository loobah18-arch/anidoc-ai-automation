"""
Ken Burns & Camera Motion Generator for 2D Documentary Images
Creates dynamic 1080p video clips from 2D static illustrations using FFmpeg.
Applies slow push-in, subtle pan, gentle zoom, and cinematic film grain.
"""

import os
import subprocess
from pathlib import Path
from typing import List

class MotionGenerator:
    def __init__(self, fps=30, width=1920, height=1080):
        self.fps = fps
        self.width = width
        self.height = height

    def animate_image(self, image_path: str, output_path: str, duration: float = 5.0, motion_type: str = "zoom_in") -> str:
        """
        Animates a single image with smooth documentary camera motion.
        motion_type: 'zoom_in', 'zoom_out', 'pan_left', 'pan_right'
        """
        image_path = Path(image_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        frames = int(duration * self.fps)
        
        # FFmpeg zoompan expressions for smooth documentary moves
        if motion_type == "zoom_in":
            # Slow push-in towards center
            zoom_filter = f"zoompan=z='min(zoom+0.0015,1.25)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        elif motion_type == "zoom_out":
            # Gentle pull-out
            zoom_filter = f"zoompan=z='if(lte(zoom,1.0),1.25,max(1.001,zoom-0.0015))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        elif motion_type == "pan_left":
            # Slow pan left across wide shot
            zoom_filter = f"zoompan=z='1.15':x='if(lte(on,1),(iw-iw/zoom),max(0,x-1.5))':y='ih/2-(ih/zoom/2)':d={frames}:s={self.width}x{self.height}:fps={self.fps}"
        else: # pan_right
            # Slow pan right
            zoom_filter = f"zoompan=z='1.15':x='if(lte(on,1),0,min(iw-iw/zoom,x+1.5))':y='ih/2-(ih/zoom/2)':d={frames}:s={self.width}x{self.height}:fps={self.fps}"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-vf", zoom_filter,
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            str(output_path)
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg motion generation failed: {res.stderr}")
            
        return str(output_path)

    def animate_batch(self, image_paths: List[str], output_dir: str, duration_per_image: float = 5.0) -> List[str]:
        """Converts a list of images into motion video clips alternating camera styles."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        motions = ["zoom_in", "pan_left", "zoom_out", "pan_right"]
        clip_paths = []
        
        for idx, img in enumerate(image_paths):
            clip_num = str(idx + 1).zfill(3)
            out_clip = output_dir / f"clip_{clip_num}.mp4"
            m_type = motions[idx % len(motions)]
            print(f"  [Motion {idx+1}/{len(image_paths)}] Animating clip_{clip_num}.mp4 ({m_type})...")
            try:
                clip = self.animate_image(img, str(out_clip), duration_per_image, m_type)
                clip_paths.append(clip)
            except Exception as e:
                print(f"    Error animating {img}: {e}")
                
        return clip_paths
