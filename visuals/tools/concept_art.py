"""Procedural ORIGINAL concept art for NASHA GOODS and beer packaging presentations (SVG, then PNG via headless Chromium).

CONCEPT VISUALIZATION ONLY: not photographs, not manufactured products. Drawn by code in this repository; no third-party artwork, no
trace of any existing artwork, no logo (D-66). Palette comes from brand/NASHA-IDENTITY-SYSTEM.md. Seeds and parameters are fixed, so the
output is reproducible.   python3 visuals/tools/concept_art.py   (writes visuals/concepts/*.svg, *.png and PROVENANCE.json)
"""
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "visuals" / "concepts"
C = dict(soot="#141110", char="#241E1B", bone="#F3ECDD", marigold="#E8870E", limestone="#E4DAC6", stainless="#C9CCCB", smoke="#9A9087",
         copper="#C47A45", indigo="#1A2142", dusk="#2B3563", herb="#7D9A45", herbink="#3F5A1E", hibiscus="#9B2447", tamarind="#5A3A25", straw="#E9C46A")
FONT = "font-family=\"Instrument Serif, Georgia, 'Times New Roman', serif\""


def svg(w, h, body, bg=None, title=""):
    rect = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{title}">'
            f'<title>{title}</title>{rect}{body}</svg>')


def p(x, y):
    return f"{x:.1f},{y:.1f}"


# ---------------------------------------------------------------- architecture
def round_arch(cx, base, half, spring, stroke, sw, fill="none"):
    return f'<path d="M{p(cx - half, base)} V{p(0, spring).split(",")[1]} A{half:.1f},{half:.1f} 0 0 1 {p(cx + half, spring)} V{base:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'


def cusped_arch(cx, base, half, spring, stroke, sw, fill="none", lobes=11):
    pts = [(cx - half * math.cos(math.pi * i / (lobes - 1) ), spring - half * math.sin(math.pi * i / (lobes - 1))) for i in range(lobes)]
    d = f"M{p(cx - half, base)} V{spring:.1f}"
    for a, b in zip(pts, pts[1:]):
        r = math.dist(a, b) * 0.56
        d += f" A{r:.1f},{r:.1f} 0 0 1 {p(*b)}"
    d += f" V{base:.1f}"
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'


def courtyard():
    w, h = 1000, 1240
    b = []
    base = 770
    # five nested thresholds, front (round, hacienda-like) to back (multifoil, Mughal-like): the outer arch is the zaguan, the inner ones the chowk
    layers = [(430, "round", C["limestone"], 5), (350, "cusped", C["limestone"], 4.5), (270, "cusped", C["stainless"], 4), (195, "cusped", C["smoke"], 3.5), (125, "round", C["smoke"], 3)]
    fills = [C["char"], C["indigo"], C["dusk"], C["indigo"], C["soot"]]
    for i, ((half, kind, col, sw), fill) in enumerate(zip(layers, fills)):
        top = base - 520 + i * 52
        fn = round_arch if kind == "round" else cusped_arch
        b.append(fn(500, base - i * 24, half, top + half, col, sw, fill))
    # threshold sill and floor in perspective (vanishing point inside the innermost opening)
    b.append(f'<path d="M70 {base + 70} H930" stroke="{C["limestone"]}" stroke-width="5"/>')
    for xx in range(-4, 5):
        b.append(f'<path d="M{p(500 + xx * 108, base + 70)} L{p(500 + xx * 14, base - 22)}" stroke="{C["smoke"]}" stroke-width="2" opacity=".55"/>')
    for k, yy in enumerate([base - 4, base + 16, base + 36, base + 54]):
        b.append(f'<path d="M{p(140 + k * 30, yy)} H{860 - k * 30}" stroke="{C["smoke"]}" stroke-width="1.6" opacity=".5"/>')
    # the single marigold accent: daylight falling through the open roof onto the floor
    b.append(f'<polygon points="{p(585, base + 62)} {p(800, base + 62)} {p(700, base - 14)} {p(572, base - 14)}" fill="{C["marigold"]}"/>')
    # plan view: the same thresholds seen from above (concentric squares, openings aligned)
    cy = 985
    for k, sz in enumerate([170, 126, 84, 44]):
        col = C["limestone"] if k < 3 else C["marigold"]
        gap = sz * 0.32
        x0, x1, y0, y1 = 500 - sz / 2, 500 + sz / 2, cy - sz / 2, cy + sz / 2
        b.append(f'<path d="M{p(500 - gap / 2, y1)} H{x0:.1f} V{y0:.1f} H{x1:.1f} V{y1:.1f} H{p(500 + gap / 2, 0).split(",")[0]}" fill="none" stroke="{col}" stroke-width="3.5"/>')
    b.append(f'<text x="500" y="1196" text-anchor="middle" {FONT} font-size="30" letter-spacing="9" fill="{C["smoke"]}">THE ROOM WITH NO ROOF</text>')
    return svg(w, h, "".join(b), C["soot"], "Concept art: Hoodie 01 The Courtyard back graphic. Nested arches, one marigold patch of daylight, plan view of thresholds.")


