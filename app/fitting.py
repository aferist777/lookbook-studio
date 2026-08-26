"""Try-on orchestration (worker-thread safe).

ensure_cutout: packshot -> background-removed cutout (U1), cached on the wardrobe item.
run_tryon: persona full-body anchor -> layered try-on (top -> bottom -> shoes, G5/G6/G7),
each step feeding the next. Returns the final model-wearing-the-outfit image path.
Every model call is logged automatically (goes through ai.service).
"""
from __future__ import annotations

from pathlib import Path

from . import config, db, wardrobe
from .ai import service

# order matters: outer layers applied after inner ones
SLOT_ORDER = {"top": 0, "outerwear": 1, "bottom": 2, "footwear": 3, "headwear": 4, "accessory": 5}


def ensure_cutout(item: dict) -> str | None:
    """Return a background-removed cutout path for the item, creating + caching it if needed."""
    existing = item.get("cutout_path")
    if existing and Path(existing).exists():
        return existing
    packshot = item.get("packshot_path")
    if not packshot or not Path(packshot).exists():
        return packshot
    out = service.remove_background(packshot)
    dest = config.CUTOUTS_DIR / f"cutout_{item.get('id') or 'x'}_{int(db.now() * 1000)}.png"
    path = service.materialize_image(out, dest)
    if item.get("id"):
        wardrobe.set_cutout(item["id"], path)
        item["cutout_path"] = path
    return path


def run_tryon(persona_fullbody: str, on_model_items: list[dict]) -> str:
    """Layer the on-model items onto the persona anchor and return the final image path."""
    if not persona_fullbody or not Path(persona_fullbody).exists():
        raise RuntimeError("Persona has no full-body anchor — generate one in the Personas tab first.")
    ordered = sorted(on_model_items, key=lambda it: SLOT_ORDER.get(it.get("slot") or "top", 9))
    base = persona_fullbody
    for item in ordered:
        slot = item.get("slot") or "top"
        garment = ensure_cutout(item) or item.get("packshot_path")
        if not garment:
            continue
        out = service.tryon(base, garment, slot, item.get("title", ""))
        dest = config.TRYON_DIR / f"step_{int(db.now() * 1000)}.png"
        base = service.materialize_image(out, dest)
    return base


def run_batch(persona_fullbody: str, on_model_items: list[dict], n: int) -> list[str]:
    """Generate n independent try-on passes; return the list of final image paths."""
    results = []
    for _ in range(max(1, n)):
        results.append(run_tryon(persona_fullbody, on_model_items))
    return results
