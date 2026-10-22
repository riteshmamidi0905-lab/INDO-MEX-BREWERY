"""Plate placement helpers on synthetic images: contact-sheet splitting, flat dark signboard detection, can detection, register integrity."""
import importlib.util
import json
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
s = importlib.util.spec_from_file_location("pd_", ROOT / "visuals/tools/plate_detect.py"); D = importlib.util.module_from_spec(s); s.loader.exec_module(D)
rng = np.random.default_rng(5)


def textured(h, w):
    base = rng.integers(60, 200, (h, w, 3)).astype("uint8")
    return base


def test_split_contact_sheet_finds_panels_in_reading_order():
    sheet = np.full((520, 800, 3), 255, "uint8")
    boxes = [(0, 0, 395, 255), (405, 0, 799, 255), (0, 265, 260, 519), (270, 265, 530, 519), (540, 265, 799, 519)]
    for x0, y0, x1, y1 in boxes:
        sheet[y0:y1 + 1, x0:x1 + 1] = textured(y1 - y0 + 1, x1 - x0 + 1)
    got = D.split_contact_sheet(Image.fromarray(sheet))
    assert len(got) == 5 and got[0][0] < got[1][0] and got[2][1] > got[0][1]


def test_flat_dark_board_is_found_and_textured_dark_regions_are_not():
    img = textured(400, 600)
    img[60:160, 200:460] = 25                                   # flat dark board
    img[200:380, 20:180] = rng.integers(0, 60, (180, 160, 3))    # dark but textured (foliage-like)
    d = D.detect_signboard(Image.fromarray(img))
    assert d and abs(d["quad"][0][0] - 200) < 20 and abs(d["quad"][2][1] - 160) < 20 and d["rectangularity"] > .9
    assert D.detect_signboard(Image.fromarray(textured(400, 600))) is None


def test_register_files_exist_and_hashes_match():
    import hashlib
    reg = json.loads((ROOT / "visuals/source-plates/PLATE-REGISTER.json").read_text())
    assert reg
    for r in reg:
        p = ROOT / r["file"]
        assert p.exists(), r["file"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"], r["file"]
        assert r["review"]["status"] in ("pending", "accepted", "rejected", "reference")
        assert "not a photograph" in r["classification"].lower()
    assert not any(r["review"]["status"] == "accepted" for r in reg)          # nothing is accepted on the founder's behalf