# ---------------------------------------------------------------- botany
def leaf(x, y, ang, L, W, fill, vein=None, stroke=None):
    """Lanceolate leaf from base (x,y) pointing along ang (degrees)."""
    a = math.radians(ang)
    tx, ty = x + L * math.cos(a), y + L * math.sin(a)
    nx, ny = -math.sin(a), math.cos(a)
    c1 = (x + L * .3 * math.cos(a) + W * nx, y + L * .3 * math.sin(a) + W * ny)
    c2 = (x + L * .72 * math.cos(a) + W * .7 * nx, y + L * .72 * math.sin(a) + W * .7 * ny)
    d1 = (x + L * .72 * math.cos(a) - W * .7 * nx, y + L * .72 * math.sin(a) - W * .7 * ny)
    d2 = (x + L * .3 * math.cos(a) - W * nx, y + L * .3 * math.sin(a) - W * ny)
    s = f'<path d="M{p(x, y)} C{p(*c1)} {p(*c2)} {p(tx, ty)} C{p(*d1)} {p(*d2)} {p(x, y)}Z" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="1.5"' if stroke else "") + "/>"
    if vein:
        s += f'<path d="M{p(x, y)} L{p(tx, ty)}" stroke="{vein}" stroke-width="2" fill="none" stroke-linecap="round"/>'
    return s


def curry_leaf(x, y, h):
    b = [f'<path d="M{p(x, y)} C{p(x - 10, y - h * .4)} {p(x + 12, y - h * .7)} {p(x, y - h)}" stroke="{C["herbink"]}" stroke-width="5" fill="none" stroke-linecap="round"/>']
    for i in range(9):
        t = i / 8
        yy = y - h * (0.1 + 0.8 * t)
        xx = x + math.sin(t * 3) * 6
        ln = 120 - 60 * t
        b.append(leaf(xx, yy, -160 + t * 8, ln, 15, C["herb"], C["herbink"]))
        b.append(leaf(xx, yy, -20 - t * 8, ln, 15, C["herb"], C["herbink"]))
    b.append(leaf(x, y - h, -92, 70, 13, C["herb"], C["herbink"]))
    return "".join(b)


def chile_plant(x, y):
    b = [f'<path d="M{p(x, y)} C{p(x - 8, y - 150)} {p(x + 10, y - 260)} {p(x, y - 380)}" stroke="{C["herbink"]}" stroke-width="6" fill="none" stroke-linecap="round"/>']
    for i, (yo, ang, ln) in enumerate([(70, -150, 120), (110, -30, 130), (160, -155, 110), (210, -25, 120), (270, -145, 95), (320, -40, 90), (380, -95, 80)]):
        b.append(leaf(x, y - yo, ang, ln, 34, C["herb"], C["herbink"]))
    for (yo, side, ln) in [(150, 1, 170), (240, -1, 150), (300, 1, 120)]:        # pods: botanical, slightly curved, with calyx and pedicel
        px, py = x + side * 26, y - yo
        b.append(f'<path d="M{p(x, py)} Q{p(x + side * 18, py + 10)} {p(px, py + 26)}" stroke="{C["herbink"]}" stroke-width="3" fill="none"/>')
        b.append(f'<path d="M{p(px - 14, py + 26)} C{p(px - 16, py + 26 + ln * .55)} {p(px + side * 8, py + 26 + ln * .9)} {p(px + side * 6, py + 26 + ln)} C{p(px + 20, py + 26 + ln * .8)} {p(px + 18, py + 26 + ln * .4)} {p(px + 14, py + 26)} Z" fill="{C["hibiscus"]}"/>')
        b.append(f'<path d="M{p(px - 18, py + 26)} Q{p(px, py + 12)} {p(px + 18, py + 26)} Q{p(px, py + 40)} {p(px - 18, py + 26)}Z" fill="{C["herbink"]}"/>')
    return "".join(b)


def maize_leaf(x, y, k=0.5):
    X = lambda dx: x + dx * k
    d = f"M{p(x, y)} C{p(X(20), y - 250)} {p(X(150), y - 420)} {p(X(330), y - 430)} C{p(X(190), y - 360)} {p(X(90), y - 200)} {p(X(34), y)} Z"
    return (f'<path d="{d}" fill="{C["herb"]}" stroke="{C["herbink"]}" stroke-width="1.5"/>'
            f'<path d="M{p(X(16), y)} C{p(X(40), y - 250)} {p(X(160), y - 400)} {p(X(330), y - 430)}" stroke="{C["herbink"]}" stroke-width="3" fill="none"/>')


