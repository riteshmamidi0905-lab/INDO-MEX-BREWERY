#!/usr/bin/env python3
"""True-pixel comparison: Courtyard wordmark vs glass-inspired G1/G2 at cap heights 16/24/32/96/256 px (+ 4x nearest-neighbour zoom of 16/24/32)."""
import sys, math, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parent))
import logo_glass_a as G, glyph_readability as R

BG = (239, 231, 214)


def tile(name, px):
    inner, w, h = G.VARIANTS[name](px <= 96)
    im = R.render_svg(inner, w, h, px, f"b_{name}_{px}")
    # recolour white->BG for the board
    px_ = im.convert("RGB"); out = Image.new("RGB", px_.size, BG)
    mask = px_.convert("L").point(lambda v: 255 - v)
    out.paste(Image.new("RGB", px_.size, (20, 17, 16)), mask=mask)
    return out


def main():
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 15)
    fb = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 17)
    names = list(G.VARIANTS)
    sizes = G.SIZES
    tiles = {(n, p): tile(n, p) for n in names for p in sizes}
    rowh = [max(tiles[(n, 256)].height, 1) + 70 for n in names]
    W = 90 + sum(tiles[(names[0], p)].width + 40 for p in sizes) + 60
    H = 60 + sum(rowh) + 330
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((24, 18), "Courtyard wordmark vs glass-inspired variation — true pixel sizes (cap height 16 / 24 / 32 / 96 / 256 px). PROVISIONAL, neither is final.", font=fb, fill=(20, 17, 16))
    y = 60
    for n, rh in zip(names, rowh):
        d.text((24, y + rh - 52), n, font=fb, fill=(20, 17, 16))
        x = 120
        for p in sizes:
            t = tiles[(n, p)]
            img.paste(t, (x, y + rh - 40 - t.height))
            d.text((x, y + rh - 32), f"{p}px", font=f, fill=(110, 100, 90))
            x += t.width + 40
        y += rh
    d.text((24, y + 8), "4× nearest-neighbour zoom of the 16 / 24 / 32 px renders (to inspect the pixels, not how they look at 1×):", font=f, fill=(60, 55, 50))
    y += 40
    for n in names:
        x = 120
        d.text((24, y + 30), n, font=f, fill=(20, 17, 16))
        for p in (16, 24, 32):
            t = tiles[(n, p)].resize((tiles[(n, p)].width * 4, tiles[(n, p)].height * 4), Image.NEAREST)
            if x + t.width < W:
                img.paste(t, (x, y)); x += t.width + 30
        y += 100
    img.save(G.OUT / "comparison-true-size.png")
    print(img.size)


if __name__ == "__main__":
    main()
