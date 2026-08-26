"""SQLite storage for Lookbook Studio."""
from __future__ import annotations

import sqlite3
import time

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS personas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    age          INTEGER,
    traits_json  TEXT,
    face_path    TEXT,
    fullbody_path TEXT,
    thumb_path   TEXT,
    portrait_path TEXT,                 -- 3-view reference portrait (actor sheet)
    tpose_path   TEXT,                  -- full-body T-pose reference (actor sheet)
    gallery_json TEXT,                  -- list of extra shots (photoshoot variations)
    created_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS wardrobe_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT,
    product_id    TEXT,                 -- marketplace product id (for dedupe)
    slot          TEXT,                 -- top/bottom/outerwear/footwear/headwear/accessory
    source        TEXT,                 -- aliexpress/temu/manual
    source_url    TEXT,
    affiliate_url TEXT,
    price         REAL,
    currency      TEXT,
    rating        REAL,
    orders        INTEGER,
    packshot_path TEXT,
    cutout_path   TEXT,
    reference_frame_path TEXT,
    attributes_json TEXT,               -- vision output (V1)
    starred       INTEGER DEFAULT 1,
    created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS wardrobe_variants (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id  INTEGER NOT NULL,
    kind     TEXT,                      -- color/size
    value    TEXT,
    sku      TEXT,
    price    REAL,
    FOREIGN KEY(item_id) REFERENCES wardrobe_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lookbooks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT,
    persona_id     INTEGER,
    status         TEXT DEFAULT 'draft',
    collage_path   TEXT,
    collage_engine TEXT,                -- flatlay/hybrid/full_ai
    model_shot_path TEXT,               -- accepted try-on (model wearing the outfit)
    post_text      TEXT,
    export_dir     TEXT,
    created_at     REAL NOT NULL,
    FOREIGN KEY(persona_id) REFERENCES personas(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS lookbook_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lookbook_id INTEGER NOT NULL,
    item_id     INTEGER NOT NULL,
    role        TEXT DEFAULT 'on_model',   -- on_model/collage_only
    tryon_path  TEXT,
    FOREIGN KEY(lookbook_id) REFERENCES lookbooks(id) ON DELETE CASCADE,
    FOREIGN KEY(item_id) REFERENCES wardrobe_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS saved_links (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    url              TEXT NOT NULL,
    shortcode        TEXT,
    source           TEXT,             -- instagram/pinterest
    poster_thumb_url TEXT,
    media_path       TEXT,             -- local cache, disposable
    status           TEXT DEFAULT 'saved',  -- saved/downloaded
    created_at       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_frames (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id       INTEGER,
    frame_path    TEXT NOT NULL,
    sent_to_vision INTEGER DEFAULT 0,
    created_at    REAL NOT NULL,
    FOREIGN KEY(link_id) REFERENCES saved_links(id) ON DELETE SET NULL
);
"""


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight additive migrations for DBs created by an earlier schema."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(wardrobe_items)")}
    if "product_id" not in cols:
        conn.execute("ALTER TABLE wardrobe_items ADD COLUMN product_id TEXT")
    lcols = {r["name"] for r in conn.execute("PRAGMA table_info(lookbooks)")}
    if "model_shot_path" not in lcols:
        conn.execute("ALTER TABLE lookbooks ADD COLUMN model_shot_path TEXT")
    pcols = {r["name"] for r in conn.execute("PRAGMA table_info(personas)")}
    for col in ("portrait_path", "tpose_path", "gallery_json"):
        if col not in pcols:
            conn.execute(f"ALTER TABLE personas ADD COLUMN {col} TEXT")


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def now() -> float:
    return time.time()