def calyx(x, y, r):
    b = []
    for i in range(5):
        b.append(leaf(x, y, -90 + (i - 2) * 34, r, 18, C["hibiscus"], C["tamarind"]))
    b.append(f'<circle cx="{x}" cy="{y}" r="{r * .16:.1f}" fill="{C["tamarind"]}"/>')
    return "".join(b)


def marigold(x, y, r):
    b = []
    for ring, (rr, n, col) in enumerate([(r, 18, C["marigold"]), (r * .78, 16, "#F0A23C"), (r * .56, 12, C["marigold"]), (r * .34, 9, "#F0A23C")]):
        for i in range(n):
            a = 2 * math.pi * (i + ring * .5) / n
            b.append(f'<ellipse cx="{x + math.cos(a) * rr * .5:.1f}" cy="{y + math.sin(a) * rr * .5:.1f}" rx="{rr * .3:.1f}" ry="{rr * .18:.1f}" transform="rotate({math.degrees(a):.1f} {x + math.cos(a) * rr * .5:.1f} {y + math.sin(a) * rr * .5:.1f})" fill="{col}" stroke="{C["tamarind"]}" stroke-width=".8" opacity=".95"/>')
    b.append(f'<circle cx="{x}" cy="{y}" r="{r * .12:.1f}" fill="{C["tamarind"]}"/>')
    return "".join(b)


def two_worlds():
    w, h = 1000, 1240
    b = [f'<rect x="40" y="40" width="920" height="1160" fill="none" stroke="{C["smoke"]}" stroke-width="2"/>']
    b.append(curry_leaf(310, 930, 560))
    b.append(leaf(110, 1000, -82, 360, 56, C["herb"], C["herbink"], C["herbink"]))            # mango leaf (lanceolate)
    for k in range(1, 8):
        yy = 1000 - k * 42
        b.append(f'<path d="M{p(110 + (1000 - yy) * .13, yy)} l{p(60, -20)}" stroke="{C["herbink"]}" stroke-width="1.5" opacity=".6"/>')
    b.append(chile_plant(700, 950))
    b.append(maize_leaf(800, 990, 0.45))
    b.append(calyx(500, 1040, 90))
    b.append(marigold(500, 360, 95))
    b.append(f'<path d="M500 455 C500 560 500 700 500 940" stroke="{C["herbink"]}" stroke-width="4" fill="none"/>' + leaf(500, 600, -140, 120, 30, C["herb"], C["herbink"]) + leaf(500, 700, -40, 120, 30, C["herb"], C["herbink"]))
    # ruler: same scale for both floras
    b.append(f'<path d="M120 1130 H880" stroke="{C["limestone"]}" stroke-width="3"/>' + "".join(f'<path d="M{120 + i * 38} 1130 v{16 if i % 5 == 0 else 9}" stroke="{C["limestone"]}" stroke-width="2"/>' for i in range(21)))
    b.append(f'<text x="500" y="1176" text-anchor="middle" {FONT} font-size="26" letter-spacing="8" fill="{C["smoke"]}">TWO FLORAS · ONE SCALE · NO CLAIMS</text>')
    return svg(w, h, "".join(b), C["soot"], "Concept art: Hoodie 02 Two Worlds back graphic. Curry leaf, mango leaf, chile plant, maize leaf, roselle calyx and a single marigold, drawn at one scale.")


# ---------------------------------------------------------------- can presentations
def can(x, y, w, h, grad, label_art, name, sub, txt):
    g = f"g{x}"
    return (f'<defs><linearGradient id="{g}" x1="0" x2="1"><stop offset="0" stop-color="{grad[0]}"/><stop offset=".35" stop-color="{grad[1]}"/><stop offset="1" stop-color="{grad[2]}"/></linearGradient></defs>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="34" fill="url(#{g})"/>'
            f'<rect x="{x + 10}" y="{y - 18}" width="{w - 20}" height="26" rx="10" fill="{C["stainless"]}"/>'
            f'<rect x="{x + 10}" y="{y + h - 8}" width="{w - 20}" height="26" rx="10" fill="{C["stainless"]}"/>'
            f'<text x="{x + w / 2}" y="{y + 120}" text-anchor="middle" {FONT} font-size="64" letter-spacing="6" fill="{txt}">{name}</text>'
            f'<text x="{x + w / 2}" y="{y + 168}" text-anchor="middle" {FONT} font-size="24" letter-spacing="6" fill="{txt}">{sub}</text>'
            + label_art +
            f'<text x="{x + w / 2}" y="{y + h - 44}" text-anchor="middle" {FONT} font-size="16" letter-spacing="3" fill="{txt}">CONCEPT · NOT A REAL PRODUCT</text>'
            f'<rect x="{x + w * .88}" y="{y + 40}" width="14" height="{h - 80}" rx="7" fill="#ffffff" opacity=".12"/>')


