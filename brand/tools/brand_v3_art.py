#!/usr/bin/env python3
"""Brand v3 art helpers (PROVISIONAL concept art; flat vector). Palette, secondary crest, wheat/mango/leaf motifs, BADSHAH and AMBA HAZE label wraps.
Labels use NO verified beverage specification other than: BADSHAH = hefeweizen (existing identity), AMBA HAZE = mango-forward juicy IPA working concept.
ABV, volume, ingredients, certifications, barcode, government/regulatory text are PLACEHOLDERS in boxes. No ™/®. Text on art is real type from Instrument Serif / Inter."""
import math, os, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import logo_courtyard_v2 as L
from logo_explorations import leaf_path

ROOT = L.ROOT
FONTS = ROOT / "website/dist/fonts"
OUTV3 = ROOT / "visuals/brand-v3"
EXE = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

PAL = dict(forest="#12372A", forest_deep="#0C261D", gold="#B8923A", gold_lt="#D5B565", ivory="#F4EDDC", terra="#B8552F", saffron="#DB8B2E", terra_deep="#9E4524", charcoal="#2A2623", leaf="#4F7A3A")
PALETTE = [("Deep forest", PAL["forest"]), ("Antique gold", PAL["gold"]), ("Warm ivory", PAL["ivory"]), ("Terracotta", PAL["terra"]), ("Dark charcoal", PAL["charcoal"])]
SUPPORT = [("Forest deep", PAL["forest_deep"]), ("Gold light", PAL["gold_lt"]), ("Saffron (AMBA HAZE accent)", PAL["saffron"]), ("Leaf green", PAL["leaf"]), ("Terracotta deep (text panels)", PAL["terra_deep"])]


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4 for v in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return round((la + .05) / (lb + .05), 2)


def css_fonts():
    f = FONTS
    return (f'@font-face{{font-family:"Instrument Serif";src:url("file://{f}/instrument-serif-latin-400-normal.woff2")}}'
            f'@font-face{{font-family:"Instrument Serif";font-style:italic;src:url("file://{f}/instrument-serif-latin-400-italic.woff2")}}'
            f'@font-face{{font-family:Inter;font-weight:100 900;src:url("file://{f}/inter-latin-wght-normal.woff2")}}')


def render(svg, png, w, h, scale=1):
    """SVG string -> PNG via headless Chromium (window oversized then cropped, as elsewhere in this repo)."""
    html = Path(str(png) + ".html")
    html.write_text(f'<!doctype html><meta charset=utf-8><style>{css_fonts()}html,body{{margin:0;background:transparent}}svg{{display:block}}</style>{svg}')
    subprocess.run([EXE, "--headless", "--no-sandbox", "--disable-gpu", f"--force-device-scale-factor={scale}", f"--screenshot={png}", f"--window-size={w + 20},{h + 240}", "--hide-scrollbars", f"file://{html}"], capture_output=True, timeout=180)
    html.unlink()
    from PIL import Image
    Image.open(png).crop((0, 0, w * scale, h * scale)).save(png)


# ------------------------------------------------------------------ motifs
def wheat(h=300, col="#B8923A", grain=None):
    """Upright wheat ear, origin at stem base (0,0), growing up (negative y)."""
    g = grain or col
    out = [f'<path d="M0,0V{-h * .7:.1f}" stroke="{col}" stroke-width="{h * .016:.1f}" fill="none" stroke-linecap="round"/>']
    n = 7
    for i in range(n):
        y = -h * .38 - i * h * .085
        for side in (-1, 1):
            out.append(f'<path d="{leaf_path(side * h * .05, y, h * .15, h * .06, -90 + side * 38 + 90 - 90)}" fill="{g}"/>'.replace("-90 + 0", ""))
    out.append(f'<path d="{leaf_path(0, -h * .38 - n * h * .085 - h * .02, h * .15, h * .06, 90)}" fill="{g}"/>')
    return "".join(out)


def mango(cx, cy, s, body, shade, leaf, rot=-18):
    """Flat two-tone mango with a leaf; s ~ half-height."""
    b = f"M0,{-s:.1f}C{s * .72:.1f},{-s * 1.02:.1f} {s * 1.02:.1f},{-s * .3:.1f} {s * .86:.1f},{s * .38:.1f}C{s * .7:.1f},{s * .98:.1f} {-s * .15:.1f},{s * 1.12:.1f} {-s * .68:.1f},{s * .62:.1f}C{-s * 1.06:.1f},{s * .18:.1f} {-s * .74:.1f},{-s * .92:.1f} 0,{-s:.1f}Z"
    sh = f"M{s * .3:.1f},{-s * .8:.1f}C{s * 1.0:.1f},{-s * .5:.1f} {s * 1.1:.1f},{s * .3:.1f} {s * .62:.1f},{s * .76:.1f}C{s * .1:.1f},{s * 1.1:.1f} {-s * .5:.1f},{s * .95:.1f} {-s * .62:.1f},{s * .55:.1f}C{s * .1:.1f},{s * .62:.1f} {s * .72:.1f},{s * .1:.1f} {s * .3:.1f},{-s * .8:.1f}Z"
    lf = leaf_path(s * .34, -s * 1.0, s * .9, s * .34, -28)
    return f'<g transform="translate({cx},{cy}) rotate({rot})"><path d="{b}" fill="{body}"/><path d="{sh}" fill="{shade}"/><path d="{lf}" fill="{leaf}"/></g>'


