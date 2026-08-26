"""Lookbook data-access layer (shared by Fitting room [Phase 3] and Lookbook [Phase 4]).

A lookbook = one outfit: a persona, the chosen wardrobe items (on-model or collage-only),
the accepted model shot, and later a collage + post text + export dir.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import config, db

DEFAULT_TEMPLATE = """✨ {persona} — streetwear look ✨

Assemble the fit 👇
{items}

#streetwear #ootd #tomboy #aliexpressfinds"""


def create(persona_id, name: str) -> int:
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO lookbooks (name, persona_id, status, created_at) VALUES (?,?,?,?)",
            (name, persona_id, "draft", db.now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def set_model_shot(lookbook_id: int, path) -> None:
    _set(lookbook_id, "model_shot_path", path)


def update_collage(lookbook_id: int, path, engine) -> None:
    conn = db.connect()
    try:
        conn.execute("UPDATE lookbooks SET collage_path=?, collage_engine=? WHERE id=?",
                     (path, engine, lookbook_id))
        conn.commit()
    finally:
        conn.close()


def update_post(lookbook_id: int, text) -> None:
    _set(lookbook_id, "post_text", text)


def update_export(lookbook_id: int, export_dir) -> None:
    _set(lookbook_id, "export_dir", export_dir)


def _set(lookbook_id: int, col: str, value) -> None:
    conn = db.connect()
    try:
        conn.execute(f"UPDATE lookbooks SET {col}=? WHERE id=?", (value, lookbook_id))
        conn.commit()
    finally:
        conn.close()


def clear_items(lookbook_id: int) -> None:
    conn = db.connect()
    try:
        conn.execute("DELETE FROM lookbook_items WHERE lookbook_id=?", (lookbook_id,))
        conn.commit()
    finally:
        conn.close()


def add_item(lookbook_id: int, item_id: int, role: str = "on_model", tryon_path=None) -> None:
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO lookbook_items (lookbook_id, item_id, role, tryon_path) VALUES (?,?,?,?)",
            (lookbook_id, item_id, role, tryon_path),
        )
        conn.commit()
    finally:
        conn.close()


def count() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM lookbooks").fetchone()["n"]
    finally:
        conn.close()


def list_all() -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute(
            """SELECT l.*, p.name AS persona_name
               FROM lookbooks l LEFT JOIN personas p ON p.id = l.persona_id
               ORDER BY l.created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get(lookbook_id: int) -> dict | None:
    conn = db.connect()
    try:
        r = conn.execute(
            """SELECT l.*, p.name AS persona_name FROM lookbooks l
               LEFT JOIN personas p ON p.id = l.persona_id WHERE l.id=?""",
            (lookbook_id,),
        ).fetchone()
        if not r:
            return None
        lb = dict(r)
        items = conn.execute(
            """SELECT li.role, li.tryon_path, w.*
               FROM lookbook_items li JOIN wardrobe_items w ON w.id = li.item_id
               WHERE li.lookbook_id=?""",
            (lookbook_id,),
        ).fetchall()
        lb["items"] = [dict(it) for it in items]
        return lb
    finally:
        conn.close()


def delete(lookbook_id: int) -> None:
    conn = db.connect()
    try:
        conn.execute("DELETE FROM lookbooks WHERE id=?", (lookbook_id,))
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------- publishing
def render_post(lb: dict, template: str | None = None) -> str:
    persona = lb.get("persona_name") or "model"
    lines = []
    for it in lb.get("items", []):
        price = it.get("price")
        cur = it.get("currency") or ""
        price_s = f"{price:.2f} {cur}".strip() if price is not None else ""
        link = it.get("affiliate_url") or it.get("source_url") or ""
        lines.append(f"• {it.get('title') or 'item'} — {price_s} → {link}".strip())
    items_block = "\n".join(lines)
    return (template or DEFAULT_TEMPLATE).replace("{persona}", persona).replace("{items}", items_block)


def export_package(lb: dict, template: str | None = None) -> str:
    """Write the ready-to-post package (model shot + collage + caption + links) to a folder."""
    out = config.EXPORT_DIR / f"lookbook_{lb['id']}"
    out.mkdir(parents=True, exist_ok=True)
    for src, name in ((lb.get("model_shot_path"), "model.png"), (lb.get("collage_path"), "collage.png")):
        if src and Path(src).exists():
            shutil.copyfile(src, out / name)
    (out / "post.txt").write_text(render_post(lb, template), encoding="utf-8")
    links = [it.get("affiliate_url") or it.get("source_url") or "" for it in lb.get("items", [])]
    (out / "links.txt").write_text("\n".join(l for l in links if l), encoding="utf-8")
    update_export(lb["id"], str(out))
    return str(out)


def post_to_telegram(lb: dict, caption: str) -> bool:
    """Publish the lookbook to a Telegram channel via the Bot API (collage + caption)."""
    import requests
    tg = config.CONFIG.get("telegram", {}) or {}
    token, chat = tg.get("bot_token"), tg.get("channel_id")
    if not (token and chat):
        raise RuntimeError("Set telegram.bot_token and telegram.channel_id in config.json.")
    img = lb.get("collage_path") or lb.get("model_shot_path")
    if img and Path(img).exists():
        with open(img, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                              data={"chat_id": chat, "caption": caption[:1024]},
                              files={"photo": f}, timeout=60)
    else:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": caption[:4096]}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram {r.status_code}: {r.text[:200]}")
    return True
