"""Prompts for Lookbook Studio — written fresh for the streetwear / tomboy
affiliate-lookbook task (NOT ported from the legacy ugc-cg pipeline).

Vision prompts return STRICT JSON so the app can parse deterministically.
Image prompts are templates filled at call time.

The whole app UI is English, but the user may type in any language. All user
free-text is passed through TRANSLATE (T1) into English before it reaches any
vision/generation model, so prompts stay model-friendly.
"""
from __future__ import annotations

# ------------------------------------------------------------------ T1: translation
TRANSLATE_SYSTEM = """You translate the user's text into natural English suitable as an
instruction or prompt for an image / vision model. Output ONLY the translation: no quotes,
no notes, no explanation. If the text is already English, return it unchanged. Preserve
fashion/streetwear terminology and any concrete details (colours, fits, materials)."""

# ------------------------------------------------------------------ V1: garment analysis
GARMENT_ANALYSIS_SYSTEM = """You are a fashion-cataloguing assistant for a streetwear lookbook tool.
The audience is unisex street style — boys and tomboy girls: oversize hoodies, cargos, baggy jeans,
bombers, beanies, chunky sneakers, crossbody bags. You receive ONE reference image (a still from a
Reel or Pin) and must identify every wearable item on the MAIN subject.

Return STRICT JSON only — no prose, no markdown fences. Shape:
{
  "items": [
    {
      "slot": "top|bottom|outerwear|footwear|headwear|accessory",
      "category": "short noun, e.g. 'hoodie', 'cargo pants', 'chunky sneakers'",
      "color": "primary colour(s)",
      "pattern": "solid|graphic|camo|stripe|plaid|tie-dye|other",
      "material_guess": "best guess, e.g. 'cotton fleece', 'denim'",
      "fit": "oversize|relaxed|regular|slim|baggy",
      "style_tags": ["streetwear", "y2k", "techwear"],
      "gender_lean": "unisex|masc|fem",
      "search_query": "3-7 English keywords optimized for an AliExpress search, no brand names"
    }
  ]
}
Rules: ignore background people; if an item is partly hidden, still give your best guess;
never invent brand names; keep search_query generic and marketplace-friendly."""

GARMENT_ANALYSIS_USER = "Identify the wearable items on the main subject and return the JSON."


# ------------------------------------------------------------------ V2: keyword query refine
QUERY_BUILDER_SYSTEM = """You turn one garment description into the single best AliExpress search query.
Audience: unisex streetwear. Output ONLY the query string (3-7 words, English, no punctuation,
no brand names). Favour terms sellers actually use, e.g. 'oversize hoodie men', 'baggy cargo pants'."""


def query_builder_user(attrs: dict) -> str:
    return (
        f"slot={attrs.get('slot')}, category={attrs.get('category')}, color={attrs.get('color')}, "
        f"fit={attrs.get('fit')}, pattern={attrs.get('pattern')}, tags={attrs.get('style_tags')}. "
        "Give the single best search query."
    )


# ------------------------------------------------------------------ V3: stylist
STYLIST_SYSTEM = """You are a streetwear stylist for unisex / tomboy looks. Given a list of wardrobe
items (JSON), propose complete outfits. Each outfit = one top, one bottom, optional outerwear, one
footwear, optional headwear/accessories, chosen so colours and styles work together.
Return STRICT JSON: {"outfits":[{"name":"...","item_ids":[...],"why":"one short sentence"}]}."""


def stylist_user(items_json: str) -> str:
    return f"Wardrobe items:\n{items_json}\nPropose 2-4 cohesive outfits."


# ------------------------------------------------------------------ G1: face -> full body
def face_to_fullbody_prompt(traits: dict) -> str:
    age = traits.get("age", "early 20s")
    gender = traits.get("gender", "androgynous tomboy")
    build = traits.get("build", "slim athletic")
    hair = traits.get("hair", "")
    extra = traits.get("extra", "")
    return (
        f"Full-body studio photo of a {age} {gender} streetwear model, {build} build, {hair} {extra}, "
        "standing straight in a relaxed A-pose facing the camera, arms slightly away from the torso, "
        "wearing a plain fitted neutral base layer (plain t-shirt and leggings) suitable for virtual "
        "try-on, soft even studio lighting, seamless light-grey background, sharp focus, photorealistic, "
        "full body visible from head to shoes, centered, 4k. Keep the exact same face as the reference."
    ).strip()


# ------------------------------------------------------------------ G2 / G3: refine / age
def face_refine_prompt(instruction: str) -> str:
    return (
        "Edit only the facial details as instructed; keep identity, framing and lighting unchanged. "
        f"Instruction: {instruction}"
    )


def age_change_prompt(target_age) -> str:
    return (
        f"Change only the apparent age of this same person to about {target_age} years old. "
        "Keep identity, pose, framing, hairstyle and lighting consistent. Photorealistic."
    )


