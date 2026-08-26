"""Collage builder (worker-thread safe).

Engines: flatlay (template, offline — real cutouts on a neutral canvas), hybrid
(AI background via G9 + real cutouts composited on top), full_ai (deferred to Phase 6).
Real product images are always used for the items, so the collage stays accurate for
the affiliate links.
"""
from __future__ import annotations

import math
from pathlib import Path

from . import config, db, theme
from .ai import service


def _item_paths(lookbook: dict) -> list[str]:
    paths = []
    for it in lookbook.get("items", []):
        p = it.get("cutout_path") or it.get("packshot_path")
        if p and Path(p).exists():
            paths.append(p)
    return paths


def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _grid(canvas, paths, pad=40):
    from PIL import Image
    W, H = canvas.size
    n = len(paths) or 1
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cw = (W - pad * (cols + 1)) // cols
    ch = (H - pad * (rows + 1)) // rows
    for i, p in enumerate(paths):
        try:
            im = Image.open(p).convert("RGBA")
        except Exception:
            continue
        im.thumbnail((cw, ch), Image.LANCZOS)
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad) + (cw - im.width) // 2
        y = pad + r * (ch + pad) + (ch - im.height) // 2
        canvas.alpha_composite(im, (x, y))
    return canvas


def _flatlay(paths, dest, bg_rgb) -> str:
    from PIL import Image
    canvas = Image.new("RGBA", (1080, 1080), bg_rgb + (255,))
    _grid(canvas, paths)
    canvas.convert("RGB").save(dest, "PNG")
    return str(dest)


def _hybrid(paths, bg_path, dest) -> str:
    from PIL import Image
    bg = Image.open(bg_path).convert("RGBA").resize((1080, 1080), Image.LANCZOS)
    _grid(bg, paths)
    bg.convert("RGB").save(dest, "PNG")
    return str(dest)


def _poster(model_path, paths, dest, bg_rgb) -> str:
    """Model hero on the left, item grid on the right — a ready 4:5 post image (offline)."""
    from PIL import Image
    W, H = 1080, 1350
    canvas = Image.new("RGBA", (W, H), bg_rgb + (255,))
    rx = int(W * 0.54)
    if model_path and Path(model_path).exists():
        m = Image.open(model_path).convert("RGBA")
        m.thumbnail((rx - 60, H - 80), Image.LANCZOS)
        canvas.alpha_composite(m, (40, (H - m.height) // 2))
    sub = Image.new("RGBA", (W - rx - 40, H - 80), (0, 0, 0, 0))
    _grid(sub, paths, pad=24)
    canvas.alpha_composite(sub, (rx, 40))
    canvas.convert("RGB").save(dest, "PNG")
    return str(dest)


def build(lookbook: dict, engine: str) -> str:
    paths = _item_paths(lookbook)
    if not paths and engine != "poster":
        raise RuntimeError("No product images to build a collage from.")
    config.COLLAGE_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.COLLAGE_DIR / f"collage_{lookbook['id']}_{int(db.now() * 1000)}.png"
    bg_rgb = _hex_to_rgb(theme.color(config.CONFIG.theme, "surface2"))
    if engine == "hybrid":
        out = service.collage_background()
        bg = service.materialize_image(out, config.COLLAGE_DIR / f"bg_{int(db.now() * 1000)}.png")
        return _hybrid(paths, bg, dest)
    if engine == "poster":
        return _poster(lookbook.get("model_shot_path"), paths, dest, bg_rgb)
    return _flatlay(paths, dest, bg_rgb)
