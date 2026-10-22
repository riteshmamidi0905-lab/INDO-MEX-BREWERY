#!/usr/bin/env python3
"""Source-plate intake and compositing pipeline (concept imagery only).

Plates are CLEAN, UNBRANDED AI-generated images the founder supplies (ChatGPT image generation; plan not independently verified). They must contain no
logos, readable text, packaging claims or brand graphics. NASHA artwork is applied only here, from verified vector masters
(visuals/brand-v3/labels, visuals/brand-v3/artwork). Every plate and composite is recorded as a CONCEPTUAL AI-GENERATED ASSET, not a photograph of any
existing NASHA product or location.

    python3 visuals/tools/plate_pipeline.py intake  <image> --plate-id badshah_can [--prompt-file p.txt] [--generated-on 2026-10-22]
    python3 visuals/tools/plate_pipeline.py review  <plate_id> --decision accepted|rejected --by "Ritesh" [--note ...]   # human decision, required
    python3 visuals/tools/plate_pipeline.py overlay <plate_id>        # draws the configured region/quad on the plate for visual checking
    python3 visuals/tools/plate_pipeline.py composite <plate_id> [--variant g1]   # only for ACCEPTED plates; g1 = approved large-format alternate
    python3 visuals/tools/plate_pipeline.py qa [<plate_id>]

Plate ids: badshah_can, badshah_glass, amba_can, amba_glass, brewhouse_exterior, hoodie, gobi.   Nothing is published or pushed by this tool.
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import composite_label as C  # noqa: E402

PLATES_DIR = ROOT / "visuals/source-plates"
CONFIGS = ROOT / "visuals/compositing-configs"
OUT = ROOT / "visuals/composites"
REGISTER = PLATES_DIR / "PLATE-REGISTER.json"
COMP_REGISTER = OUT / "COMPOSITE-REGISTER.json"

SUBJECTS = {
    "badshah_can": "BADSHAH beer can (blank)", "badshah_glass": "Wheat beer glass for BADSHAH (blank)",
    "amba_can": "AMBA HAZE beer can (blank)", "amba_glass": "IPA glass for AMBA HAZE (blank)",
    "brewhouse_exterior": "Court Brewhouse exterior / courtyard (blank sign board)", "hoodie": "THE COURTYARD hoodie (blank)", "gobi": "Mango Habanero Gobi (concept dish)",
}
CLASSIFICATION = "AI-generated conceptual asset. Not a photograph of any existing NASHA product or location. Not a verified product image."
TOOL = "ChatGPT image generation (supplied by the founder); ChatGPT plan NOT independently verified; OpenAI terms/output ownership not verified"
CAPTION = "Conceptual AI-generated image — not a photograph of an existing NASHA product or location."
MIN_LONG_SIDE = 1600
EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def rel(p):
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path, default):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default


def save(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1))


# ------------------------------------------------------------------ intake checks
def scan_text(img: Image.Image, min_score=0.5):
    """Detect readable text with an OCR engine. Returns (available, [strings]). A clean plate must return []."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:  # noqa: BLE001
        return False, []
    im = img.convert("RGB")
    s = 1600 / max(im.size)
    if s < 1:
        im = im.resize((round(im.width * s), round(im.height * s)))
    res, _ = RapidOCR()(np.asarray(im))
    out = []
    for r in res or []:
        txt, score = r[1].strip(), float(r[2])
        if score >= min_score and sum(ch.isalnum() for ch in txt) >= 2:
            out.append(f"{txt} ({score:.2f})")
    return True, out


def intake_checks(path):
    p = Path(path)
    c = {"format_ok": p.suffix.lower() in EXTS}
    img = Image.open(p)
    c["size"] = list(img.size)
    c["long_side_ok"] = max(img.size) >= MIN_LONG_SIDE
    ocr_ok, found = scan_text(img)
    c["text_scan_available"] = ocr_ok
    c["text_found"] = found
    c["text_clean"] = bool(ocr_ok and not found)
    c["alpha_channel"] = img.mode in ("RGBA", "LA")
    return c