def crest(c="#B8923A", bg=None, leaf="#B8923A", door="#B8552F", w=100):
    """Secondary symbol: arch outline holding a three-leaf botanical sprig over an ember doorway. 100x100 box."""
    d = L.ring(46, 6)
    lv = ""
    for ang, y, ln in ((-52, 44, 30), (52, 44, 30), (-40, 62, 26), (40, 62, 26), (-90 + 0, 28, 36)):
        x = 50 + (math.copysign(11, ang) if abs(ang) != 90 else 0)
        lv += f'<path d="{leaf_path(x, y, ln, 11, ang if abs(ang) != 90 else -90)}" fill="{leaf}"/>'
    stem = f'<path d="M50,92V30" stroke="{leaf}" stroke-width="3" fill="none" stroke-linecap="round"/>'
    return f'<g style="color:{c}"><path d="{d}" fill="{c}"/>{stem}{lv}</g>'


def lattice(x, y, w, h, col, size=34, op=.35, sw=1.4):
    """Generic diamond lattice band (decorative, geometric; cultural review pending before any claim about its origin)."""
    ln = []
    n = int(w / size) + 2
    for i in range(-1, n):
        ln.append(f'<path d="M{x + i * size},{y + h}L{x + i * size + h},{y}M{x + i * size},{y}L{x + i * size + h},{y + h}" stroke="{col}" stroke-width="{sw}" opacity="{op}" fill="none"/>')
    return f'<g clip-path="url(#lat{int(x)}_{int(y)})"><clipPath id="lat{int(x)}_{int(y)}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>{"".join(ln)}</g>'


# ------------------------------------------------------------------ label wraps: 2070 x 1000 (10 px / mm: 207 mm x 100 mm print area, assumed can; size TBD)
WRAP_W, WRAP_H = 2070, 1000
FRONT_CX = 1035


def placeholder(x, y, w, h, text, col, op=.7, size=22):
    import textwrap
    lines = textwrap.wrap(text, max(8, int(w / (size * .56))))
    y0 = y + h / 2 - (len(lines) - 1) * size * .6 + size * .35
    tx = "".join(f'<tspan x="{x + w / 2}" y="{y0 + i * size * 1.25:.1f}">{ln}</tspan>' for i, ln in enumerate(lines))
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{col}" stroke-width="2" stroke-dasharray="10 7" opacity="{op}"/><text text-anchor="middle" font-family="Inter" font-size="{size}" fill="{col}" opacity="{op}">{tx}</text>'


def nasha_header(cx, y, w, col, acc):
    inner, ww, hh = L.wordmark(L.SMALL)
    k = w / ww
    return f'<g transform="translate({cx - w / 2},{y}) scale({k:.4f})" style="color:{col};--accent:{acc}">{inner}</g>', hh * k


def back_panels(bg, fg, acc, name, desc):
    s = []
    s.append(f'<text x="120" y="190" font-family="Instrument Serif" font-size="58" fill="{fg}">{name}</text>')
    s.append(f'<text x="120" y="240" font-family="Inter" font-size="21" fill="{fg}" opacity=".85" letter-spacing="1">{desc}</text>')
    s.append(placeholder(120, 300, 400, 150, "TASTING NOTES — TBD (no tasting done)", fg))
    s.append(placeholder(120, 480, 400, 150, "INGREDIENTS — TBD (unverified)", fg))
    s.append(placeholder(120, 660, 400, 110, "ABV / VOLUME — TBD", fg))
    s.append(placeholder(1570, 150, 380, 130, "CERTIFICATIONS — NONE CLAIMED", fg))
    s.append(placeholder(1570, 310, 380, 230, "REGULATORY / GOVERNMENT WARNING — TBD (needs compliance review)", fg))
    s.append(placeholder(1570, 570, 260, 170, "BARCODE — TBD", fg))
    s.append(f'<text x="1570" y="830" font-family="Inter" font-size="19" fill="{fg}" opacity=".8">CONCEPT ARTWORK</text><text x="1570" y="858" font-family="Inter" font-size="19" fill="{fg}" opacity=".8">NOT A REAL PRODUCT · NOT CLEARED</text>')
    return "".join(s)


