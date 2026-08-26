"""OpenRouter client (OpenAI-compatible chat completions) for vision + text."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(RuntimeError):
    pass


def _data_url(image_path: str | Path) -> str:
    p = Path(image_path)
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


class OpenRouterClient:
    def __init__(self, api_key: str, timeout: int = 120):
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, model, system, user_text, image_paths=None, json_mode=False) -> str:
        if not self.api_key:
            raise OpenRouterError(
                "OpenRouter API key is not set (config.json -> openrouter_api_key)."
            )
        content: list[dict] = [{"type": "text", "text": user_text}]
        for ip in image_paths or []:
            content.append({"type": "image_url", "image_url": {"url": _data_url(ip)}})

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        payload: dict = {"model": model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Lookbook Studio",
        }
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise OpenRouterError(f"OpenRouter {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]
