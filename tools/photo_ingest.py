#!/usr/bin/env python3
"""NASHA R&D photo ingestion (Sprint 14). Keeps ORIGINAL, EDITED and WEB-EXPORT separate and never modifies an original.
  python3 tools/photo_ingest.py ingest <src_dir_or_file> --run RUN --construction A --hold-min 0 --photographer NAME --device DEVICE --rights-owner NAME
  python3 tools/photo_ingest.py report            list ingested photos and QA flags
  python3 tools/photo_ingest.py selftest
Originals are copied (read-only) to food/t1-photos/originals/<run>/ with a SHA-256; provenance rows go to food/t1-photos/provenance.csv. Metrics are
screening flags only (blur/exposure/clipping/resolution); a human reviews every photo. No AI enhancement, no generative edits."""
import argparse, csv, hashlib, os, shutil, subprocess, sys, tempfile, datetime
import numpy as np
from PIL import Image, ImageOps
import cv2, imagehash
ROOT = "food/t1-photos"; PROV = f"{ROOT}/provenance.csv"
COLS = ["photo_id","sha256","original_path","run_id","date_ingested","construction","hold_time_min","shot_type","photographer","device","edits_applied","rights_owner","identifiable_people","width","height","megapixels","exif_datetime","sharpness_lap_var","mean_luma","clip_black_pct","clip_white_pct","phash","qa_flags","edited_path","web_export_path"]
IMG = (".jpg",".jpeg",".png",".heic",".tif",".tiff",".webp")

