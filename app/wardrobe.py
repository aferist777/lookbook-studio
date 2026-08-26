"""Wardrobe data-access layer (the hub). Safe to call from worker threads:
each call opens and closes its own SQLite connection.
"""
from __future__ import annotations

from . import config, db


def _download_packshot(url: str | None, product_id: str | None) -> str | None:
    if not url:
        return None
    try:
        import requests
        r = requests.get(url, timeout=20)
        r.raise_for_status()
    except Exception:
        return None
    stamp = int(db.now() * 1000)
    path = config.WARDROBE_DIR / f"{(product_id or 'item')}_{stamp}.jpg"
    config.WARDROBE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return str(path)


def save_result(card: dict) -> int:
    """Persist a search result into the wardrobe; downloads the packshot locally."""
    packshot = _download_packshot(card.get("image") or card.get("image_url"), card.get("product_id"))
    conn = db.connect()
    try:
        cur = conn.execute(
            """INSERT INTO wardrobe_items
               (title, product_id, slot, source, source_url, affiliate_url, price, currency,
                rating, orders, packshot_path, starred, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?)""",
            (card.get("title"), str(card.get("product_id") or ""), card.get("slot"),
             card.get("source", "aliexpress"), card.get("source_url"), card.get("affiliate_url"),
             card.get("price"), card.get("currency"), card.get("rating"), card.get("orders"),
             packshot, db.now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def is_saved(product_id, source="aliexpress") -> bool:
    if not product_id:
        return False
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM wardrobe_items WHERE product_id=? AND source=? LIMIT 1",
            (str(product_id), source),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def delete_by_product(product_id, source="aliexpress") -> None:
    conn = db.connect()
    try:
        conn.execute(
            "DELETE FROM wardrobe_items WHERE product_id=? AND source=?",
            (str(product_id), source),
        )
        conn.commit()
    finally:
        conn.close()


def set_cutout(item_id: int, cutout_path: str) -> None:
    conn = db.connect()
    try:
        conn.execute("UPDATE wardrobe_items SET cutout_path=? WHERE id=?", (cutout_path, item_id))
        conn.commit()
    finally:
        conn.close()


def delete_item(item_id: int) -> None:
    conn = db.connect()
    try:
        conn.execute("DELETE FROM wardrobe_items WHERE id=?", (item_id,))
        conn.commit()
    finally:
        conn.close()


def count_items() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM wardrobe_items").fetchone()["n"]
    finally:
        conn.close()


def list_items(limit: int, offset: int = 0) -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT * FROM wardrobe_items ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [_row_to_card(r) for r in rows]
    finally:
        conn.close()


def _row_to_card(r) -> dict:
    return {
        "id": r["id"],
        "title": r["title"],
        "product_id": r["product_id"],
        "slot": r["slot"],
        "source": r["source"],
        "source_url": r["source_url"],
        "affiliate_url": r["affiliate_url"],
        "price": r["price"],
        "currency": r["currency"],
        "rating": r["rating"],
        "orders": r["orders"],
        "packshot_path": r["packshot_path"],
        "image": None,
    }
