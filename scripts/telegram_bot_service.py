#!/usr/bin/env python3
"""
Full-Memory Antigravity AI Assistant & Cloud Workflow Dispatcher for Telegram (@Jazzkabot).
Directly connects to OpenCode / Shared Memory Bank (~/.config/opencode/memory/):
- USER.md (Authoritative rules & preferences)
- context.md (Current project state & active runs)
- patterns.md (Editing guidelines & lessons learned)
- Session logs (Timestamped session RECAP entries)
"""
import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = Path("/data/data/com.termux/files/home/.config/opencode/memory")
USER_MD = MEMORY_DIR / "USER.md"
CONTEXT_MD = MEMORY_DIR / "context.md"
PATTERNS_MD = MEMORY_DIR / "patterns.md"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8834100431:AAHkNlSa1Jc1yWibdXvhjQL6-IKsSVHwmVI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1212982193")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def load_memory_context() -> str:
    """Dynamically loads shared OpenCode/Antigravity Memory Bank."""
    memory_text = ""
    if USER_MD.exists():
        try:
            memory_text += f"--- USER PREFERENCES & RULES ---\n{USER_MD.read_text()}\n\n"
        except Exception:
            pass
    if CONTEXT_MD.exists():
        try:
            memory_text += f"--- CURRENT PROJECT STATE & CONTEXT ---\n{CONTEXT_MD.read_text()}\n\n"
        except Exception:
            pass
    if PATTERNS_MD.exists():
        try:
            memory_text += f"--- PATTERNS & LESSONS LEARNED ---\n{PATTERNS_MD.read_text()}\n\n"
        except Exception:
            pass
    return memory_text

def send_message(chat_id: str, text: str, parse_mode: str = "Markdown"):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        requests.post(url, json=payload, timeout=10)
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
            return f"🚀 Dispatched **{character.upper()}** ({universe.upper()}) 4K 60FPS Cloud Workflow to GitHub Actions!\nOutput video will be delivered directly to this Telegram chat upon completion. 🎬"
        else:
            return f"⚠️ Workflow dispatch notice: {proc.stderr}"
    except Exception as e:
        return f"⚠️ Failed to dispatch workflow: {e}"

def check_workflow_status() -> str:
    cmd = ["gh", "run", "list", "-R", "loobah18-arch/anidoc-ai-automation", "--limit", "4"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return f"📊 **GitHub Actions Workflow Status**:\n```\n{proc.stdout.strip()}\n```"
    except Exception as e:
        return f"⚠️ Status check error: {e}"

CURRENT_MODEL = "opencode/deepseek-v4-flash-free"

MODEL_MAP = {
    "deepseek": "opencode/deepseek-v4-flash-free",
    "gemini": "gemini-2.0-flash",
    "kimi": "bai/kimi-k2.5",
    "nemotron": "nvidia/nemotron-3-ultra",
    "minimax": "minimax-m2.7"
}

def query_antigravity_llm(user_prompt: str) -> str:
    """Queries selected LLM model with full Memory Bank context."""
    global CURRENT_MODEL
    memory_bank = load_memory_context()
    sys_prompt = (
        "You are Antigravity, a powerful agentic AI assistant pair programming with Jasper (@Sanguin06).\n"
        "You have FULL access to the OpenCode Memory Bank below, including all rules, preferences, reference video priorities, and project state.\n"
        "Always follow these rules strictly:\n"
        "1. NEVER use references from @jazzcreates.\n"
        "2. ALL video renders MUST be executed in the cloud on GitHub Actions (zero phone rendering).\n"
        "3. Main Priority Reference: Gojo Attitude Status by @Chakra_boy.\n"
        "4. Be concise, direct, helpful, and friendly.\n\n"
        f"{memory_bank}"
    )
    
    cmd = [
        "/data/data/com.termux/files/home/.opencode/bin/opencode", "run",
        "-m", CURRENT_MODEL,
        f"{sys_prompt}\n\nUser Question: {user_prompt}"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
        
    return f"🤖 **Antigravity AI** (Model: `{CURRENT_MODEL}`):\n\n{user_prompt}\n\n*(Use /model to switch AI models, or /render to dispatch cloud edits!)*"

def process_update(update: dict):
    global CURRENT_MODEL
    msg = update.get("message", {})
    text = msg.get("text", "").strip()
    chat_id = str(msg.get("chat", {}).get("id", ""))
    
    if not text or not chat_id:
        return

    print(f"📩 Received message from {chat_id}: '{text}'")

    if text.startswith("/start"):
        send_message(chat_id, "✨ **Antigravity AI Assistant & Cloud Edit Dispatcher** 🎬\n\nI have **FULL memory access** to your project context, rules, and reference preferences!\n\nCommands:\n- `/render <character>` — Render 4K Short in Cloud\n- `/status` — View Cloud Workflow Runs\n- `/model <name>` — Switch AI Model (deepseek, gemini, kimi, nemotron, minimax)\n- Or ask me any question directly!")
    elif text.startswith("/model"):
        parts = text.split()
        if len(parts) > 1 and parts[1].lower() in MODEL_MAP:
            m_key = parts[1].lower()
            CURRENT_MODEL = MODEL_MAP[m_key]
            send_message(chat_id, f"✅ Switched AI Model to **{m_key.upper()}** (`{CURRENT_MODEL}`).")
        else:
            avail = ", ".join([f"`{k}`" for k in MODEL_MAP.keys()])
            send_message(chat_id, f"🧠 Current Model: `{CURRENT_MODEL}`\n\nTo switch models, use:\n`/model <name>`\nAvailable models: {avail}")
    elif text.startswith("/render"):
        parts = text.split()
        char = parts[1].lower() if len(parts) > 1 else "gojo"
        universe = "marvel" if char in ["spiderman", "ironman", "thor", "wolverine", "loki"] else "jjk"
        resp = dispatch_cloud_workflow(character=char, universe=universe)
        send_message(chat_id, resp)
    elif text.startswith("/status"):
        resp = check_workflow_status()
        send_message(chat_id, resp)
    else:
        resp = query_antigravity_llm(text)
        send_message(chat_id, resp)


def main():
    print("🤖 Full-Memory Antigravity Telegram Bot Service started for @Jazzkabot...")
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
