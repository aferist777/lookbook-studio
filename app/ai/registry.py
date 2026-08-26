"""Model registry: maps logical AI call IDs → provider + model.

Call IDs (models assigned by the user; multi-option calls can be overridden in
config.json -> model_choices):

  Vision/LLM (OpenRouter):
    T1  translate user free-text -> English (before any model sees it)
    V1  garment analysis from a reference frame
    V2  keyword-query builder            (reuses V1 model)
    V3  AI-stylist outfit suggestions    (reuses V1 model)

  Image gen/edit (Replicate):
    G1  persona face -> full-body (identity preserving)
    G2  persona face refine
    G3  persona age change
    G4  multi-angle persona reference set
    G5  try-on: top
    G6  try-on: bottom
    G7  try-on: shoes
    G8  extra poses of a dressed look
    G9  collage hybrid background
    G10 collage full-AI (TBD)

  Utility (Replicate):
    U1  packshot background removal / cutout
"""
from __future__ import annotations

from dataclasses import dataclass

OPENROUTER = "openrouter"
REPLICATE = "replicate"


@dataclass(frozen=True)
class ModelSpec:
    call_id: str
    provider: str
    kind: str                 # "vision" | "image"
    options: tuple[str, ...]  # one or more model ids; first = default
    note: str = ""

    @property
    def default(self) -> str:
        return self.options[0] if self.options else ""


REGISTRY: dict[str, ModelSpec] = {
    "T1": ModelSpec("T1", OPENROUTER, "text", ("nousresearch/hermes-4-405b",), "translate user text -> English"),
    "RC": ModelSpec("RC", OPENROUTER, "text", ("nousresearch/hermes-4-405b", "google/gemini-3.1-flash-lite"), "realism prompt compiler"),
    "V1": ModelSpec("V1", OPENROUTER, "vision", ("google/gemini-3.1-flash-lite", "stepfun/step-3.7-flash"), "garment analysis"),
    "V2": ModelSpec("V2", OPENROUTER, "text", ("google/gemini-3.1-flash-lite", "nousresearch/hermes-4-405b"), "keyword query builder"),
    "V3": ModelSpec("V3", OPENROUTER, "text", ("google/gemini-3.1-flash-lite", "nousresearch/hermes-4-405b"), "stylist outfit combos"),

    "G1": ModelSpec("G1", REPLICATE, "image", ("prunaai/z-image-turbo", "qwen/qwen-image"), "face->fullbody"),
    "G2": ModelSpec("G2", REPLICATE, "image", ("openai/gpt-image-1.5", "qwen/qwen-image"), "face refine"),
    "G3": ModelSpec("G3", REPLICATE, "image", ("openai/gpt-image-1.5", "qwen/qwen-image"), "age change"),
    "G4": ModelSpec("G4", REPLICATE, "image", ("ideogram-ai/ideogram-character", "sdxl-based/consistent-character"), "multi-angle set"),
    "G5": ModelSpec("G5", REPLICATE, "image", ("cedoysch/flux-fill-redux-try-on",), "try-on top"),
    "G6": ModelSpec("G6", REPLICATE, "image", ("cedoysch/flux-fill-redux-try-on",), "try-on bottom"),
    "G7": ModelSpec("G7", REPLICATE, "image", ("cedoysch/flux-fill-redux-try-on",), "try-on shoes"),
    "G8": ModelSpec("G8", REPLICATE, "image", ("ideogram-ai/ideogram-character",), "extra poses"),
    "G9": ModelSpec("G9", REPLICATE, "image", ("bria/generate-background",), "collage hybrid bg"),
    "G10": ModelSpec("G10", REPLICATE, "image", (), "collage full-AI (TBD)"),
    "U1": ModelSpec("U1", REPLICATE, "image", ("bria/remove-background", "fottoai/remove-bg-2"), "bg removal / cutout"),
}


def resolve(call_id: str, config) -> tuple[str, str]:
    """Return (provider, model_id), honoring a user override in config.model_choices."""
    spec = REGISTRY[call_id]
    chosen = config.model_choices.get(call_id) if config else None
    return spec.provider, (chosen or spec.default)
