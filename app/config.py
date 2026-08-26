"""Configuration & filesystem paths for Lookbook Studio.

Secrets (API keys) live in `config.json` at the project root (gitignored), with
environment-variable fallback. Model-registry defaults live in `app/ai/registry.py`;
`config.json -> model_choices` only overrides the multi-option calls.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # lookbook-studio/
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons" / "tabler"

# Per-feature media folders (created on demand)
PERSONAS_DIR = DATA_DIR / "personas"
WARDROBE_DIR = DATA_DIR / "wardrobe"
CUTOUTS_DIR = DATA_DIR / "cutouts"
TRYON_DIR = DATA_DIR / "tryon"
COLLAGE_DIR = DATA_DIR / "collage"
EXPORT_DIR = DATA_DIR / "exports"
CACHE_DIR = DATA_DIR / "cache"          # downloaded reels/media — disposable
FRAMES_DIR = DATA_DIR / "frames"
DB_PATH = DATA_DIR / "lookbook.sqlite3"

_CONFIG_PATH = ROOT / "config.json"

_ALL_DIRS = (
    DATA_DIR, PERSONAS_DIR, WARDROBE_DIR, CUTOUTS_DIR, TRYON_DIR,
    COLLAGE_DIR, EXPORT_DIR, CACHE_DIR, FRAMES_DIR, ICONS_DIR,
)


def ensure_dirs() -> None:
    for d in _ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


class Config:
    def __init__(self, data: dict):
        self._d = data

    @classmethod
    def load(cls) -> "Config":
        data: dict = {}
        if _CONFIG_PATH.exists():
            try:
                data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
        return cls(data)

    def save(self) -> None:
        _CONFIG_PATH.write_text(
            json.dumps(self._d, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # --- secrets: config.json first, then environment ---
    @property
    def openrouter_api_key(self) -> str:
        return self._d.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")

    @property
    def replicate_api_token(self) -> str:
        return self._d.get("replicate_api_token") or os.environ.get("REPLICATE_API_TOKEN", "")

    @property
    def aliexpress(self) -> dict:
        return self._d.get("aliexpress", {})

    @property
    def model_choices(self) -> dict:
        return self._d.get("model_choices", {})

    def set_model_choice(self, call_id: str, model: str) -> None:
        """Persist the chosen model for an AI operation (per-operation selector)."""
        self._d.setdefault("model_choices", {})[call_id] = model
        self.save()

    def set_secrets(self, data: dict) -> None:
        """Persist API keys edited in the in-app Settings dialog."""
        for k in ("openrouter_api_key", "replicate_api_token"):
            if k in data:
                self._d[k] = data[k]
        if "aliexpress" in data:
            self._d["aliexpress"] = {**self._d.get("aliexpress", {}), **data["aliexpress"]}
        if "telegram" in data:
            self._d["telegram"] = {**self._d.get("telegram", {}), **data["telegram"]}
        self.save()

    @property
    def theme(self) -> str:
        return self._d.get("theme", "midnight")

    def set_theme(self, name: str) -> None:
        self._d["theme"] = name
        self.save()

    def get(self, key, default=None):
        return self._d.get(key, default)


CONFIG = Config.load()