def cmd_intake(a):
    if a.plate_id not in SUBJECTS:
        sys.exit(f"unknown plate id; choose from {sorted(SUBJECTS)}")
    src = Path(a.image)
    dst = PLATES_DIR / "incoming" / a.plate_id / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    checks = intake_checks(dst)
    reg = load(REGISTER, [])
    prompt = Path(a.prompt_file).read_text() if a.prompt_file else None
    rec = {"plate_id": a.plate_id, "subject": SUBJECTS[a.plate_id], "file": rel(dst), "sha256": sha(dst), "received_at": now(), "generated_on": a.generated_on,
           "tool": TOOL, "prompt": prompt or "NOT RECORDED (founder to supply)", "classification": CLASSIFICATION, "caption": CAPTION,
           "rights": "unverified; no third-party material known; NASHA/trademark clearance not assumed; not approved for publication",
           "checks": checks, "review": {"status": "pending", "by": None, "at": None, "note": None},
           "auto_verdict": "pass" if (checks["format_ok"] and checks["long_side_ok"] and checks["text_clean"]) else "needs attention"}
    reg = [r for r in reg if not (r["plate_id"] == a.plate_id and r["sha256"] == rec["sha256"])] + [rec]
    save(REGISTER, reg)
    print(json.dumps({k: rec[k] for k in ("plate_id", "file", "auto_verdict", "checks")}, indent=1))
    if not checks["text_scan_available"]:
        print("WARNING: no OCR engine installed (pip install rapidocr-onnxruntime); readable-text check NOT performed — review by eye.")


def cmd_review(a):
    reg = load(REGISTER, [])
    recs = [r for r in reg if r["plate_id"] == a.plate_id]
    if not recs:
        sys.exit("no such plate in the register")
    r = recs[-1]
    if a.decision == "accepted" and r["auto_verdict"] != "pass" and not a.override:
        sys.exit("auto checks did not pass (" + json.dumps(r["checks"]) + "); fix the plate or pass --override with a note")
    src = ROOT / r["file"]
    folder = "accepted" if a.decision == "accepted" else "rejected"
    dst = PLATES_DIR / folder / a.plate_id / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dst)
    r["file"] = rel(dst)
    r["review"] = {"status": a.decision, "by": a.by, "at": now(), "note": a.note}
    save(REGISTER, reg)
    print(a.plate_id, "->", a.decision)


def accepted_plate(plate_id):
    reg = load(REGISTER, [])
    recs = [r for r in reg if r["plate_id"] == plate_id and r["review"]["status"] == "accepted"]
    if not recs:
        sys.exit(f"{plate_id}: no ACCEPTED plate (a human review is required first)")
    return recs[-1]


