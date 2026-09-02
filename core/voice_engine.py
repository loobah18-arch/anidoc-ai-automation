"""
Neural Voice Synthesis & Dialogue Isolation Engine for Marvel & Anime Edits.
Uses real character audio clips or Microsoft Edge Natural Neural TTS with word-level sync.
"""
import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from config.settings import DIALOGUE_DIR, SCRATCH_DIR

CHARACTER_VOICES = {
    "spiderman": {"voice": "en-US-GuyNeural", "rate": "+4%", "pitch": "+2Hz"},
    "ironman":   {"voice": "en-US-ChristopherNeural", "rate": "+0%", "pitch": "-1Hz"},
    "thor":      {"voice": "en-US-RogerNeural", "rate": "-2%", "pitch": "-4Hz"},
    "thanos":    {"voice": "en-US-RogerNeural", "rate": "-8%", "pitch": "-8Hz"},
    "wolverine": {"voice": "en-US-EricNeural", "rate": "-3%", "pitch": "-5Hz"},
    "loki":      {"voice": "en-US-BrianNeural", "rate": "+0%", "pitch": "-2Hz"},
    "gojo":      {"voice": "en-US-BrianNeural", "rate": "+2%", "pitch": "+0Hz"},
    "sukuna":    {"voice": "en-US-EricNeural", "rate": "-5%", "pitch": "-6Hz"},
    "toji":      {"voice": "en-US-ChristopherNeural", "rate": "-3%", "pitch": "-4Hz"},
    "yuji":      {"voice": "en-US-GuyNeural", "rate": "+3%", "pitch": "+1Hz"},
    "megumi":    {"voice": "en-US-BrianNeural", "rate": "-1%", "pitch": "-2Hz"}
}


async def _synthesize_edge_tts(text: str, voice_cfg: Dict[str, str], output_path: Path) -> Path:
    """Synthesizes text using edge-tts async API. Streams MP3 → pipes to FFmpeg → writes WAV.
    No intermediate MP3 file on disk."""
    import edge_tts
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_cfg["voice"],
        rate=voice_cfg.get("rate", "+0%"),
        pitch=voice_cfg.get("pitch", "+0Hz")
    )

    # Collect MP3 chunks in memory
    mp3_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_chunks.append(chunk["data"])
    mp3_data = b"".join(mp3_chunks)

    # Pipe MP3 → WAV via FFmpeg (no temp MP3 on disk)
    cmd = [
        "ffmpeg", "-y",
        "-i", "pipe:0",
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
        str(output_path)
    ]
    proc = subprocess.run(cmd, input=mp3_data, capture_output=True, check=True)
    return output_path


def get_character_dialogue_audio(
    character_key: str,
    quote_text: str,
    output_path: Optional[Path] = None
) -> Path:
    """
    Returns high-quality dialogue audio for the intro phase:
    1. Checks for curated movie clip audio in assets/audio/dialogue/
    2. Otherwise synthesizes high-fidelity Neural TTS matching the quote.
    """
    DIALOGUE_DIR.mkdir(parents=True, exist_ok=True)
    if not output_path:
        output_path = SCRATCH_DIR / f"dialogue_{character_key}.mp3"
        
    # Check for curated character voice file
    curated_files = list(DIALOGUE_DIR.glob(f"{character_key}*.mp3"))
    if curated_files:
        print(f"🎙️ Using curated character dialogue audio: {curated_files[0].name}")
        return curated_files[0]
        
    # Synthesize Neural Voice
    voice_cfg = CHARACTER_VOICES.get(character_key, CHARACTER_VOICES["gojo"])
    print(f"🎙️ Synthesizing Neural Voiceover ({voice_cfg['voice']}) for: \"{quote_text}\"...")
    
    try:
        asyncio.run(_synthesize_edge_tts(quote_text, voice_cfg, output_path))
        if output_path.exists() and output_path.stat().st_size > 1000:
            return output_path
    except Exception as e:
        print(f"⚠️ Edge-TTS notice: {e}. Generating procedural voice tone.")
        
    # Fallback to procedural synth tone if TTS network unavailable
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=220:d=3.5",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path
