# Lookbook Studio

Desktop app (PySide6) for building **streetwear / tomboy** affiliate lookbooks:
find products on AliExpress → curate a wardrobe → dress a consistent AI persona
(virtual try-on) → assemble a lookbook + collage → export a Telegram post with
affiliate links.

Monetization = **affiliate** (model A): lookbooks are free, revenue is commission
on tracked links.

## Stack
- Python + PySide6 (QtWebEngine for the embedded browser)
- SQLite (local, file-based)
- Tabler icons (vendored SVG → QIcon)
- AI behind an adapter layer:
  - **OpenRouter** — vision / LLM (`google/gemini-3.1-flash-lite`)
  - **Replicate** — image generation / editing / try-on / background
- AliExpress official **Affiliate API** (`python-aliexpress-api`)
- yt-dlp for media download

## Tabs (UI order)
1. **Personas** — TPDNE face → full-body persona → library
2. **Wardrobe** — the hub: curated products (packshot, price, affiliate link, variants, cutout)
3. **Fitting room** — layered try-on (top → bottom → shoes), batch → pick best
4. **Collect** — embedded browser (IG / Pinterest) → saved links → download → frame-pick → vision search
5. **Lookbook** — outfit on model + collage + export package (template flatlay / hybrid / full-AI)

## Build phases
0. Foundation (this) · 1. Wardrobe + keyword search · 2. Personas · 3. Fitting room ·
4. Lookbook/Publish **(MVP)** · 5. Collect · 6. Expansion.

The fragile Collect tab (IG DOM / downloaders / vision) is built last — the Wardrobe is
fed by plain keyword search first, so the money-making slice (phases 0–4) does not depend on it.

## Setup
```bash
pip install -r requirements.txt
cp config.example.json config.json   # then fill in API keys
python main.py
```

## AI call registry (assign models in `config.json` → `model_choices`)
| ID | Where | Provider | Default model |
|----|-------|----------|---------------|
| V1 | garment analysis from a reference frame | OpenRouter | google/gemini-3.1-flash-lite |
| V2 | keyword-query builder | OpenRouter | (reuses V1) |
| V3 | AI-stylist outfit suggestions | OpenRouter | (reuses V1) |
| G1 | persona face → full-body | Replicate | prunaai/z-image-turbo *(or qwen/qwen-image)* |
| G2 | persona face refine | Replicate | openai/gpt-image-1.5 *(or qwen/qwen-image)* |
| G3 | persona age change | Replicate | openai/gpt-image-1.5 *(or qwen/qwen-image)* |
| G4 | multi-angle persona set | Replicate | ideogram-ai/ideogram-character *(or sdxl consistent-character)* |
| G5/G6/G7 | try-on top / bottom / shoes | Replicate | cedoysch/flux-fill-redux-try-on |
| G8 | extra poses | Replicate | ideogram-ai/ideogram-character |
| G9 | collage hybrid background | Replicate | bria/generate-background |
| G10 | collage full-AI | Replicate | *(TBD)* |
| U1 | packshot background removal | Replicate | bria/remove-background |
