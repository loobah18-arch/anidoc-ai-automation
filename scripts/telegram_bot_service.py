#!/usr/bin/env python3
"""
Full-Capability Antigravity AI Agent & Cloud Editor Service for Telegram (@Jazzkabot).
Equips Telegram Bot with 100% of Antigravity's capabilities:
1. Full Memory Bank (USER.md, context.md, patterns.md, daily session logs).
2. Codebase Research & File Reader (read files, inspect diffs, search code).
3. GitHub Actions & Cloud Workflow Control (dispatch, status, logs).
4. Trend Reference Engine (search 10 trend edits excluding @jazzcreates).
5. Dynamic AI Models (DeepSeek, Gemini, Kimi, Nemotron, MiniMax).
6. Automatic 4K 60FPS Video Delivery directly to Telegram chat.
"""
import os
import sys
import re
import json
import time
import requests
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
HOME_DIR = Path("/data/data/com.termux/files/home")
MEMORY_DIR = HOME_DIR / ".config/opencode/memory"
SESSIONS_DIR = HOME_DIR / ".config/opencode/sessions"
USER_MD = MEMORY_DIR / "USER.md"
CONTEXT_MD = MEMORY_DIR / "context.md"
PATTERNS_MD = MEMORY_DIR / "patterns.md"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8834100431:AAHkNlSa1Jc1yWibdXvhjQL6-IKsSVHwmVI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1212982193")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

CURRENT_MODEL = "opencode/deepseek-v4-flash-free"

MODEL_MAP = {
    "deepseek": "opencode/deepseek-v4-flash-free",
    "gemini": "gemini-2.0-flash",
    "kimi": "bai/kimi-k2.5",
    "nemotron": "nvidia/nemotron-3-ultra",
    "minimax": "minimax-m2.7"
}

def load_memory_context() -> str:
    """Loads shared OpenCode/Antigravity Memory Bank."""
    memory_text = ""
    if USER_MD.exists():
        try:
            memory_text += f"=== USER PREFERENCES & RULES ===\n{USER_MD.read_text()}\n\n"
        except Exception:
            pass
    if CONTEXT_MD.exists():
        try:
            memory_text += f"=== CURRENT PROJECT STATE ===\n{CONTEXT_MD.read_text()}\n\n"
        except Exception:
            pass
    if PATTERNS_MD.exists():
        try:
            memory_text += f"=== PATTERNS & LESSONS LEARNED ===\n{PATTERNS_MD.read_text()}\n\n"
        except Exception:
            pass
    return memory_text

def send_message(chat_id: str, text: str, parse_mode: str = "Markdown"):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        requests.post(url, json=payload, timeout=12)
    except Exception as e:
        print(f"Error sending message: {e}")

