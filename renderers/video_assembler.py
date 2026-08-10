"""
Automated Video Assembler Engine
Stitches animated 2D clips, synchronizes narration voiceover, mixes ambient suspense BGM,
and exports high-definition 1080p documentary video with optional hardcoded subtitles.
"""

import os
import subprocess
from pathlib import Path
from typing import List

class VideoAssembler:
    def __init__(self, output_width=1920, output_height=1080, fps=30):
        self.output_width = output_width
        self.output_height = output_height
        self.fps = fps

    def get_media_duration(self, file_path: str) -> float:
        """Retrieves exact duration in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            return float(res.stdout.strip())
        except Exception:
            return 10.0

    def assemble(self, clip_paths: List[str], audio_path: str, output_video_path: str, subtitle_path: str = None, bgm_path: str = None) -> str:
        """
        Assembles complete documentary video.
        - clip_paths: List of .mp4 animated clips
        - audio_path: Path to voiceover .mp3
        - output_video_path: Target .mp4 file path
        - subtitle_path: Optional .srt or .ass file
        - bgm_path: Optional background suspense music track
        """
        output_video_path = Path(output_video_path)
        output_video_path.parent.mkdir(exist_ok=True, parents=True)
        
        audio_duration = self.get_media_duration(audio_path)
        
        # 1. Create a concat list for all video clips
        concat_list_file = output_video_path.parent / "clips_concat.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                f.write(f"file '{Path(clip).resolve()}'\n")

        # 2. Concat all clips into a unified visual track
        merged_video = output_video_path.parent / "temp_merged_video.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(merged_video)
        ]
        subprocess.run(cmd_concat, capture_output=True)

        # 3. Final audio/video mixing with FFmpeg
        # Loop video if clips are shorter than audio, trim to exact audio duration
        cmd_final = ["ffmpeg", "-y"]
        
        # Input 0: Visuals (stream looped if needed)
        cmd_final += ["-stream_loop", "-1", "-i", str(merged_video)]
        
        # Input 1: Voiceover Audio
        cmd_final += ["-i", str(audio_path)]
        
        # Input 2: Background Music (if provided)
        if bgm_path and Path(bgm_path).exists():
            cmd_final += ["-stream_loop", "-1", "-i", str(bgm_path)]
            # Mix voiceover (100%) and BGM (12% volume)
            audio_filter = "[1:a]volume=1.0[voice];[2:a]volume=0.12[bgm];[voice][bgm]amix=inputs=2:duration=first[aout]"
            cmd_final += ["-filter_complex", audio_filter, "-map", "0:v", "-map", "[aout]"]
        else:
            cmd_final += ["-map", "0:v", "-map", "1:a"]

        # Subtitle burning filter
        video_filters = []
        if subtitle_path and Path(subtitle_path).exists():
            # Escape path for ffmpeg filter
            sub_escaped = str(Path(subtitle_path).resolve()).replace(":", "\\:").replace("\\", "/")
            video_filters.append(f"subtitles='{sub_escaped}'")

        if video_filters:
            cmd_final += ["-vf", ",".join(video_filters)]

        cmd_final += [
            "-t", str(audio_duration),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_video_path)
        ]

        print(f"Rendering final documentary video to {output_video_path}...")
        res = subprocess.run(cmd_final, capture_output=True, text=True)
        
        # Cleanup temp files
        if concat_list_file.exists(): concat_list_file.unlink()
        if merged_video.exists(): merged_video.unlink()

        if res.returncode != 0 and not output_video_path.exists():
            raise RuntimeError(f"Video assembly failed: {res.stderr}")

        return str(output_video_path)
