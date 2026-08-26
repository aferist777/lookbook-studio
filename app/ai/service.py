"""High-level AI service — orchestrates registry + provider clients + prompts.

EVERY call (foreground or background) is logged to ai.log.STORE with its full
Request / Response / Result, provider and content kinds, so the Log panel shows all
traffic and any model errors. Replicate inputs are logged by path (not raw bytes);
output media URLs are kept verbatim so they stay clickable in the log.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config as cfg
from . import prompts
from .log import STORE
from .openrouter import OpenRouterClient
from .registry import REGISTRY, resolve
from .replicate_client import ReplicateClient


def _openrouter() -> OpenRouterClient:
    return OpenRouterClient(cfg.CONFIG.openrouter_api_key)


def _replicate() -> ReplicateClient:
    return ReplicateClient(cfg.CONFIG.replicate_api_token)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        nl = text.find("\n")
        if nl != -1:
            text = text[nl + 1:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        raise


def _stringify(out):
    """Make a Replicate output JSON-friendly, preserving media URLs verbatim."""
    def one(o):
        if isinstance(o, str):
            return o
        url = getattr(o, "url", None)
        return url or str(o)
    if isinstance(out, (list, tuple)):
        return [one(o) for o in out]
    return one(out)


# --------------------------------------------------------------------- logged runners
def _or_logged(call_id, system, user_text, image_paths=None, json_mode=False) -> str:
    model = resolve(call_id, cfg.CONFIG)[1]
    kinds = ["text"] + (["image"] if image_paths else [])
    request = {
        "model": model,
        "json_mode": json_mode,
        "system": system,
        "user_text": user_text,
        "images": [str(p) for p in (image_paths or [])],
    }
    e = STORE.start("OpenRouter", f"{call_id} · {REGISTRY[call_id].note}", model, kinds, request)
    try:
        text = _openrouter().chat(model, system, user_text, image_paths, json_mode)
    except Exception as ex:
        STORE.error(e, str(ex))
        raise
    STORE.finish(e, {"content": text}, text)
    return text


def _rep_logged(call_id, log_input, real_input, kinds):
    model = resolve(call_id, cfg.CONFIG)[1]
    e = STORE.start("Replicate", f"{call_id} · {REGISTRY[call_id].note}", model, kinds,
                    {"model": model, "input": log_input})
    try:
        out = _replicate().run(model, real_input)
    except Exception as ex:
        STORE.error(e, str(ex))
        raise
    s = _stringify(out)
    STORE.finish(e, {"output": s}, s)
    return out


# --------------------------------------------------------------------- Translation (T1)
def translate_to_english(text: str) -> str:
    if not text or not text.strip():
        return text or ""
    return _or_logged("T1", prompts.TRANSLATE_SYSTEM, text.strip())


# --------------------------------------------------------------------- Realism compiler (RC)
def compile_realism(prompt: str) -> str:
    """Enrich an image prompt with phone-camera realism markers (logged as RC)."""
    return _or_logged("RC", prompts.REALISM_SYSTEM, prompt)


def _realize(prompt: str, realism: bool) -> str:
    return compile_realism(prompt) if realism else prompt


# --------------------------------------------------------------------- Vision (OpenRouter)
def analyze_reference(image_path):
    out = _or_logged("V1", prompts.GARMENT_ANALYSIS_SYSTEM, prompts.GARMENT_ANALYSIS_USER,
                     [image_path], json_mode=True)
    return _parse_json(out).get("items", [])


def build_query(attrs: dict) -> str:
    out = _or_logged("V2", prompts.QUERY_BUILDER_SYSTEM, prompts.query_builder_user(attrs))
    return out.strip().strip('"')


def suggest_outfits(items: list[dict]) -> list[dict]:
    out = _or_logged("V3", prompts.STYLIST_SYSTEM,
                     prompts.stylist_user(json.dumps(items, ensure_ascii=False)), json_mode=True)
    return _parse_json(out).get("outfits", [])


# --------------------------------------------------------------------- Image (Replicate)
def _edit(call_id, image_path, prompt, realism):
    prompt = _realize(prompt, realism)
    with open(image_path, "rb") as f:
        return _rep_logged(call_id, {"prompt": prompt, "image": str(image_path)},
                           {"prompt": prompt, "image": f}, ["text", "image"])


def generate_model(params: dict, realism: bool = True):
    """G1 text-to-image from the parameter dropdowns (no face seed)."""
    p = dict(params)
    if p.get("custom"):
        p["custom"] = translate_to_english(p["custom"])
    prompt = _realize(prompts.model_prompt(p), realism)
    return _rep_logged("G1", {"prompt": prompt}, {"prompt": prompt}, ["text"])


def generate_fullbody(face_path, traits: dict, realism: bool = True):
    if traits.get("extra"):
        traits = {**traits, "extra": translate_to_english(traits["extra"])}
    prompt = _realize(prompts.face_to_fullbody_prompt(traits), realism)
    with open(face_path, "rb") as f:
        return _rep_logged("G1", {"prompt": prompt, "image": str(face_path)},
                           {"prompt": prompt, "image": f}, ["text", "image"])


def refine_face(image_path, instruction: str, realism: bool = True):
    return _edit("G2", image_path, prompts.face_refine_prompt(translate_to_english(instruction)), realism)


def change_age(image_path, target_age, realism: bool = True):
    return _edit("G3", image_path, prompts.age_change_prompt(target_age), realism)


def apply_pose(image_path, pose, realism: bool = True):
    return _edit("G2", image_path, prompts.pose_edit_prompt(translate_to_english(pose)), realism)


def apply_emotion(image_path, emotion, realism: bool = True):
    return _edit("G2", image_path, prompts.emotion_edit_prompt(translate_to_english(emotion)), realism)


def apply_gender(image_path, gender, realism: bool = True):
    return _edit("G2", image_path, prompts.gender_edit_prompt(gender), realism)


def pose_variation(image_path, pose, realism: bool = True):
    return _edit("G8", image_path, prompts.pose_variation_prompt(translate_to_english(pose)), realism)


def actor_portrait(image_path):
    return _edit("G4", image_path, prompts.ACTOR_PORTRAIT_PROMPT, realism=False)


def actor_tpose(image_path):
    return _edit("G4", image_path, prompts.ACTOR_TPOSE_PROMPT, realism=False)


def remove_background(image_path):
    with open(image_path, "rb") as f:
        return _rep_logged("U1", {"image": str(image_path)}, {"image": f}, ["image"])


def tryon(model_image, garment_image, slot: str, garment_desc: str = ""):
    call = {"top": "G5", "bottom": "G6", "footwear": "G7"}.get(slot, "G5")
    prompt = prompts.tryon_prompt(slot, garment_desc)
    with open(model_image, "rb") as mf, open(garment_image, "rb") as gf:
        return _rep_logged(call,
                           {"prompt": prompt, "image": str(model_image), "garment": str(garment_image)},
                           {"prompt": prompt, "image": mf, "garment": gf}, ["text", "image"])


def collage_background(style: str = "streetwear flatlay"):
    prompt = prompts.collage_bg_prompt(style)
    return _rep_logged("G9", {"prompt": prompt}, {"prompt": prompt}, ["text", "image"])


def materialize_image(output, dest_path) -> str:
    """Turn a Replicate output (list / FileOutput / url / bytes) into a saved local file."""
    import requests
    obj = output[0] if isinstance(output, (list, tuple)) and output else output
    data = None
    if hasattr(obj, "read"):
        data = obj.read()
    elif isinstance(obj, (bytes, bytearray)):
        data = bytes(obj)
    elif isinstance(obj, str):
        r = requests.get(obj, timeout=60); r.raise_for_status(); data = r.content
    else:
        url = getattr(obj, "url", None)
        if url:
            r = requests.get(url, timeout=60); r.raise_for_status(); data = r.content
    if not data:
        raise RuntimeError("Could not read the model output image.")
    Path(dest_path).write_bytes(data)
    return str(dest_path)
