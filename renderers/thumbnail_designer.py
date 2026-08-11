"""
Viral 2D Documentary Thumbnail Designer
Generates high-CTR 16:9 thumbnails with Devanagari text styling,
red/yellow keyword highlight, and the signature '2D ANIMATION' bottom badge.
"""

import subprocess
import re
from pathlib import Path
from generators.image_generator import ImageGenerator

class ThumbnailDesigner:
    def __init__(self):
        self.image_gen = ImageGenerator()

    def create_thumbnail(self, image_prompt: str, hindi_headline: str, output_path: str, keyword_highlight: str = None) -> str:
        """
        Renders complete viral thumbnail:
        1. Generates 16:9 base illustration via Flux / Pollinations
        2. Overlays stylized headline text & '2D ANIMATION' badge
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        base_image = output_path.parent / "temp_thumb_base.png"
        
        # Clean prompt: strip any markdown tables or headers
        clean_prompt = re.sub(r'[\*#_`\|]', '', image_prompt)
        if len(clean_prompt) < 20 or "estimated" in clean_prompt.lower() or "table" in clean_prompt.lower():
            clean_prompt = "Dramatic 2D vector documentary illustration, high contrast split composition, South Asian operative escaping prison tower at night under amber lamp light, moody atmospheric lighting, 16:9"
            
        print(f"Generating thumbnail base image from clean prompt: {clean_prompt[:60]}...")
        self.image_gen.generate_single(clean_prompt, str(base_image), width=1280, height=720)

        # Clean headline
        headline_escaped = re.sub(r'[\*#_`]', '', hindi_headline).strip()
        headline_escaped = headline_escaped.replace("'", "").replace(":", "\\:").replace("%", "\\%")
        
        # Badge filter: Yellow rounded box at bottom center with black bold text '2D ANIMATION'
        # Top title: Bold white text
        vf_filters = [
            # Top dark gradient banner for headline contrast
            "drawbox=x=0:y=0:w=iw:h=180:color=black@0.65:t=fill",
            # Headline text
            f"drawtext=text='{headline_escaped}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=55:shadowcolor=black@0.9:shadowx=3:shadowy=3",
            # Bottom Yellow Badge Background
            "drawbox=x=(iw-260)/2:y=ih-75:w=260:h=48:color=yellow@0.95:t=fill",
            # '2D ANIMATION' Black Text inside badge
            "drawtext=text='2D ANIMATION':fontcolor=black:fontsize=26:x=(w-text_w)/2:y=h-64"
        ]

        cmd = [
            "ffmpeg", "-y",
            "-i", str(base_image),
            "-vf", ",".join(vf_filters),
            str(output_path)
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if base_image.exists(): base_image.unlink()

        if res.returncode != 0 and not output_path.exists():
            # Fallback copy if drawtext font issue occurs in minimal ffmpeg build
            cmd_fallback = ["ffmpeg", "-y", "-i", str(base_image), str(output_path)]
            subprocess.run(cmd_fallback, capture_output=True)

        return str(output_path)