# ------------------------------------------------------------------ compositing
def perspective_coeffs(dst, src):
    """Coefficients for PIL Image.transform(PERSPECTIVE): maps output (dst) pixel -> source (art) pixel."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(A, float), np.array(b, float))


def warp_art(art: Image.Image, quad, size):
    """Warp RGBA `art` into the plate-sized RGBA canvas so that its corners land on quad (TL,TR,BR,BL)."""
    w, h = art.size
    co = perspective_coeffs(quad, [(0, 0), (w, 0), (w, h), (0, h)])
    return art.convert("RGBA").transform(size, Image.PERSPECTIVE, tuple(co), Image.BICUBIC)


def blend_print(plate: Image.Image, art_rgba: Image.Image, mode="normal", opacity=0.9, luminance_follow=0.4, glow=0.0, displace=0.0):
    """Apply warped RGBA ink to the plate. luminance_follow: ink picks up the plate's own light (1 = fully, 0 = flat); displace: px shift from fabric relief."""
    p = np.asarray(plate.convert("RGB"), np.float32)
    a = np.asarray(art_rgba, np.float32)
    lum = p.mean(axis=2, keepdims=True) / 255.0
    if displace:
        g = np.asarray(Image.fromarray((lum[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255.0
        gy, gx = np.gradient(g)
        yy, xx = np.mgrid[0:p.shape[0], 0:p.shape[1]]
        sx = np.clip((xx + gx * displace * 40).round().astype(int), 0, p.shape[1] - 1)
        sy = np.clip((yy + gy * displace * 40).round().astype(int), 0, p.shape[0] - 1)
        a = a[sy, sx]
    alpha = a[..., 3:4] / 255.0 * opacity
    ink = a[..., :3]
    ink = ink * ((1 - luminance_follow) + luminance_follow * np.clip(lum / max(np.percentile(lum, 95), 1e-3), 0, 1.1))
    if mode == "multiply":
        out = p * (1 - alpha) + (p * ink / 255.0) * alpha
    elif mode == "screen":
        out = p * (1 - alpha) + (255 - (255 - p) * (255 - ink) / 255.0) * alpha
    else:
        out = p * (1 - alpha) + ink * alpha
    if glow:
        halo = Image.fromarray((a[..., 3] * 1.0).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18))
        h = np.asarray(halo, np.float32)[..., None] / 255.0 * glow
        out = out + (a[..., :3].mean(axis=(0, 1), keepdims=True) * 0 + np.array([240, 190, 100], np.float32)) * h
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


ART = {"badshah_wrap": "visuals/brand-v3/labels/badshah-wrap.png", "badshah_wrap_g1": "visuals/brand-v3/labels/badshah-wrap-g1.png",
       "amba_wrap": "visuals/brand-v3/labels/amba-haze-wrap.png", "amba_wrap_g1": "visuals/brand-v3/labels/amba-haze-wrap-g1.png"}


def art_path(name):
    return ROOT / (ART.get(name) or (name if "/" in name else f"visuals/brand-v3/artwork/{name}"))


def pick(item, variant):
    """Artwork name for this variant: `art_g1` when variant == 'g1' and the item defines one, else `art`."""
    return item.get("art_g1") if variant == "g1" and item.get("art_g1") else item.get("art")


def render_composite(plate_img: Image.Image, cfg: dict, variant="primary") -> Image.Image:
    mode = cfg["mode"]
    if mode == "none":
        return plate_img.convert("RGB")
    if mode == "can":
        return C.composite(plate_img, Image.open(art_path(pick(cfg, variant))), tuple(cfg["region"]), center_frac=cfg.get("center_frac", .5), shade_strength=cfg.get("shade_strength", 1.0), ink=cfg.get("ink", .96))
    if mode == "print":
        out = plate_img.convert("RGB")
        for item in cfg["items"]:
            warped = warp_art(Image.open(art_path(pick(item, variant))), item["quad"], out.size)
            out = blend_print(out, warped, item.get("blend", "normal"), item.get("opacity", .9), item.get("luminance_follow", .4), item.get("glow", 0.0), item.get("displace", 0.0))
        return out
    raise ValueError(f"unknown mode {mode}")


G1_MIN_CAP_PX = 32
G1_CAP_FRACTION_OF_WRAP = 0.085        # label wraps: the G1 header's cap height is ~85 art px of the 1000 px wrap height


def g1_cap_px(cfg, item):
    """Cap height (px) the G1 wordmark would have on the FINAL plate image, or None when the item does not use G1."""
    name = str(pick(item, "g1") if cfg.get("mode") != "can" else pick(cfg, "g1"))
    if "g1" not in name.lower():
        return None
    if cfg.get("mode") == "can":
        x0, y0, x1, y1 = cfg["region"]
        return (y1 - y0) * G1_CAP_FRACTION_OF_WRAP
    im = Image.open(art_path(name))
    q = item["quad"]
    qw = ((q[1][0] - q[0][0]) ** 2 + (q[1][1] - q[0][1]) ** 2) ** .5
    return 100 * im.height / (100 + 12) * qw / im.width          # artwork height = 100 + 2*6 units


def validate_config(cfg, variant="primary"):
    errs = []
    if cfg.get("status", "").startswith("TEMPLATE"):
        errs.append("config is still a TEMPLATE: set region/quad after reviewing the accepted plate (use `overlay` to check)")
    items = [cfg] if cfg.get("mode") == "can" else cfg.get("items", [])
    for it in items:
        name = pick(it, variant)
        if cfg.get("mode") != "none" and (not name or not art_path(name).exists()):
            errs.append(f"artwork not found: {name}")
        if variant == "g1":
            cap = g1_cap_px(cfg, it)
            if cap is not None and cap < G1_MIN_CAP_PX and any(q for q in (it.get("quad") or it.get("region") or []) if q):
                errs.append(f"G1 alternate would have a cap height of ~{cap:.0f}px on this plate; the approved minimum is {G1_MIN_CAP_PX}px (use the original wordmark or a higher-resolution plate)")
        if "g1" in str(name).lower() and cfg.get("plate_kind") not in ("can", "glass", "signage"):
            errs.append("G1 alternate is approved only for cans, glassware and architectural signage (never apparel, food, small formats)")
    return errs


def cmd_overlay(a):
    rec = accepted_plate(a.plate_id) if not a.any_status else load(REGISTER, [])[-1]
    cfg = load(CONFIGS / f"{a.plate_id}.json", None)
    img = Image.open(ROOT / rec["file"]).convert("RGB")
    d = ImageDraw.Draw(img)
    if cfg and cfg.get("mode") == "can":
        x0, y0, x1, y1 = cfg["region"]; d.rectangle((x0, y0, x1, y1), outline=(255, 0, 0), width=4)
    for it in (cfg or {}).get("items", []):
        q = [tuple(p) for p in it["quad"]]; d.line(q + [q[0]], fill=(255, 0, 0), width=4)
    o = OUT / a.plate_id / "overlay-check.png"
    o.parent.mkdir(parents=True, exist_ok=True); img.save(o); print(o)


def cmd_composite(a):
    rec = accepted_plate(a.plate_id)
    cfg = load(CONFIGS / f"{a.plate_id}.json", None)
    if cfg is None:
        sys.exit("no compositing config for this plate")
    errs = validate_config(cfg, a.variant)
    if errs:
        sys.exit("; ".join(errs))
    img = render_composite(Image.open(ROOT / rec["file"]), cfg, a.variant)
    d = OUT / a.plate_id
    d.mkdir(parents=True, exist_ok=True)
    tag = "" if a.variant == "primary" else f"-{a.variant}"
    full = d / f"{a.plate_id}{tag}-composite.png"
    img.save(full)
    web = {}
    for w in (1600, 800, 400):
        if img.width >= w:
            p = d / f"{a.plate_id}{tag}-{w}.webp"
            img.resize((w, round(img.height * w / img.width)), Image.LANCZOS).save(p, quality=86); web[w] = rel(p)
    arts = sorted({pick(it, a.variant) for it in ([cfg] if cfg["mode"] == "can" else cfg.get("items", []))})
    prov = {"asset": rel(full), "sha256": sha(full), "web_sizes": web, "plate": rec["file"], "plate_sha256": rec["sha256"], "variant": a.variant, "config_sha256": sha(CONFIGS / f"{a.plate_id}.json"),
            "artwork": {n: sha(art_path(n)) for n in arts}, "composited_at": now(), "method": "visuals/tools/plate_pipeline.py (cylinder/perspective warp of verified vector art onto an unbranded plate)",
            "classification": CLASSIFICATION, "caption": CAPTION, "plate_tool": TOOL, "rights": rec["rights"],
            "approval": "NOT approved for publication; conceptual only; placeholders (ABV, volume, ingredients, certifications, regulatory text, barcode) remain placeholders",
            "usage": "internal review / local preview only"}
    save(d / f"{a.plate_id}{tag}-composite.provenance.json", prov)
    reg = [r for r in load(COMP_REGISTER, []) if r["asset"] != prov["asset"]] + [prov]
    save(COMP_REGISTER, reg)
    print("composited", full)


def cmd_qa(a):
    problems = []
    for pr in load(COMP_REGISTER, []):
        if a.plate_id and a.plate_id not in pr["asset"]:
            continue
        f = ROOT / pr["asset"]
        if not f.exists() or sha(f) != pr["sha256"]:
            problems.append(f"{pr['asset']}: file missing or changed since provenance was written")
        for n, h in pr["artwork"].items():
            if sha(art_path(n)) != h:
                problems.append(f"{pr['asset']}: artwork {n} changed after compositing (re-composite)")
        if "conceptual" not in pr["classification"].lower() or "not a photograph" not in pr["classification"].lower():
            problems.append(f"{pr['asset']}: classification missing")
    print("QA:", "OK" if not problems else "\n".join(problems))
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("intake"); i.add_argument("image"); i.add_argument("--plate-id", required=True); i.add_argument("--prompt-file"); i.add_argument("--generated-on", default="not stated")
    r = sp.add_parser("review"); r.add_argument("plate_id"); r.add_argument("--decision", required=True, choices=["accepted", "rejected"]); r.add_argument("--by", required=True); r.add_argument("--note", default=""); r.add_argument("--override", action="store_true")
    o = sp.add_parser("overlay"); o.add_argument("plate_id"); o.add_argument("--any-status", action="store_true")
    c = sp.add_parser("composite"); c.add_argument("plate_id"); c.add_argument("--variant", choices=["primary", "g1"], default="primary", help="g1 = approved glass-A alternate (cans, glassware, signage only)")
    q = sp.add_parser("qa"); q.add_argument("plate_id", nargs="?")
    a = ap.parse_args(argv)
    return {"intake": cmd_intake, "review": cmd_review, "overlay": cmd_overlay, "composite": cmd_composite, "qa": cmd_qa}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
