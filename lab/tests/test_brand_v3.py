"""Brand v3 assets: provenance hashes match files, placeholders stay placeholders, compositing preserves geometry. Concept art only."""
import hashlib, importlib.util, json, pathlib, re
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(rel, name):
    s = importlib.util.spec_from_file_location(name, ROOT / rel); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def test_provenance_hashes_match_and_every_record_has_status():
    recs = json.loads((ROOT / "visuals/brand-v3/PROVENANCE.json").read_text())
    assert recs
    for r in recs:
        assert hashlib.sha256((ROOT / r["asset"]).read_bytes()).hexdigest() == r["sha256"], r["asset"]
        assert r["approval"] and r["rights"] and r["method"]
    refs = [r for r in recs if "chatgpt" in r["asset"]]
    assert len(refs) == 2                                   # both ChatGPT boards are recorded
    for ref in refs:
        assert "EXPLORATORY" in ref["approval"] and "not a photograph of" in ref["approval"].lower()
        assert "not independently verified" in ref["rights"].lower() and "2026-10-22" in ref["method"]
    assert not any("generative" in r["method"] and "no generative" not in r["method"] and "chatgpt" not in r["asset"] for r in recs)


def test_label_svgs_keep_unverified_specs_as_placeholders():
    for n in ("badshah", "amba-haze"):
        t = (ROOT / f"visuals/brand-v3/labels/{n}-wrap.svg").read_text()
        assert "ABV · VOLUME — TBD" in t and "BARCODE — TBD" in t and "CERTIFICATIONS — NONE CLAIMED" in t
        assert not re.search(r"\d+(\.\d+)?\s?%\s?(ALC|ABV)|\bIBU\b|™|®|halal", t, re.I)


def test_cylinder_composite_keeps_outside_pixels_and_maps_label_colour():
    C = _load("visuals/tools/composite_label.py", "cl")
    plate = Image.new("RGB", (200, 300), (180, 180, 180))
    wrap = Image.new("RGB", (400, 100), (10, 80, 40))
    out = np.asarray(C.composite(plate, wrap, (50, 50, 150, 250)))
    assert (out[:40] == 180).all() and (out[:, :40] == 180).all()                   # untouched outside the region
    c = out[150, 100]; assert c[1] > c[0] and c[1] > c[2]                           # label green came through at centre
