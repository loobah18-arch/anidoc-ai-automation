"""
Universal Multi-LLM Provider Interface with Automatic Failover Waterfall
Supports: OpenRouter, NVIDIA NIM, Anthropic (Claude), OpenAI, DeepSeek, Free Fallback
"""

import os
import json
import urllib.request
import urllib.error
from config import settings

class LLMProvider:
    def __init__(self, provider=None, model=None):
        self.provider = provider or settings.DEFAULT_LLM_PROVIDER
        self.model = model or settings.DEFAULT_LLM_MODEL
        
        # Resolve keys
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY") or settings.OPENROUTER_API_KEY
        self.nvidia_key = os.environ.get("NVIDIA_API_KEY") or settings.NVIDIA_API_KEY
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or settings.ANTHROPIC_API_KEY
        self.openai_key = os.environ.get("OPENAI_API_KEY") or settings.OPENAI_API_KEY

    def generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        Executes LLM generation with automatic multi-tier fallback waterfall:
        Tier 1: OpenRouter (DeepSeek / Claude / Llama 3.3)
        Tier 2: NVIDIA NIM (Nemotron / Llama 3.1 70B)
        Tier 3: Anthropic / OpenAI (if keys present)
        Tier 4: Free Zero-Cost Neural Engine
        """
        errors = []

        # Tier 1: OpenRouter
        if self.openrouter_key:
            try:
                return self._call_openrouter(prompt, system_prompt, temperature, max_tokens)
            except Exception as e:
                print(f"[!] OpenRouter notice ({e}), falling back to Tier 2 (NVIDIA NIM)...")
                errors.append(f"OpenRouter: {e}")

        # Tier 2: NVIDIA NIM
        if self.nvidia_key:
            try:
                return self._call_nvidia(prompt, system_prompt, temperature, max_tokens)
            except Exception as e:
                print(f"[!] NVIDIA NIM notice ({e}), falling back to Tier 3...")
                errors.append(f"NVIDIA: {e}")

        # Tier 3: Anthropic Direct
        if self.anthropic_key:
            try:
                return self._call_anthropic(prompt, system_prompt, temperature, max_tokens)
            except Exception as e:
                errors.append(f"Anthropic: {e}")

        # Tier 4: OpenAI Direct
        if self.openai_key:
            try:
                return self._call_openai(prompt, system_prompt, temperature, max_tokens)
            except Exception as e:
                errors.append(f"OpenAI: {e}")

        # Final Tier: Free Fallback Engine
        print("[!] Using Free Fallback Neural Engine...")
        try:
            return self._call_free_fallback(prompt, system_prompt, temperature, max_tokens)
        except Exception as e:
            errors.append(f"Free Fallback: {e}")
            raise RuntimeError(f"All LLM tiers failed: {'; '.join(errors)}")

    def _call_openrouter(self, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/anidoc-ai-automation",
            "X-Title": "AniDoc AI Automation"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Use widely available standard OpenRouter models
        models_to_try = [
            "deepseek/deepseek-chat",
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-2.0-flash-001",
            "anthropic/claude-3-5-sonnet:beta"
        ]
        if self.model and self.model not in models_to_try:
            models_to_try.insert(0, self.model)

        last_err = None
        for m in models_to_try:
            payload = {
                "model": m,
                "messages": messages,
                "temperature": temp,
                "max_tokens": max_tokens
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                last_err = e.read().decode()
                continue
            except Exception as e:
                last_err = str(e)
                continue

        raise RuntimeError(f"OpenRouter models failed: {last_err}")

    def _call_nvidia(self, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        models = [
            "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "meta/llama-3.3-70b-instruct",
            "mistralai/mixtral-8x22b-instruct-v0.1"
        ]
        for m in models:
            payload = {
                "model": m,
                "messages": messages,
                "temperature": temp,
                "max_tokens": max_tokens
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
            except Exception:
                continue

        raise RuntimeError("NVIDIA NIM endpoints failed")

    def _call_anthropic(self, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model or "claude-3-5-sonnet-20241022",
            "max_tokens": max_tokens,
            "temperature": temp,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system:
            payload["system"] = system
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]

    def _call_openai(self, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model or "gpt-4o",
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    def _call_free_fallback(self, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        """Zero-cost public fallback AI interface."""
        import urllib.parse
        full_text = (f"System: {system}\n\nUser: {prompt}") if system else prompt
        encoded = urllib.parse.quote(full_text[:4000])
        url = f"https://text.pollinations.ai/{encoded}?model=openai&seed=42"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8")
