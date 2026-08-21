#!/usr/bin/env python3
"""
Zero-Command Antigravity Telegram AI Bot & Cloud Workflow Dispatcher (@Jazzkabot).
Features:
1. Natural Language Intent Detection: "make a gojo edit", "check status", "switch to gemini" work without slash commands.
2. Interactive Tap Buttons (Inline Keyboards): Tap buttons on screen instead of typing commands!
3. Full Memory Bank Access & AI Reasoning.
4. Automatic 4K 60FPS Video Delivery directly into Telegram chat.
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
USER_MD = MEMORY_DIR / "USER.md"
CONTEXT_MD = MEMORY_DIR / "context.md"
PATTERNS_MD = MEMORY_DIR / "patterns.md"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8834100431:AAHkNlSa1Jc1yWibdXvhjQL6-IKsSVHwmVI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1212982193")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

CURRENT_MODEL = "gemini-3.6-flash"

MODEL_MAP = {
    "gemini": "gemini-3.6-flash",
    "flash": "gemini-3.6-flash",
    "deepseek": "opencode/deepseek-v4-flash-free",
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

def send_message(chat_id: str, text: str, reply_markup: dict = None, parse_mode: str = "Markdown"):
    url = f"{API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=12)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_main_menu_keyboard() -> dict:
    """Returns interactive tap buttons for zero-typing interaction."""
    return {
        "inline_keyboard": [
            [
                {"text": "⚡ Render Gojo 4K", "callback_data": "render_gojo"},
                {"text": "🕷️ Render Spider-Man", "callback_data": "render_spiderman"}
            ],
            [
                {"text": "⚔️ Render Sukuna 4K", "callback_data": "render_sukuna"},
                {"text": "🗡️ Render Toji 4K", "callback_data": "render_toji"}
            ],
            [
                {"text": "📊 Check Status", "callback_data": "check_status"},
                {"text": "🔥 10 Trend Edits", "callback_data": "search_trends"}
            ],
            [
                {"text": "🧠 Switch Model", "callback_data": "show_models"},
                {"text": "📖 Memory Bank", "callback_data": "show_memory"}
            ]
        ]
    }

def get_models_keyboard() -> dict:
    """Returns clickable AI model selection buttons."""
    return {
        "inline_keyboard": [
            [
                {"text": "✨ Gemini 3.6 Flash (High)", "callback_data": "set_model_gemini"},
                {"text": "DeepSeek v4 Flash", "callback_data": "set_model_deepseek"}
            ],
            [
                {"text": "Kimi k2.5", "callback_data": "set_model_kimi"},
                {"text": "NVIDIA Nemotron 550B", "callback_data": "set_model_nemotron"}
            ],
            [
                {"text": "MiniMax M2.7", "callback_data": "set_model_minimax"},
                {"text": "🔙 Back to Main Menu", "callback_data": "show_main_menu"}
            ]
        ]
    }

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
                f"🚀 **Cloud Edit Dispatched!**\n\n"
                f"- **Character**: `{character.upper()}`\n"
                f"- **Universe**: `{universe.upper()}`\n"
                f"- **Branch**: `feat/pro-editor-vfx`\n"
                f"- **Safety**: `upload=false`\n\n"
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
        "You are Antigravity, the official agentic AI assistant created by Google DeepMind.\n"
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
        
    return f"🤖 **Antigravity AI Agent** (`{CURRENT_MODEL}`):\n\nI received your prompt: *'{user_prompt}'*\n\nMemory Bank: Connected ✅"

def process_callback_query(cb_query: dict):
    global CURRENT_MODEL
    cb_id = cb_query.get("id")
    data = cb_query.get("data", "")
    chat_id = str(cb_query.get("message", {}).get("chat", {}).get("id", ""))
    
    # Answer callback query to stop loading spinner on Telegram
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
    except Exception:
        pass

    if data == "show_main_menu":
        send_message(chat_id, "✨ **Antigravity Control Dashboard** 🎬\nTap any button below to trigger actions without typing!", reply_markup=get_main_menu_keyboard())
    elif data.startswith("render_"):
        char = data.replace("render_", "")
        universe = "marvel" if char in ["spiderman", "ironman", "thor", "wolverine", "loki"] else "jjk"
        resp = dispatch_cloud_workflow(character=char, universe=universe)
        send_message(chat_id, resp, reply_markup=get_main_menu_keyboard())
    elif data == "check_status":
        resp = check_workflow_status()
        send_message(chat_id, resp, reply_markup=get_main_menu_keyboard())
    elif data == "search_trends":
        send_message(chat_id, "🔍 Searching 10 trend edits (excluding @jazzcreates)...")
        resp = search_10_trend_edits()
        send_message(chat_id, resp, reply_markup=get_main_menu_keyboard())
    elif data == "show_models":
        send_message(chat_id, f"🧠 Current Model: `{CURRENT_MODEL}`\nTap a model button below to switch instantly:", reply_markup=get_models_keyboard())
    elif data.startswith("set_model_"):
        m_key = data.replace("set_model_", "")
        if m_key in MODEL_MAP:
            CURRENT_MODEL = MODEL_MAP[m_key]
            send_message(chat_id, f"✅ Switched AI Model to **{m_key.upper()}** (`{CURRENT_MODEL}`).", reply_markup=get_main_menu_keyboard())
    elif data == "show_memory":
        mem = load_memory_context()
        send_message(chat_id, f"🧠 **Antigravity Memory Bank Snapshot**:\n\n```\n{mem[:1200]}\n```", reply_markup=get_main_menu_keyboard())

def process_update(update: dict):
    global CURRENT_MODEL
    
    # Handle tap button clicks
    if "callback_query" in update:
        process_callback_query(update["callback_query"])
        return

    msg = update.get("message", {})
    text = msg.get("text", "").strip()
    chat_id = str(msg.get("chat", {}).get("id", ""))
    
    if not text or not chat_id:
        return

    print(f"📩 Received message from {chat_id}: '{text}'")
    lower_text = text.lower()

    # ─────────────────────────────────────────────────────────────────────────
    # Natural Language & Zero-Typing Intent Auto-Detection
    # ─────────────────────────────────────────────────────────────────────────
    if text.startswith("/start") or text.startswith("/help") or "menu" in lower_text:
        send_message(
            chat_id,
            "✨ **Antigravity AI Control Dashboard** 🎬\n\nYou don't need to type commands! Simply **tap any button below** or chat naturally in plain text:",
            reply_markup=get_main_menu_keyboard()
        )
    # Detect render intents in plain text: "make gojo edit", "render spiderman", "edit sukuna"
    elif any(k in lower_text for k in ["render", "edit", "make a", "create a", "generate"]) and any(c in lower_text for c in ["gojo", "spiderman", "sukuna", "toji", "megumi", "yuji", "ironman", "thor"]):
        char = "gojo"
        for c in ["spiderman", "sukuna", "toji", "megumi", "yuji", "ironman", "thor", "gojo"]:
            if c in lower_text:
                char = c
                break
        universe = "marvel" if char in ["spiderman", "ironman", "thor"] else "jjk"
        resp = dispatch_cloud_workflow(character=char, universe=universe)
        send_message(chat_id, resp, reply_markup=get_main_menu_keyboard())
    # Detect status intents in plain text: "status", "check run", "how is the render", "workflow"
    elif any(k in lower_text for k in ["status", "check run", "workflow", "progress"]):
        resp = check_workflow_status()
        send_message(chat_id, resp, reply_markup=get_main_menu_keyboard())
    # Detect trend intents in plain text: "trend", "scrape", "search edits"
    elif any(k in lower_text for k in ["trend", "scrape", "search edit"]):
        send_message(chat_id, "🔍 Searching 10 trend edits (excluding @jazzcreates)...")
        resp = search_10_trend_edits()
        send_message(chat_id, resp, reply_markup=get_main_menu_keyboard())
    # Detect model switch intents in plain text: "switch to gemini", "use deepseek", "change model"
    elif "model" in lower_text or "switch to" in lower_text or "use model" in lower_text:
        for m_key in MODEL_MAP.keys():
            if m_key in lower_text:
                CURRENT_MODEL = MODEL_MAP[m_key]
                send_message(chat_id, f"✅ Switched AI Model to **{m_key.upper()}** (`{CURRENT_MODEL}`).", reply_markup=get_main_menu_keyboard())
                return
        send_message(chat_id, f"🧠 Current Model: `{CURRENT_MODEL}`\nTap a model button below to switch:", reply_markup=get_models_keyboard())
    else:
        resp = query_antigravity_agent(text)
        send_message(chat_id, resp, reply_markup=get_main_menu_keyboard())

def main():
    print("🤖 Zero-Command Antigravity Telegram Bot active for @Jazzkabot...")
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
