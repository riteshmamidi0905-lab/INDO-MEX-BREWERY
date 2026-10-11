"""Responsive image pipeline: crop (desktop + mobile composition), resize, encode AVIF/WebP/JPEG. Pillow only.
Cache lives in website/.imgcache (git-ignored); output goes to dist/images/."""
import hashlib, json, os, shutil
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CACHE = os.path.join(HERE, ".imgcache")
D_WIDTHS = [640, 1024, 1600, 1920]
M_WIDTHS = [480, 800]
FALLBACK_D, FALLBACK_M = 1024, 800

def _crop_box(im, crop):
    w, h = im.size
    if not crop: return (0, 0, w, h)
    x0, y0, x1, y1 = [float(v) for v in crop.split(",")]
    return (round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h))

def _mobile_box(box, ar, fx):
    """Portrait crop with aspect ar=(w,h) from the desktop box, horizontally centred on focus fx (0-1 of box width)."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    aw, ah = ar
    cw = min(bw, round(bh * aw / ah)); ch = round(cw * ah / aw)
    if ch > bh: ch = bh; cw = round(ch * aw / ah)
    cx = x0 + fx * bw
    left = max(x0, min(x1 - cw, round(cx - cw / 2)))
    return (left, y0, left + cw, y0 + ch)

def _save(im, path, fmt):
    if fmt == "avif": im.save(path, "AVIF", quality=48, speed=6)
    elif fmt == "webp": im.save(path, "WEBP", quality=74, method=6)
    else: im.convert("RGB").save(path, "JPEG", quality=74, optimize=True, progressive=True)

def build_raster(row, out_dir):
    """row: manifest dict with id, source_file (path from repo root), src_crop, mobile_ar ('4:5'), mobile_focus_x. Returns metadata."""
    src = os.path.join(REPO, row["source_file"])
    key = hashlib.sha1(usedforsecurity=False, string=(open(src, "rb").read() + json.dumps([row["src_crop"], row["mobile_ar"], row["mobile_focus_x"], D_WIDTHS, M_WIDTHS]).encode())).hexdigest()[:12]
    cdir = os.path.join(CACHE, row["id"] + "-" + key)
    meta_path = os.path.join(cdir, "meta.json")
    if not os.path.exists(meta_path):
        os.makedirs(cdir, exist_ok=True)
        im = Image.open(src).convert("RGB")
        dbox = _crop_box(im, row["src_crop"])
        ar = tuple(int(v) for v in row["mobile_ar"].split(":"))
        mbox = _mobile_box(dbox, ar, float(row["mobile_focus_x"] or .5))
        meta = {"d": {"w": dbox[2] - dbox[0], "h": dbox[3] - dbox[1], "files": []}, "m": {"w": mbox[2] - mbox[0], "h": mbox[3] - mbox[1], "files": []}}
        for tag, box, widths in (("d", dbox, D_WIDTHS), ("m", mbox, M_WIDTHS)):
            base = im.crop(box); bw, bh = base.size
            ws = sorted({min(w, bw) for w in widths})
            for w in ws:
                h = round(bh * w / bw); r = base.resize((w, h), Image.LANCZOS)
                for fmt in ("avif", "webp", "jpg"):
                    if fmt == "jpg" and w > (FALLBACK_D if tag == "d" else FALLBACK_M): continue
                    fn = f"{row['id']}-{tag}-{w}.{fmt}"; _save(r, os.path.join(cdir, fn), fmt)
                    meta[tag]["files"].append({"fmt": fmt, "w": w, "h": h, "file": fn})
        json.dump(meta, open(meta_path, "w"))
    meta = json.load(open(meta_path))
    os.makedirs(out_dir, exist_ok=True)
    for tag in ("d", "m"):
        for f in meta[tag]["files"]:
            shutil.copy(os.path.join(cdir, f["file"]), os.path.join(out_dir, f["file"]))
    return meta

def picture_html(row, meta, alt, sizes_d="100vw", eager=False, cls=""):
    def srcset(tag, fmt):
        fs = [f for f in meta[tag]["files"] if f["fmt"] == fmt]
        return ", ".join(f'images/{f["file"]} {f["w"]}w' for f in sorted(fs, key=lambda x: x["w"]))
    jd = [f for f in meta["d"]["files"] if f["fmt"] == "jpg"]
    fb = sorted(jd, key=lambda x: abs(x["w"] - FALLBACK_D))[0]
    mq = "(max-width: 700px)"
    load = 'fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
    return (f'<picture>'
            f'<source media="{mq}" type="image/avif" srcset="{srcset("m", "avif")}" sizes="100vw">'
            f'<source media="{mq}" type="image/webp" srcset="{srcset("m", "webp")}" sizes="100vw">'
            f'<source media="{mq}" type="image/jpeg" srcset="{srcset("m", "jpg")}" sizes="100vw">'
            f'<source type="image/avif" srcset="{srcset("d", "avif")}" sizes="{sizes_d}">'
            f'<source type="image/webp" srcset="{srcset("d", "webp")}" sizes="{sizes_d}">'
            f'<img src="images/{fb["file"]}" srcset="{srcset("d", "jpg")}" sizes="{sizes_d}" width="{meta["d"]["w"]}" height="{meta["d"]["h"]}" alt="{alt}" {load}>'
            f'</picture>')
