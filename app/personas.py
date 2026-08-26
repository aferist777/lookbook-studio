"""Persona data-access layer + generation helpers (worker-thread safe).

Pipeline: TPDNE face seed -> (optional G2 refine / G3 age edit) -> G1 full-body anchor.
The generation wrappers call the AI service and materialise the model output into a
local file, returning its path.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import config, db
from .ai import service


def _save(out, prefix: str) -> str:
    dest = config.PERSONAS_DIR / f"{prefix}_{int(db.now() * 1000)}.png"
    return service.materialize_image(out, dest)


# ----------------------------------------------------------------- generation
def fetch_face() -> str:
    """Roll a new face from thispersondoesnotexist.com → local path."""
    import requests
    r = requests.get(
        "https://thispersondoesnotexist.com/",
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (LookbookStudio)"},
    )
    r.raise_for_status()
    config.PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PERSONAS_DIR / f"face_{int(db.now() * 1000)}.jpg"
    path.write_bytes(r.content)
    return str(path)


def upload_face(src_path: str) -> str:
    """Copy a user-supplied face image into the personas folder → local path."""
    config.PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(src_path).suffix or ".jpg"
    dest = config.PERSONAS_DIR / f"face_{int(db.now() * 1000)}{ext}"
    shutil.copyfile(src_path, dest)
    return str(dest)


def generate_model(params: dict, realism: bool = True) -> str:
    """Parameter-driven text-to-image model image → local path."""
    return _save(service.generate_model(params, realism), "model")


def make_fullbody(face_path: str, traits: dict, realism: bool = True) -> str:
    return _save(service.generate_fullbody(face_path, traits, realism), "body")


def refine_face(image_path: str, instruction: str, realism: bool = True) -> str:
    return _save(service.refine_face(image_path, instruction, realism), "face_refined")


def apply_age(image_path: str, target_age, realism: bool = True) -> str:
    return _save(service.change_age(image_path, target_age, realism), "face_age")


def apply_pose(image_path: str, pose: str, realism: bool = True) -> str:
    return _save(service.apply_pose(image_path, pose, realism), "pose")


def apply_emotion(image_path: str, emotion: str, realism: bool = True) -> str:
    return _save(service.apply_emotion(image_path, emotion, realism), "emotion")


def apply_gender(image_path: str, gender: str, realism: bool = True) -> str:
    return _save(service.apply_gender(image_path, gender, realism), "gender")


def make_pose_variation(image_path: str, pose: str, realism: bool = True) -> str:
    return _save(service.pose_variation(image_path, pose, realism), "shot")


def make_portrait(image_path: str) -> str:
    return _save(service.actor_portrait(image_path), "portrait")


def make_tpose(image_path: str) -> str:
    return _save(service.actor_tpose(image_path), "tpose")


# ----------------------------------------------------------------- DAL
def create(name, age, traits: dict, face_path, fullbody_path) -> int:
    conn = db.connect()
    try:
        cur = conn.execute(
            """INSERT INTO personas (name, age, traits_json, face_path, fullbody_path, thumb_path, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (name, age, json.dumps(traits, ensure_ascii=False), face_path, fullbody_path,
             face_path, db.now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update(persona_id: int, name, age, traits: dict, face_path, fullbody_path) -> None:
    conn = db.connect()
    try:
        conn.execute(
            """UPDATE personas SET name=?, age=?, traits_json=?, face_path=?, fullbody_path=?, thumb_path=?
               WHERE id=?""",
            (name, age, json.dumps(traits, ensure_ascii=False), face_path, fullbody_path,
             face_path, persona_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_all() -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM personas ORDER BY created_at DESC").fetchall()
        return [_row(r) for r in rows]
    finally:
        conn.close()


def get(persona_id: int) -> dict | None:
    conn = db.connect()
    try:
        r = conn.execute("SELECT * FROM personas WHERE id=?", (persona_id,)).fetchone()
        return _row(r) if r else None
    finally:
        conn.close()


def delete(persona_id: int) -> None:
    conn = db.connect()
    try:
        conn.execute("DELETE FROM personas WHERE id=?", (persona_id,))
        conn.commit()
    finally:
        conn.close()


def count() -> int:
    conn = db.connect()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM personas").fetchone()["n"]
    finally:
        conn.close()


def set_sheets(persona_id: int, portrait_path, tpose_path) -> None:
    conn = db.connect()
    try:
        conn.execute("UPDATE personas SET portrait_path=?, tpose_path=? WHERE id=?",
                     (portrait_path, tpose_path, persona_id))
        conn.commit()
    finally:
        conn.close()


def set_gallery(persona_id: int, paths: list) -> None:
    conn = db.connect()
    try:
        conn.execute("UPDATE personas SET gallery_json=? WHERE id=?",
                     (json.dumps(paths, ensure_ascii=False), persona_id))
        conn.commit()
    finally:
        conn.close()


def _row(r) -> dict:
    keys = set(r.keys())

    def g(k):
        return r[k] if k in keys else None

    try:
        traits = json.loads(r["traits_json"]) if r["traits_json"] else {}
    except (json.JSONDecodeError, TypeError):
        traits = {}
    try:
        gallery = json.loads(g("gallery_json")) if g("gallery_json") else []
    except (json.JSONDecodeError, TypeError):
        gallery = []
    return {
        "id": r["id"], "name": r["name"], "age": r["age"], "traits": traits,
        "face_path": r["face_path"], "fullbody_path": r["fullbody_path"], "thumb_path": r["thumb_path"],
        "portrait_path": g("portrait_path"), "tpose_path": g("tpose_path"), "gallery": gallery,
    }