def badshah_wrap():
    P = PAL
    s = [f'<rect width="{WRAP_W}" height="{WRAP_H}" fill="{P["forest"]}"/>']
    s.append(lattice(0, 0, WRAP_W, 60, P["gold"], 30, .5) + lattice(0, WRAP_H - 60, WRAP_W, 60, P["gold"], 30, .5))
    s.append(f'<rect x="0" y="60" width="{WRAP_W}" height="4" fill="{P["gold"]}"/><rect x="0" y="{WRAP_H - 64}" width="{WRAP_W}" height="4" fill="{P["gold"]}"/>')
    # front: gateway of concentric arches framing a wheat ear, name below
    cx = FRONT_CX
    for i, (half, sw) in enumerate(((300, 8), (268, 3), (240, 3))):
        top = 110 + i * 0
        s.append(f'<path d="M{cx - half},650V{360 - 0}A{half},{half} 0 0 1 {cx + half},{360}V650" fill="none" stroke="{P["gold"]}" stroke-width="{sw}"/>'.replace("A300", "A300"))
    s.append(f'<path d="M{cx - 232},650V360A232,232 0 0 1 {cx + 232},360V650Z" fill="{P["forest_deep"]}"/>')
    s.append(f'<g transform="translate({cx},640)">{wheat(330, P["gold"])}</g>')
    hdr, hh = nasha_header(cx, 215, 250, P["ivory"], P["saffron"])
    s.append(hdr)
    s.append(f'<text x="{cx}" y="770" text-anchor="middle" font-family="Instrument Serif" font-size="128" fill="{P["gold_lt"]}" letter-spacing="14">BADSHAH</text>')
    s.append(f'<text x="{cx}" y="830" text-anchor="middle" font-family="Inter" font-weight="600" font-size="28" fill="{P["ivory"]}" letter-spacing="14">HEFEWEIZEN</text>')
    s.append(f'<rect x="{cx - 150}" y="858" width="300" height="2" fill="{P["gold"]}"/>')
    s.append(placeholder(cx - 170, 872, 340, 48, "ABV · VOLUME — TBD", P["ivory"], .65))
    s.append(back_panels(P["forest"], P["ivory"], P["gold"], "BADSHAH", "HEFEWEIZEN · WORKING CONCEPT"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WRAP_W} {WRAP_H}" width="{WRAP_W}" height="{WRAP_H}">{"".join(s)}</svg>'


def amba_wrap():
    P = PAL
    s = [f'<rect width="{WRAP_W}" height="{WRAP_H}" fill="{P["ivory"]}"/>']
    cx = FRONT_CX
    # flowing botanical field behind the front panel: long mango leaves radiating from the lower centre
    for k in range(-4, 5):
        ang = -90 + k * 17
        col = (P["leaf"], P["forest"], P["terra"], P["gold"])[abs(k) % 4]
        s.append(f'<path d="{leaf_path(cx + math.cos(math.radians(ang)) * 215, 650 + math.sin(math.radians(ang)) * 215, 330, 84, ang)}" fill="{col}" opacity=".92"/>')
    for k in (-1, 1):
        s.append(f'<path d="{leaf_path(cx + k * 330, 590, 300, 70, -90 + k * 62)}" fill="{P["forest"]}" opacity=".9"/>')
    s.append(mango(cx - 120, 520, 150, P["saffron"], P["terra"], P["leaf"], -16) + mango(cx + 130, 560, 125, P["terra"], "#8E3E20", P["forest"], 14) + mango(cx + 10, 430, 100, P["gold_lt"], P["saffron"], P["leaf"], 4))
    hdr, hh = nasha_header(cx, 60, 250, P["forest"], P["terra"])
    s.append(f'<rect x="{cx - 330}" y="690" width="660" height="210" fill="{P["forest"]}"/>')
    s.append(hdr)
    s.append(f'<text x="{cx}" y="796" text-anchor="middle" font-family="Instrument Serif" font-style="italic" font-size="132" fill="{P["ivory"]}">Amba Haze</text>')
    s.append(f'<text x="{cx}" y="846" text-anchor="middle" font-family="Inter" font-weight="600" font-size="26" fill="{P["saffron"]}" letter-spacing="10">JUICY MANGO IPA</text>')
    s.append(placeholder(cx - 170, 858, 340, 38, "ABV · VOLUME — TBD", P["ivory"], .75))
    s.append(f'<rect x="0" y="0" width="{WRAP_W}" height="22" fill="{P["terra"]}"/><rect x="0" y="{WRAP_H - 22}" width="{WRAP_W}" height="22" fill="{P["terra"]}"/>')
    s.append(back_panels(P["ivory"], P["forest"], P["terra"], "AMBA HAZE", "MANGO-FORWARD HAZY IPA · WORKING CONCEPT"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WRAP_W} {WRAP_H}" width="{WRAP_W}" height="{WRAP_H}">{"".join(s)}</svg>'


def main():
    OUTV3.mkdir(parents=True, exist_ok=True)
    (OUTV3 / "labels").mkdir(exist_ok=True)
    for name, fn in (("badshah", badshah_wrap), ("amba-haze", amba_wrap)):
        svg = fn()
        (OUTV3 / "labels" / f"{name}-wrap.svg").write_text(svg)
        render(svg, OUTV3 / "labels" / f"{name}-wrap.png", WRAP_W, WRAP_H)
    print("labels written")


if __name__ == "__main__":
    main()
