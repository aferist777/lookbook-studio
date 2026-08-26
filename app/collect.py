"""Collect data-access + media download (worker-thread safe).

saved_links: references harvested in the browser (links only — the source of truth).
download_media: yt-dlp fetches the media into the disposable cache.
saved_frames: stills picked from a reel, sent to vision (V1) for product search.
"""
from __future__ import annotations

import re

from . import config, db

_SHORT = re.compile(r"/(?:reels?|p|tv)/([^/?#]+)")


def _shortcode(url: str) -> str | None:
    m = _SHORT.search(url or "")
    return m.group(1) if m else None


# ----------------------------------------------------------------- links
def save_link(url: str, source: str, poster_thumb: str | None = None) -> int:
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO saved_links (url, shortcode, source, poster_thumb_url, status, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (url, _shortcode(url), source, poster_thumb, "saved", db.now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_links() -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM saved_links ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_links() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM saved_links").fetchone()["n"]
    finally:
        conn.close()


def set_downloaded(link_id: int, media_path: str) -> None:
    conn = db.connect()
    try:
        conn.execute("UPDATE saved_links SET media_path=?, status='downloaded' WHERE id=?",
                     (media_path, link_id))
        conn.commit()
    finally:
        conn.close()


def delete_link(link_id: int) -> None:
    conn = db.connect()
    try:
        conn.execute("DELETE FROM saved_links WHERE id=?", (link_id,))
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------- frames
def save_frame(link_id, frame_path: str) -> int:
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO saved_frames (link_id, frame_path, sent_to_vision, created_at) VALUES (?,?,0,?)",
            (link_id, frame_path, db.now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_frames() -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM saved_frames ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ----------------------------------------------------------------- download (yt-dlp)
def download_media(url: str, link_id=None) -> str:
    """Download the media for a link into the cache; returns the local file path."""
    try:
        import yt_dlp
    except ImportError as e:
        raise RuntimeError("yt-dlp is not installed (pip install yt-dlp).") from e
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    opts = {
        "outtmpl": str(config.CACHE_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "format": "mp4/bestvideo+bestaudio/best",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    if link_id is not None:
        set_downloaded(link_id, path)
    return path