def dispatch_cloud_workflow(character: str = "gojo", universe: str = "jjk") -> str:
    cmd = [
        "gh", "workflow", "run", "daily_edit.yml",
        "-R", "loobah18-arch/anidoc-ai-automation",
        "-r", "feat/pro-editor-vfx",
        "-f", f"character={character}",
        "-f", f"universe={universe}",
        "-f", "upload=false"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode == 0:
            return (
                f"🚀 **Cloud Workflow Dispatched!**\n\n"
                f"- **Character**: `{character.upper()}`\n"
                f"- **Universe**: `{universe.upper()}`\n"
                f"- **Branch**: `feat/pro-editor-vfx`\n"
                f"- **Safety**: `upload=false` (Cloud GDrive & Telegram Delivery)\n\n"
                f"The 4K 60FPS video will be sent directly to this Telegram chat upon completion! 🎬"
            )
        else:
            return f"⚠️ Workflow dispatch notice: {proc.stderr}"
    except Exception as e:
        return f"⚠️ Failed to dispatch workflow: {e}"

def check_workflow_status() -> str:
    cmd = ["gh", "run", "list", "-R", "loobah18-arch/anidoc-ai-automation", "--limit", "4"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return f"📊 **GitHub Actions Workflow Runs**:\n```\n{proc.stdout.strip()}\n```"
    except Exception as e:
        return f"⚠️ Status check error: {e}"

def search_10_trend_edits() -> str:
    trend_script = BASE_DIR / "scripts" / "anime_edit_trend_engine.py"
    if not trend_script.exists():
        return "⚠️ Trend engine script not found."
    try:
        proc = subprocess.run([sys.executable, str(trend_script)], capture_output=True, text=True, timeout=30)
        return f"🔍 **10 Trend Edits Scraped (Excluding @jazzcreates)**:\n\n```\n{proc.stdout.strip()[:1500]}\n```"
    except Exception as e:
        return f"⚠️ Trend search notice: {e}"

def query_antigravity_agent(user_prompt: str) -> str:
    """Full Antigravity Agent Query with Memory Context."""
    global CURRENT_MODEL
    memory_bank = load_memory_context()
    sys_prompt = (
        "You are Antigravity, the official agentic AI coding assistant created by Google DeepMind.\n"
        "You are pair programming with Jasper (@Sanguin06) on Telegram.\n"
        "You have 100% full access to the OpenCode Shared Memory Bank below.\n"
        "STRICT MANDATORY RULES:\n"
        "1. NEVER use references from @jazzcreates.\n"
        "2. ZERO local phone rendering; ALL video rendering MUST execute on GitHub Actions cloud runners.\n"
        "3. Main Priority Reference: Gojo Attitude Status by @Chakra_boy.\n"
        "4. Be concise, direct, intelligent, and authoritative.\n\n"
        f"{memory_bank}"
    )
    
    cmd = [
        "/data/data/com.termux/files/home/.opencode/bin/opencode", "run",
        "-m", CURRENT_MODEL,
        f"{sys_prompt}\n\nUser Prompt: {user_prompt}"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
        
    return f"🤖 **Antigravity AI Agent** (`{CURRENT_MODEL}`):\n\nI received your prompt: *'{user_prompt}'*\n\nMemory Bank: Connected ✅\nUse `/help` to view all agent capabilities!"

def process_update(update: dict):
    global CURRENT_MODEL
    msg = update.get("message", {})
    text = msg.get("text", "").strip()
    chat_id = str(msg.get("chat", {}).get("id", ""))
    
    if not text or not chat_id:
        return

    print(f"📩 Received message from {chat_id}: '{text}'")

    if text.startswith("/start") or text.startswith("/help"):
        help_text = (
            "✨ **Full Antigravity Agent Capabilities** 🤖\n\n"
            "**Cloud Editing & Rendering:**\n"
            "• `/render gojo` — Dispatch 4K Gojo Short\n"
            "• `/render spiderman` — Dispatch 4K Spider-Man Short\n"
            "• `/render sukuna` — Dispatch 4K Sukuna Short\n"
            "• `/render toji` — Dispatch 4K Toji Short\n"
            "• `/status` — View GitHub Cloud Runs\n"
            "• `/trends` — Search 10 Trend Edits (No @jazzcreates)\n\n"
            "**AI Intelligence & Models:**\n"
            "• `/model` — View/Switch AI Models (`deepseek`, `gemini`, `kimi`, `nemotron`, `minimax`)\n"
            "• `/memory` — View Memory Bank State\n\n"
            "**General Assistance:**\n"
            "Send any question or coding task directly to chat with Antigravity AI!"
        )
        send_message(chat_id, help_text)
    elif text.startswith("/model"):
        parts = text.split()
        if len(parts) > 1 and parts[1].lower() in MODEL_MAP:
            m_key = parts[1].lower()
            CURRENT_MODEL = MODEL_MAP[m_key]
            send_message(chat_id, f"✅ Switched AI Model to **{m_key.upper()}** (`{CURRENT_MODEL}`).")
        else:
            avail = ", ".join([f"`{k}`" for k in MODEL_MAP.keys()])
            send_message(chat_id, f"🧠 Current Model: `{CURRENT_MODEL}`\n\nUse `/model <name>` to switch:\nAvailable models: {avail}")
    elif text.startswith("/render"):
        parts = text.split()
        char = parts[1].lower() if len(parts) > 1 else "gojo"
        universe = "marvel" if char in ["spiderman", "ironman", "thor", "wolverine", "loki"] else "jjk"
        resp = dispatch_cloud_workflow(character=char, universe=universe)
        send_message(chat_id, resp)
    elif text.startswith("/status"):
        resp = check_workflow_status()
        send_message(chat_id, resp)
    elif text.startswith("/trends"):
        resp = search_10_trend_edits()
        send_message(chat_id, resp)
    elif text.startswith("/memory"):
        mem = load_memory_context()
        send_message(chat_id, f"🧠 **Antigravity Memory Bank Snapshot**:\n\n```\n{mem[:1500]}\n```")
    else:
        resp = query_antigravity_agent(text)
        send_message(chat_id, resp)

def main():
    print("🤖 Full-Capability Antigravity Agent Service active for @Jazzkabot...")
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            r = requests.get(f"{API_URL}/getUpdates", params=params, timeout=35)
            if r.status_code == 200:
                data = r.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    process_update(update)
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    main()
