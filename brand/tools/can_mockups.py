#!/usr/bin/env python3
"""Procedural can mockups: compose the verified vector label wraps onto a PROCEDURAL blank can plate with visuals/tools/composite_label.py.
These are RENDERS (code), not photographs, and they exist to prove the compositing pipeline until a real blank-product photo is supplied."""
import sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "visuals/tools"))
import composite_label as C
V3 = ROOT / "visuals/brand-v3"


def main():
    (V3 / "mockups").mkdir(exist_ok=True)
    plate, region = C.blank_can_plate()
    plate.save(V3 / "mockups/blank-can-plate-procedural.png")
    for n in ("badshah", "amba-haze"):
        wrap = Image.open(V3 / f"labels/{n}-wrap.png")
        C.composite(plate, wrap, region, center_frac=0.5).save(V3 / f"mockups/{n}-can-procedural.png")
    a, b = (Image.open(V3 / f"mockups/{n}-can-procedural.png") for n in ("badshah", "amba-haze"))
    sheet = Image.new("RGB", (a.width * 2, a.height)); sheet.paste(a, (0, 0)); sheet.paste(b, (a.width, 0)); sheet.save(V3 / "mockups/cans-pair-procedural.png")
    print(sheet.size)


if __name__ == "__main__":
    main()