def metrics(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    g = np.asarray(im.convert("L"), dtype=np.float32)
    small = cv2.resize(g, (min(1024, g.shape[1]), int(g.shape[0] * min(1024, g.shape[1]) / g.shape[1])))
    lap = float(cv2.Laplacian(small, cv2.CV_32F).var())
    m = dict(width=im.width, height=im.height, megapixels=round(im.width * im.height / 1e6, 2), sharpness_lap_var=round(lap, 1), mean_luma=round(float(g.mean()), 1),
             clip_black_pct=round(float((g <= 3).mean() * 100), 2), clip_white_pct=round(float((g >= 252).mean() * 100), 2), phash=str(imagehash.phash(im)))
    flags = []
    if lap < 60: flags.append("POSSIBLE_BLUR")
    if m["mean_luma"] < 70: flags.append("UNDEREXPOSED?")
    if m["mean_luma"] > 200: flags.append("OVEREXPOSED?")
    if m["clip_white_pct"] > 5: flags.append("HIGHLIGHT_CLIP")
    if m["clip_black_pct"] > 8: flags.append("SHADOW_CLIP")
    if min(im.size) < 1500: flags.append("LOW_RES(<1500px short side)")
    m["qa_flags"] = "|".join(flags) or "none"
    return m

def exif_dt(path):
    try:
        out = subprocess.run(["exiftool", "-s3", "-DateTimeOriginal", path], capture_output=True, text=True, timeout=30).stdout.strip()
        return out or "NOT MEASURED"
    except Exception: return "NOT MEASURED"

def rows(): return list(csv.DictReader(open(PROV, encoding="utf-8"))) if os.path.exists(PROV) else []

def ingest(src, a, root=ROOT, prov=PROV):
    files = [src] if os.path.isfile(src) else sorted(os.path.join(d, f) for d, _, fs in os.walk(src) for f in fs if f.lower().endswith(IMG))
    od = f"{root}/originals/{a.run}"; os.makedirs(od, exist_ok=True)
    os.makedirs(f"{root}/edited/{a.run}", exist_ok=True); os.makedirs(f"{root}/web/{a.run}", exist_ok=True)
    existing = {r["sha256"] for r in (list(csv.DictReader(open(prov, encoding="utf-8"))) if os.path.exists(prov) else [])}
    new = not os.path.exists(prov); added = []
    with open(prov, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLS)
        if new: w.writeheader()
        n = len(existing)
        for f in files:
            h = hashlib.sha256(open(f, "rb").read()).hexdigest()
            if h in existing: print("SKIP duplicate (same SHA-256):", f); continue
            n += 1; pid = f"{a.run}-P{n:03d}"; dst = f"{od}/{pid}{os.path.splitext(f)[1].lower()}"
            shutil.copy2(f, dst); os.chmod(dst, 0o444)
            try: m = metrics(dst)
            except Exception as e: m = dict(width="",height="",megapixels="",sharpness_lap_var="",mean_luma="",clip_black_pct="",clip_white_pct="",phash="",qa_flags=f"UNREADABLE:{e}")
            w.writerow(dict(photo_id=pid, sha256=h, original_path=dst, run_id=a.run, date_ingested=datetime.date.today().isoformat(), construction=a.construction, hold_time_min=a.hold_min,
                shot_type=a.shot_type, photographer=a.photographer, device=a.device, edits_applied="none (original)", rights_owner=a.rights_owner, identifiable_people=a.people,
                exif_datetime=exif_dt(dst), edited_path="", web_export_path="", **m))
            existing.add(h); added.append(pid)
    # near-duplicate screening
    allr = list(csv.DictReader(open(prov, encoding="utf-8")))
    for i, r in enumerate(allr):
        for s in allr[:i]:
            if r["phash"] and s["phash"] and (imagehash.hex_to_hash(r["phash"]) - imagehash.hex_to_hash(s["phash"])) <= 4 and r["run_id"] == s["run_id"]:
                print(f"NEAR-DUPLICATE? {r['photo_id']} ~ {s['photo_id']}")
    return added

def selftest():
    tmp = tempfile.mkdtemp(); src = os.path.join(tmp, "s"); os.makedirs(src)
    rng = np.random.default_rng(1)
    sharp = (rng.integers(0, 255, (1600, 2000, 3))).astype("uint8"); Image.fromarray(sharp).save(f"{src}/sharp.jpg", quality=95)
    Image.fromarray(np.full((1600, 2000, 3), 128, "uint8")).save(f"{src}/flat.jpg")
    class A: run="SELFTEST"; construction="A"; hold_min="0"; shot_type="top"; photographer="test"; device="synthetic"; rights_owner="test"; people="none"
    root = os.path.join(tmp, "o"); prov = os.path.join(root, "p.csv"); os.makedirs(root)
    added = ingest(src, A, root, prov); r = list(csv.DictReader(open(prov)))
    assert len(added) == 2 and any("POSSIBLE_BLUR" in x["qa_flags"] for x in r) and any(x["qa_flags"] == "none" or "BLUR" not in x["qa_flags"] for x in r)
    assert ingest(src, A, root, prov) == [], "duplicates must be skipped"
    assert all(not os.access(x["original_path"], os.W_OK) or os.geteuid() == 0 for x in r)
    print("selftest ok: separation, SHA-256 dedupe, blur flag, read-only originals"); shutil.rmtree(tmp)

if __name__ == "__main__":
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest="cmd")
    i = s.add_parser("ingest"); i.add_argument("src"); i.add_argument("--run", required=True)
    for k, d in (("construction","NOT RECORDED"),("hold-min","NOT RECORDED"),("shot-type","NOT RECORDED"),("photographer","NOT RECORDED"),("device","NOT RECORDED"),("rights-owner","NOT RECORDED"),("people","NOT RECORDED")): i.add_argument("--"+k, default=d)
    s.add_parser("report"); s.add_parser("selftest")
    a = p.parse_args()
    if a.cmd == "ingest": print("ingested:", ingest(a.src, a))
    elif a.cmd == "selftest": selftest()
    else:
        r = rows(); print(f"{len(r)} photos ingested" if r else "NO PHOTOS INGESTED (nothing physical has been supplied)")
        for x in r: print(x["photo_id"], x["construction"], x["hold_time_min"], x["qa_flags"])
