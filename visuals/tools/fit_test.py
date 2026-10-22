#!/usr/bin/env python3
"""Positioning experiments on REFERENCE plates (below the 1600 px minimum / not accepted). Uses the readiness proposals; ORIGINAL wordmark only (G1 is tested
only on eligible full-resolution cans, glassware and signage). Outputs are labelled FIT TEST, never registered as composites, never deliverables.

    python3 visuals/tools/fit_test.py contact-sheet-2        # or: single-image-2
"""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plate_pipeline as pp  # noqa: E402
import plate_readiness as PR  # noqa: E402

ORDER = ["badshah_can", "amba_can", "badshah_glass", "amba_glass", "brewhouse_exterior", "hoodie"]


def cfg_for(pid, prop):
    if pid in ("badshah_can", "amba_can"):
        return dict(mode="can", plate_kind="can", art="badshah_wrap" if pid.startswith("bad") else "amba_wrap", region=prop["region"], shade_strength=.7 if pid.startswith("bad") else .5, ink=1.0)
    if pid.endswith("glass"):
        x0, y0, x1, y1 = prop["print_zone"]
        w = x1 - x0; cx = (x0 + x1) / 2; cy = (y0 + y1) / 2; s = min(w * .8, (y1 - y0) * .9)
        return dict(mode="print", plate_kind="glass", items=[dict(art="glass-etch-crest-white.png", quad=[[cx - s / 2, cy - s / 2], [cx + s / 2, cy - s / 2], [cx + s / 2, cy + s / 2], [cx - s / 2, cy + s / 2]], blend="screen", opacity=.85, luminance_follow=.5)])
    if pid == "brewhouse_exterior":
        return dict(mode="print", plate_kind="signage", items=[dict(art="sign-original-gold.png", quad=prop["art_quad"], blend="normal", opacity=.97, luminance_follow=.1, glow=.2)])
    if pid == "hoodie":
        x0, y0, x1, y1 = prop["chest_zone"]
        s = min(x1 - x0, y1 - y0) * .9; cx = (x0 + x1) / 2; cy = (y0 + y1) / 2
        return dict(mode="print", plate_kind="apparel", items=[dict(art="hoodie-symbol-gold.png", quad=[[cx - s / 2, cy - s / 2], [cx + s / 2, cy - s / 2], [cx + s / 2, cy + s / 2], [cx - s / 2, cy + s / 2]], blend="normal", opacity=.95, luminance_follow=.3, displace=.5)])


def main(set_name):
    reg = [r for r in pp.load(pp.REGISTER, []) if r.get("set") == set_name and r["plate_id"] in ORDER]
    out = ROOT / "visuals/composites/_fit-tests" / set_name
    out.mkdir(parents=True, exist_ok=True)
    tiles, prov = [], {}
    for pid in ORDER:
        for r in reg:
            if r["plate_id"] != pid:
                continue
            img = Image.open(ROOT / r["file"]).convert("RGB")
            prop = PR.propose(pid, img)
            if not prop.get("found"):
                continue
            cfg = cfg_for(pid, prop)
            res = pp.render_composite(img, cfg, "primary")
            f = out / f"{pid}-FIT-TEST.png"; res.save(f); tiles.append(res)
            prov[pid] = {"file": pp.rel(f), "sha256": pp.sha(f), "plate": r["file"], "plate_sha256": r["sha256"], "config": cfg}
    h = 520
    tiles = [t.resize((round(t.width * h / t.height), h)) for t in tiles]
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + 8 * (len(tiles) - 1), h), "white"); x = 0
    for t in tiles:
        sheet.paste(t, (x, 0)); x += t.width + 8
    sheet.save(out / "fit-test-sheet.png")
    (out / "FIT-TEST-PROVENANCE.json").write_text(json.dumps({"status": "FIT TEST ONLY — reference plates below the 1600 px minimum / not human-accepted; not registered; original wordmark only", "classification": pp.CLASSIFICATION, "caption": pp.CAPTION, "outputs": prov}, indent=1))
    print(set_name, len(prov), "fit tests ->", out)


if __name__ == "__main__":
    main(sys.argv[1])
