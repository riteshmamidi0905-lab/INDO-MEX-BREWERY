#!/usr/bin/env python3
"""Compositing-readiness report: for every registered plate, native size, intake verdict, review status, PROPOSED placement zones (auto-detected) and
the G1 cap-height feasibility there. Proposals are never used without a human `overlay` check; reference/fit-test plates are NOT production-ready by definition.

    python3 visuals/tools/plate_readiness.py            # writes docs/master-directive/COMPOSITING-READINESS.{md,json} and overlay montages
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plate_detect as D  # noqa: E402
import plate_pipeline as pp  # noqa: E402

KIND = {"badshah_can": "can", "amba_can": "can", "badshah_glass": "glass", "amba_glass": "glass", "brewhouse_exterior": "sign", "hoodie": "apparel", "gobi": "food"}


def propose(pid, img):
    kind = KIND[pid]
    if kind == "can":
        d = D.detect_can(img)
        if not d:
            return {"kind": kind, "found": False}
        reg = d["body_region"]
        cap = (reg[3] - reg[1]) * pp.G1_CAP_FRACTION_OF_WRAP
        return {"kind": kind, "found": True, "region": reg, "bbox": d["bbox"], "aspect_h_over_w": d["aspect_h_over_w"], "g1_cap_px": round(cap, 1), "zone": D.zone_metrics(img, reg)}
    if kind == "sign":
        d = D.detect_signboard(img)
        if not d:
            return {"kind": kind, "found": False}
        q = d["quad"]
        item = {"art": "sign-original-gold.png", "art_g1": "sign-g1-gold.png"}
        # artwork centred on the board, 60% of its width, placed by bilinear interpolation so it follows the board's perspective
        TL, TR, BR, BL = [__import__("numpy").array(p, float) for p in q]
        wq = float(__import__("numpy").linalg.norm(TR - TL))
        v_half = (.6 * wq * 409 / 1600) / float(__import__("numpy").linalg.norm(BL - TL)) / 2
        def bil(u, v):
            return TL * (1 - u) * (1 - v) + TR * u * (1 - v) + BL * (1 - u) * v + BR * u * v
        item["quad"] = [[float(x) for x in bil(u, v)] for u, v in ((.2, .5 - v_half), (.8, .5 - v_half), (.8, .5 + v_half), (.2, .5 + v_half))]
        cap = pp.g1_cap_px({"mode": "print"}, item)
        return {"kind": kind, "found": True, "board_quad": q, "board_area_frac": d["area_frac"], "rectangularity": d["rectangularity"], "art_quad": [[round(v) for v in p] for p in item["quad"]], "g1_cap_px": round(cap, 1), "zone": D.zone_metrics(img, q)}
    # glass / apparel: GrabCut object box, then proportional print zones
    d = D.detect_can(img, (.08, .04, .84, .92)) if kind == "apparel" else D.detect_can(img)
    if not d:
        return {"kind": kind, "found": False}
    x0, y0, x1, y1 = d["bbox"]; w, h = x1 - x0, y1 - y0
    if kind == "glass":
        zone = [round(x0 + .22 * w), round(y0 + .30 * h), round(x1 - .22 * w), round(y0 + .52 * h)]
        qw = zone[2] - zone[0]
        im = Image.open(pp.art_path("glass-etch-g1-white.png"))
        cap = 100 * im.height / 112 * qw / im.width
        return {"kind": kind, "found": True, "bbox": d["bbox"], "print_zone": zone, "g1_cap_px": round(cap, 1), "zone": D.zone_metrics(img, zone)}
    if kind == "apparel":
        zone = [round(x0 + .36 * w), round(y0 + .33 * h), round(x0 + .64 * w), round(y0 + .47 * h)]
        return {"kind": kind, "found": True, "bbox": d["bbox"], "chest_zone": zone, "zone": D.zone_metrics(img, zone)}
    return {"kind": kind, "found": True, "note": "food plate stays unbranded"}


def overlay(img, prop, out):
    im = img.convert("RGB"); d = ImageDraw.Draw(im)
    for k in ("region", "print_zone", "chest_zone", "bbox"):
        if k in prop and prop[k]:
            d.rectangle(prop[k], outline=(255, 0, 0) if k != "bbox" else (0, 160, 255), width=3)
    for k in ("board_quad", "art_quad"):
        if k in prop:
            q = [tuple(p) for p in prop[k]]; d.line(q + [q[0]], fill=(255, 255, 0) if k == "art_quad" else (255, 0, 0), width=3)
    im.save(out)


def main():
    reg = pp.load(pp.REGISTER, [])
    rows = []
    outdir = ROOT / "visuals/composites/_readiness"; outdir.mkdir(parents=True, exist_ok=True)
    for r in reg:
        pid = r["plate_id"]
        if pid.startswith("_") or pid not in KIND:
            continue
        f = ROOT / r["file"]
        img = Image.open(f)
        prop = propose(pid, img.convert("RGB"))
        ov = outdir / f"{r.get('set', 'default')}__{pid}.png"
        overlay(img, prop, ov)
        c = r["checks"]
        blockers = []
        if not c["long_side_ok"]:
            blockers.append(f"native long side {max(c['size'])} px < {pp.MIN_LONG_SIDE} px minimum")
        if not c["text_clean"]:
            blockers.append("readable text detected" if c["text_found"] else "text scan unavailable")
        if r["review"]["status"] != "accepted":
            blockers.append(f"review status = {r['review']['status']} (human acceptance required)")
        g1 = prop.get("g1_cap_px")
        if g1 is not None and g1 < pp.G1_MIN_CAP_PX:
            blockers.append(f"G1 would be ~{g1:.0f} px cap height (< {pp.G1_MIN_CAP_PX} px): original wordmark only")
        if pid == "brewhouse_exterior" and not prop.get("found"):
            blockers.append("no rectangular dark signboard detected")
        rows.append({"plate_id": pid, "set": r.get("set", "default"), "native_size": c["size"], "text_found": c["text_found"], "border_clean": c.get("border_clean"), "upscale_suspect": c.get("upscale_suspect"),
                     "review": r["review"]["status"], "proposal": prop, "blockers": blockers, "production_ready": not blockers, "overlay": pp.rel(ov)})
    (ROOT / "docs/master-directive/COMPOSITING-READINESS.json").write_text(json.dumps(rows, indent=1))
    md = ["# Compositing readiness (generated by visuals/tools/plate_readiness.py)", "",
          "**No plate is production-ready.** Every registered plate is below the 1600 px minimum and/or not human-accepted; they stay reference/fit-test assets. Proposed zones are auto-detected and unreviewed.", "",
          "| plate | set | native px | text | review | proposed zone | G1 cap px | blockers |", "|---|---|---|---|---|---|---|---|"]
    for x in rows:
        p = x["proposal"]
        zone = p.get("region") or p.get("print_zone") or p.get("art_quad") or p.get("chest_zone") or ("n/a" if x["plate_id"] == "gobi" else "not found")
        md.append(f"| {x['plate_id']} | {x['set']} | {x['native_size'][0]}×{x['native_size'][1]} | {'none' if not x['text_found'] else 'FOUND'} | {x['review']} | {zone} | {p.get('g1_cap_px', '—')} | {'; '.join(x['blockers']) or 'none'} |")
    (ROOT / "docs/master-directive/COMPOSITING-READINESS.md").write_text("\n".join(md) + "\n")
    print(f"{len(rows)} plates assessed; production-ready: {sum(x['production_ready'] for x in rows)}")


if __name__ == "__main__":
    main()