def cans():
    w, h = 1600, 1000
    c1, c2, base = 360, 1240, 800
    badshah = ""
    for i in range(5):                                       # stacked thresholds (the NASHA arch device), centred on the can
        half = 150 - i * 26
        badshah += round_arch(c1, base, half, base - 300 + i * 46 + half - 150 + 150 - half, C["soot"], 3).replace('stroke-width="3"', 'stroke-width="3" opacity=".4"')
    badshah += leaf(c1, base, -90, 300, 50, C["herbink"], C["soot"])
    paapi = f'<path d="M{c2} {base} V470" stroke="{C["tamarind"]}" stroke-width="5"/>'
    for i in range(8):                                       # wheat ear: original geometric grains on a stalk
        yy = 480 + i * 36
        paapi += f'<ellipse cx="{c2 - 20}" cy="{yy}" rx="13" ry="26" transform="rotate(-24 {c2 - 20} {yy})" fill="{C["tamarind"]}" opacity=".85"/>'
        paapi += f'<ellipse cx="{c2 + 20}" cy="{yy + 18}" rx="13" ry="26" transform="rotate(24 {c2 + 20} {yy + 18})" fill="{C["tamarind"]}" opacity=".85"/>'
    paapi += f'<ellipse cx="{c2}" cy="450" rx="12" ry="28" fill="{C["tamarind"]}" opacity=".85"/>'
    body = (f'<rect y="760" width="{w}" height="240" fill="{C["char"]}"/>'
            + can(100, 130, 520, 760, (C["copper"], "#F0A23C", "#D9892B"), badshah, "BADSHAH", "MANGO HAZY IPA", C["soot"])
            + can(980, 130, 520, 760, (C["straw"], "#F3D98A", "#E2B84F"), paapi, "PAAPI", "HEFEWEIZEN", C["soot"])
            + f'<text x="800" y="948" text-anchor="middle" {FONT} font-size="22" letter-spacing="6" fill="{C["smoke"]}">PACKAGING PRESENTATION CONCEPT · DEVELOPMENT TARGETS · NEVER BREWED · NO LOGO (D-66)</text>')
    return svg(w, h, body, C["char"], "Concept art: BADSHAH mango hazy IPA and PAAPI hefeweizen can presentations. Illustrations, not photographs.")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    arts = {"hoodie-01-courtyard-back": courtyard(), "hoodie-02-two-worlds-back": two_worlds(), "can-concepts-badshah-paapi": cans()}
    chrome = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    prov = []
    for name, s in arts.items():
        f = OUT / f"{name}.svg"
        f.write_text(s)
        png = OUT / f"{name}.png"
        w, h = map(int, __import__("re").search(r'viewBox="0 0 (\d+) (\d+)"', s).groups())
        html = OUT / f".{name}.html"
        html.write_text(f"<!doctype html><meta charset=utf-8><style>html,body{{margin:0;background:#141110}}svg{{display:block}}</style>{s}")
        r = subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", f"--screenshot={png}", f"--window-size={w},{h + 240}", "--hide-scrollbars", f"file://{html}"], capture_output=True, text=True, timeout=120)
        html.unlink()
        if png.exists():
            from PIL import Image
            Image.open(png).crop((0, 0, w, h)).save(png)
        prov.append({"asset": f"visuals/concepts/{name}", "svg_sha256": sha(f), "png_sha256": sha(png) if png.exists() else None, "png_ok": png.exists(),
                     "method": "procedural vector drawing by code (visuals/tools/concept_art.py), rendered with headless Chromium; no generative image model, no Runway",
                     "authorship": "Claude Code in a session with the founder; AI-assisted, declare as such", "sources": "shapes drawn from scratch; reference research in brand/goods/GOODS-CREATIVE-BRIEFS.md; no third-party artwork, no tracing",
                     "rights": "no third-party material; ownership/assignment not yet documented (needs counsel)", "status": "LOCAL-ONLY concept visualization; not photographs of real products; not published; no logo (D-66)"})
    (OUT / "PROVENANCE.json").write_text(json.dumps(prov, indent=1))
    print(json.dumps([{k: v for k, v in a.items() if k in ("asset", "png_ok")} for a in prov]))


if __name__ == "__main__":
    sys.exit(main())
