#!/usr/bin/env python3
"""Regenerate visuals/brand-v3/PROVENANCE.json (sha256 + method/rights/approval per asset). Run after re-rendering any brand-v3 asset."""
import hashlib, json, pathlib
R = pathlib.Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256((R / p).read_bytes()).hexdigest()
common = dict(authorship="Claude Code in a session with the founder; AI-assisted, declare as such", rights="No third-party material; ownership/assignment undocumented (needs counsel); NOT trademark-cleared", approval="NOT approved by founder; concept only; unpublished")
items = []
for f in ("badshah-wrap.svg", "badshah-wrap.png", "amba-haze-wrap.svg", "amba-haze-wrap.png"):
    items.append(dict(asset=f"visuals/brand-v3/labels/{f}", sha256=sha(f"visuals/brand-v3/labels/{f}"), method="procedural vector drawing by code (brand/tools/brand_v3_art.py), PNG via headless Chromium; real type = Instrument Serif/Inter (OFL, licence record pending)", sources="drawn from scratch; mood/palette informed by the user-supplied ChatGPT reference board, nothing copied or traced", usage="concept label artwork; ABV, volume, ingredients, certifications, regulatory text, barcode are PLACEHOLDERS", **common))
for f in ("blank-can-plate-procedural.png", "badshah-can-procedural.png", "amba-haze-can-procedural.png", "cans-pair-procedural.png"):
    items.append(dict(asset=f"visuals/brand-v3/mockups/{f}", sha256=sha(f"visuals/brand-v3/mockups/{f}"), method="procedural render by code (visuals/tools/composite_label.py); NOT a photograph, no generative model", sources="procedural plate + the label wraps above", usage="pipeline proof / concept mockup only; never label as photography", **common))
for f in ("identity-board-v3.svg", "identity-board-v3.png"):
    items.append(dict(asset=f"visuals/brand-v3/{f}", sha256=sha(f"visuals/brand-v3/{f}"), method="flat vector board built by brand/tools/brand_v3_board.py", sources="Courtyard refined marks + v3 palette; label wraps; procedural can renders", usage="internal review board", **common))
for f in ("badshah-label-front.webp", "badshah-can.webp", "amba-haze-label-front.webp", "amba-haze-can.webp"):
    items.append(dict(asset=f"website/preview-courtyard/assets/{f}", sha256=sha(f"website/preview-courtyard/assets/{f}"), method="optimised web copy (crop + WebP) of the brand-v3 source files", sources="visuals/brand-v3 (sources kept separately)", usage="local noindex website preview only; never deployed", **common))
ref = "visuals/references/chatgpt-brand-board-2026-10-22.webp"
items.append(dict(asset=ref, sha256=sha(ref), method="AI image generation with ChatGPT's image-generation tool, by the founder, 2026-10-22 (per the founder)", authorship="founder-prompted, model-generated", sources="not copied from another brand (per the founder); prompt text not recorded in the repo", rights="OpenAI terms for this account/plan not verified; ownership of outputs not verified; image contains model-drawn text and logo-like marks", approval="EXPLORATORY CONCEPT ARTWORK, creative reference only; not a product photograph; not trademark-cleared; not for publication or reuse", usage="mood/palette/composition reference; nothing from it is incorporated into any asset"))
(R / "visuals/brand-v3/PROVENANCE.json").write_text(json.dumps(items, indent=1))
print(len(items), "records")
