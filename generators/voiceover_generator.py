"""
Voiceover Generator Module
Supports:
1. Microsoft Edge Neural TTS (100% Free, Unlimited, ultra-realistic Hindi & English)
2. ElevenLabs API (Multi-lingual v2 documentary voices)
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from config import settings

class VoiceoverGenerator:
    def __init__(self, provider=None):
        self.provider = provider or settings.DEFAULT_TTS_PROVIDER
        self.elevenlabs_key = settings.ELEVENLABS_API_KEY
        
        # Load voice profiles
        profiles_path = settings.CONFIG_DIR / "voice_profiles.json"
        if profiles_path.exists():
            with open(profiles_path, "r", encoding="utf-8") as f:
                self.profiles = json.load(f)
        else:
            self.profiles = {}

    def generate(self, text: str, output_path: str, language: str = "hindi", voice_type: str = "male") -> str:
        """
        Synthesizes voiceover from clean script text.
        text: Raw narrative text
        output_path: Target mp3 file path
        language: "hindi" or "english"
        voice_type: "male" or "female"
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Clean text of any accidental tags or tension markers
        cleaned_text = self._clean_script(text)
        
        if self.provider == "elevenlabs" and self.elevenlabs_key:
            return self._generate_elevenlabs(cleaned_text, output_path)
        else:
            return self._generate_edge_tts(cleaned_text, output_path, language, voice_type)

    def _clean_script(self, text: str) -> str:
        import re
        # Remove markdown headers, tension peak tags, etc.
        text = re.sub(r'\[TENSION PEAK\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[MUSIC.*?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[SFX.*?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
        return text.strip()

    def _generate_edge_tts(self, text: str, output_path: Path, language: str, voice_type: str) -> str:
        """Generate voice using Microsoft Edge Neural TTS."""
        voice = settings.DEFAULT_HINDI_VOICE_EDGE if language.lower() == "hindi" else settings.DEFAULT_ENGLISH_VOICE_EDGE
        if voice_type == "female" and language.lower() == "hindi":
            voice = "hi-IN-SwaraNeural"
            
        rate = "-4%" # Documentary slow gravitas
        pitch = "-2Hz"

        # Check if edge-tts python package or CLI is available
        try:
            import edge_tts
            async def _run():
                communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
                await communicate.save(str(output_path))
            asyncio.run(_run())
            return str(output_path)
        except ImportError:
            # Fallback to edge-playback or command line if edge-tts CLI is installed
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", str(output_path),
                "--rate", rate,
                "--pitch", pitch
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and output_path.exists():
                return str(output_path)
            
            # If edge-tts not installed, use gTTS or python fallback
            return self._fallback_gtts(text, output_path, language)

    def _fallback_gtts(self, text: str, output_path: Path, language: str) -> str:
        """Lightweight Google Translate TTS fallback."""
        import urllib.parse
        import urllib.request
        
        lang_code = "hi" if language.lower() == "hindi" else "en"
        # Split text into chunks < 200 chars for Google TTS URL
        chunks = [text[i:i+180] for i in range(0, len(text), 180)]
        temp_files = []
        
        for idx, chunk in enumerate(chunks):
            chunk_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(chunk)}&tl={lang_code}&client=tw-ob"
            temp_file = output_path.parent / f"chunk_{idx}.mp3"
            req = urllib.request.Request(chunk_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                with open(temp_file, "wb") as f:
                    f.write(resp.read())
            temp_files.append(temp_file)
            
        # Concatenate using ffmpeg
        list_file = output_path.parent / "audio_concat.txt"
        with open(list_file, "w") as f:
            for tf in temp_files:
                f.write(f"file '{tf.resolve()}'\n")
                
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output_path)], capture_output=True)
        
        # Cleanup
        for tf in temp_files:
            if tf.exists(): tf.unlink()
        if list_file.exists(): list_file.unlink()
        return str(output_path)

    def _generate_elevenlabs(self, text: str, output_path: Path) -> str:
        import urllib.request
        cfg = self.profiles.get("elevenlabs", {})
        voice_id = cfg.get("default_voice_id", "pNInz6obpgDQGcFmaJgB")
        model_id = cfg.get("model_id", "eleven_multilingual_v2")
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.elevenlabs_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": cfg.get("voice_settings", {"stability": 0.55, "similarity_boost": 0.8})
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=180) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
        return str(output_path)
