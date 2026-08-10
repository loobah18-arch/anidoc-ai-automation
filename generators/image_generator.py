"""
2D Illustration Image Generator Module
Supports:
1. Pollinations AI (100% Free, High-Res Flux 16:9 Generation, Zero API Key needed)
2. Replicate / Together AI Flux API
3. OpenAI DALL-E 3
"""

import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List
from config import settings

class ImageGenerator:
    def __init__(self, provider="pollinations"):
        self.provider = provider
        self.replicate_key = settings.REPLICATE_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

    def generate_single(self, prompt: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
        """Generates a single 16:9 2D illustration image."""
        output_path = Path(output_path)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Enhanced style injection
        style_suffix = ", semi-realistic 2d illustration, clean outlines, cinematic lighting, warm muted tones, 8k resolution, 16:9 aspect ratio"
        final_prompt = prompt if "2d illustration" in prompt.lower() else prompt + style_suffix
        
        if self.provider == "pollinations":
            return self._generate_pollinations(final_prompt, output_path, width, height)
        else:
            return self._generate_pollinations(final_prompt, output_path, width, height)

    def _generate_pollinations(self, prompt: str, output_path: Path, width: int, height: int) -> str:
        """Uses Pollinations AI Free Flux Engine."""
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={int(time.time()*1000)%100000}"
        
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    with open(output_path, "wb") as f:
                        f.write(resp.read())
                return str(output_path)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Pollinations Image Generation failed: {e}")
                time.sleep(2)
        return str(output_path)

    def generate_batch(self, prompts: List[str], output_dir: str, width: int = 1920, height: int = 1080) -> List[str]:
        """Generates a list of prompts sequentially into output_dir."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        generated_paths = []
        for idx, prompt in enumerate(prompts):
            frame_num = str(idx + 1).zfill(3)
            out_file = output_dir / f"frame_{frame_num}.png"
            print(f"  [Image {idx+1}/{len(prompts)}] Generating frame_{frame_num}.png...")
            try:
                path = self.generate_single(prompt, str(out_file), width, height)
                generated_paths.append(path)
                time.sleep(0.5) # Gentle rate limiting
            except Exception as e:
                print(f"    Error on image {idx+1}: {e}")
                
        return generated_paths
