"""Seed the app with REAL generations so results are waiting when you open it.

Requires API keys in config.json (replicate_api_token; aliexpress.* for products;
openrouter_api_key for the vision/translate steps). Run:  python seed.py

Every model call is recorded in the AI log (data/ai_log.jsonl), so you can inspect
exactly what was sent and returned. Stages are independent — a missing key only skips
its stage.
"""
from __future__ import annotations

from app import collage, config, fitting, lookbooks, personas, wardrobe
from app.db import init_db
from app.sources.base import get_source


def main() -> None:
    config.ensure_dirs()
    init_db()
    c = config.CONFIG

    if not c.replicate_api_token:
        raise SystemExit("Set replicate_api_token in config.json before seeding.")

    # 1) persona: TPDNE face -> full-body anchor (G1)
    print("· Rolling a face (TPDNE)…")
    face = personas.fetch_face()
    traits = {"name": "Mika", "age": 22, "gender": "androgynous tomboy",
              "build": "slim athletic", "hair": "buzzcut bleached", "extra": "silver hoops"}
    print("· Generating full-body (G1)… this calls Replicate")
    body = personas.make_fullbody(face, traits)
    pid = personas.create("Mika", 22, traits, face, body)
    print(f"  ✓ persona #{pid}")

    # 2) wardrobe: search + save a few items (needs AliExpress keys)
    have_ae = bool(c.aliexpress.get("app_key") and c.aliexpress.get("tracking_id"))
    if not have_ae:
        print("· No AliExpress keys — skipping product search / try-on / lookbook.")
        print("  ✓ seeded a persona; add AliExpress keys to seed a full lookbook.")
        return

    src = get_source("aliexpress_keyword")
    for q in ["oversize hoodie men", "baggy cargo pants", "chunky sneakers"]:
        print(f"· Searching “{q}”…")
        try:
            res = src.search(q, page=1, page_size=3)
            if res:
                wardrobe.save_result(res[0].to_card())
                print(f"  ✓ saved: {res[0].title[:48]}")
        except Exception as e:
            print(f"  ! search failed: {e}")

    saved = wardrobe.list_items(3, 0)
    if not saved:
        print("· No items saved — stopping after persona.")
        return

    # 3) try-on: layer the items onto the persona (U1 cutouts + G5/G6/G7)
    on_model = []
    for it, slot in zip(saved, ["top", "bottom", "footwear"]):
        it["slot"] = slot
        on_model.append(it)
    print("· Running try-on (cutouts + layered)… this calls Replicate")
    final = fitting.run_tryon(body, on_model)
    print(f"  ✓ model shot: {final}")

    # 4) lookbook + collage + export
    lb = lookbooks.create(pid, "Mika look")
    lookbooks.set_model_shot(lb, final)
    for it in on_model:
        lookbooks.add_item(lb, it["id"], "on_model")
    lbd = lookbooks.get(lb)
    cp = collage.build(lbd, "flatlay")
    lookbooks.update_collage(lb, cp, "flatlay")
    lbd = lookbooks.get(lb)
    out = lookbooks.export_package(lbd, None)
    print(f"  ✓ lookbook #{lb} collage + export → {out}")
    print("Done. Open the app — the persona, wardrobe, look and lookbook are waiting.")


if __name__ == "__main__":
    main()
