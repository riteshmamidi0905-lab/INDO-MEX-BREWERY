#!/usr/bin/env python3
"""Derive web source images from approved/provisional originals in visuals/generated/.
Deterministic and non-generative: crops, a scripted NASHA wordmark overlay on the blank monument sign, and light tone work.
Output: visuals/web-source/*.webp (kept in git). Run: python3 website/tools/make_sources.py
Requires Pillow; the wordmark font is Instrument Serif (OFL) converted from website/src/fonts via fontTools."""
import os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN, OUT = os.path.join(ROOT, "visuals/generated"), os.path.join(ROOT, "visuals/web-source")
os.makedirs(OUT, exist_ok=True)

def font(size):
    ttf = "/tmp/instrument.ttf"
    if not os.path.exists(ttf):
        from fontTools.ttLib import TTFont
        t = TTFont(os.path.join(ROOT, "website/src/fonts/instrument-serif-latin-400-normal.woff2")); t.flavor = None; t.save(ttf)
    return ImageFont.truetype(ttf, size)

def hero_night():
    """ARC-02-A night exterior + scripted TEMPORARY typographic wordmark (plain tracked capitals; no rule, no mark; CONCEPT, NOT OFFICIAL; logo governance: brand/NASHA-LOGO-GOVERNANCE.md) on the blank monument sign (sign box measured at about x 995-1088, y 698-785)."""
    im = Image.open(os.path.join(GEN, "ARC-02-A.webp")).convert("RGB")
    box = (995, 698, 1088, 785)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    txt = "NASHA"; f = font(23)
    # tracked capitals, centred in the sign face
    gap = 4; widths = [d.textlength(c, font=f) for c in txt]; total = sum(widths) + gap * (len(txt) - 1)
    x = box[0] + (box[2] - box[0] - total) / 2; y = box[1] + 26
    for c, w in zip(txt, widths):
        d.text((x, y), c, font=f, fill=(243, 236, 221, 255)); x += w + gap
    glow = layer.filter(ImageFilter.GaussianBlur(6)); glow = Image.blend(Image.new("RGBA", im.size), glow, 0.55)
    base = im.convert("RGBA"); base = Image.alpha_composite(base, glow); base = Image.alpha_composite(base, layer)
    base.convert("RGB").save(os.path.join(OUT, "HERO-NIGHT.webp"), quality=92, method=6)

def copy(src, dst, q=92):
    Image.open(os.path.join(GEN, src)).convert("RGB").save(os.path.join(OUT, dst), quality=q, method=6)

hero_night()
copy("ARC-01-D.png", "EXT-DAY.webp")
copy("BRW-01-R1-V1.webp", "BREWERY-HALL.webp")
copy("ARC-01-E-external-crop-attempt1.webp", "BREWERY-GLASS.webp")
print("sources written:", sorted(os.listdir(OUT)))
