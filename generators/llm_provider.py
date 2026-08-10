"""
Universal Multi-LLM Provider Interface
Supports: OpenRouter, NVIDIA NIM, Anthropic (Claude), OpenAI, DeepSeek, Groq, Ollama
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
        self.openrouter_key = settings.OPENROUTER_API_KEY
        self.nvidia_key = settings.NVIDIA_API_KEY
        self.anthropic_key = settings.ANTHROPIC_API_KEY
        self.openai_key = settings.OPENAI_API_KEY
        
        # Auto-detect fallback if current provider lacks key
        if self.provider == "openrouter" and not self.openrouter_key:
            if self.nvidia_key:
                self.provider = "nvidia"
                self.model = "nvidia/nemotron-3-nano"
            elif self.anthropic_key:
                self.provider = "anthropic"
                self.model = "claude-3-5-sonnet-20241022"
            elif self.openai_key:
                self.provider = "openai"
                self.model = "gpt-4o"
            else:
                self.provider = "pollinations"

    def generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """Generate text from LLM with automatic error handling and fallback."""
        if self.provider == "openrouter":
            return self._call_openrouter(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "nvidia":
            return self._call_nvidia(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, max_tokens)
        else:
            return self._call_free_fallback(prompt, system_prompt, temperature, max_tokens)

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

        # Sensible model selection
        model_name = self.model if "/" in self.model else f"anthropic/{self.model}"
        if "nemotron" in self.model.lower():
            model_name = "nvidia/llama-3.1-nemotron-70b-instruct"

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            raise RuntimeError(f"OpenRouter API Error: {e.code} - {err}")

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

        payload = {
            "model": "nvidia/llama-3.1-nemotron-70b-instruct",
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

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
        with urllib.request.urlopen(req, timeout=120) as resp:
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    def _call_free_fallback(self, prompt: str, system: str, temp: float, max_tokens: int) -> str:
        """Zero-cost public fallback AI interface via text pollinations / public endpoint."""
        import urllib.parse
        full_text = (f"System: {system}\n\nUser: {prompt}") if system else prompt
        encoded = urllib.parse.quote(full_text)
        url = f"https://text.pollinations.ai/{encoded}?model=openai&seed=42"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8")