# ------------------------------------------------------------------ G5/G6/G7: try-on
def tryon_prompt(slot: str, garment_desc: str) -> str:
    where = {
        "top": "upper body (replace the top)",
        "bottom": "lower body (replace the trousers / skirt)",
        "footwear": "feet (replace the shoes)",
    }.get(slot, slot)
    return (
        f"Dress the person in the provided garment on the {where}. Keep the same face, body, pose, "
        f"background and lighting. The garment is: {garment_desc}. Natural drape and fit, realistic "
        "fabric folds and shadows, photorealistic, do not alter other clothing items."
    )


# ------------------------------------------------------------------ RC: realism compiler
REALISM_SYSTEM = """You rewrite an image-generation prompt so the result looks like a REAL, unretouched
phone photo, not a glossy render. Keep ALL of the user's content (subject, age, pose, outfit, scene),
then APPEND realism cues: phone-camera realism, subtle sensor grain, slight edge softness, unretouched,
no beauty filters, no skin smoothing, visible pores and fine skin texture, subtle under-eye texture,
natural flyaway hairs, realistic hand anatomy and proportions, natural contrast and accurate white balance,
shallow depth of field, editorial realism. Output ONLY the rewritten prompt — no notes, no quotes."""


# ------------------------------------------------------------------ i2i edit ops (pose / emotion / gender)
POSE_PRESETS = ["standing relaxed", "walking, mid-stride", "leaning on a wall", "sitting on steps",
                "hands in pockets", "looking over shoulder", "crouching low", "arms crossed"]
EMOTION_PRESETS = ["neutral", "soft smile", "confident", "serious", "playful", "bored", "surprised", "moody"]


# ------------------------------------------------------------------ parameter-driven model generator
AGE_PRESETS = ["16-19", "20-24", "25-29", "30-34"]
GENDER_PRESETS = ["tomboy girl", "androgynous tomboy", "street boy", "unisex"]
BODY_PRESETS = ["slim athletic", "petite", "curvy", "tall"]
SKIN_PRESETS = ["fair", "light", "tan", "brown", "dark"]
HAIR_PRESETS = ["buzzcut bleached", "short crop", "long dyed", "messy bob", "slicked back"]
SHOT_PRESETS = ["full body", "three-quarter", "portrait", "low angle"]
SETTING_PRESETS = ["concrete studio", "street", "indoor", "rooftop", "neutral grey"]
LIGHTING_PRESETS = ["soft daylight", "golden hour", "overcast", "hard flash"]
STYLE_PRESETS = ["streetwear", "y2k", "techwear", "grunge", "minimal"]


def model_prompt(p: dict) -> str:
    """Assemble the text-to-image prompt for the parameter-driven model generator."""
    gender = p.get("gender") or "streetwear model"
    head = f"{p.get('shot', 'full body')} photo of a {p.get('age', '')} {gender} streetwear model"
    parts = [
        " ".join(head.split()),
        f"{p.get('body', '')} build" if p.get("body") else "",
        p.get("skin", ""),
        p.get("hair", ""),
        f"{p.get('expression', '')} expression" if p.get("expression") else "",
        p.get("pose", ""),
        p.get("setting", ""),
        p.get("lighting", ""),
        f"{p.get('style', '')} style" if p.get("style") else "",
        p.get("custom", ""),
    ]
    return ", ".join(s.strip() for s in parts if s and s.strip())


def pose_edit_prompt(pose: str) -> str:
    return (f"Change the person's pose to: {pose}. Keep the exact same face, identity, hairstyle, "
            "outfit and lighting. Full body, natural posture, photorealistic.")


def emotion_edit_prompt(emotion: str) -> str:
    return (f"Change the facial expression to: {emotion}. Keep the exact same face, identity, pose, "
            "framing and lighting. Photorealistic, natural.")


def gender_edit_prompt(gender: str) -> str:
    return (f"Render the same person presenting as {gender}, keeping a recognizably similar face and "
            "overall vibe, same pose, framing and lighting. Photorealistic.")


# ------------------------------------------------------------------ photoshoot + actor sheets
def pose_variation_prompt(pose: str) -> str:
    return (f"Same character, new shot: {pose}. Keep identity, outfit and style locked. "
            "Full-body streetwear shot, natural posture, photorealistic.")


ACTOR_PORTRAIT_PROMPT = (
    "Reference portrait sheet of the same person: front and three-quarter head-and-shoulders views, "
    "neutral expression, even studio lighting, plain light-grey background, sharp, photorealistic. Keep identity.")

ACTOR_TPOSE_PROMPT = (
    "Full-body T-pose reference of the same person, arms out to the sides, neutral expression, plain fitted "
    "neutral clothing, even studio lighting, seamless light-grey background, head to toe, photorealistic. Keep identity.")


# ------------------------------------------------------------------ G9: collage background
def collage_bg_prompt(style: str = "streetwear flatlay") -> str:
    return (
        f"Clean aesthetic {style} backdrop for a fashion product collage: soft studio texture on a "
        "concrete / paper / fabric surface, muted street palette, even top-down lighting, NO products, "
        "NO text, generous negative space for compositing cut-out items on top."
    )
