"""Plate intake + compositing pipeline on SYNTHETIC plates (no real plate exists yet). Concept imagery only."""
import importlib.util
import json
import pathlib

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load():
    s = importlib.util.spec_from_file_location("pp", ROOT / "visuals/tools/plate_pipeline.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


@pytest.fixture()
def pp(tmp_path, monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "PLATES_DIR", tmp_path / "plates"); monkeypatch.setattr(m, "REGISTER", tmp_path / "plates/PLATE-REGISTER.json")
    monkeypatch.setattr(m, "CONFIGS", tmp_path / "cfg"); monkeypatch.setattr(m, "OUT", tmp_path / "out"); monkeypatch.setattr(m, "COMP_REGISTER", tmp_path / "out/COMPOSITE-REGISTER.json")
    (tmp_path / "cfg").mkdir()
    return m


def can_plate(path):
    sys_path = str(ROOT / "visuals/tools")
    import sys; sys.path.insert(0, sys_path)
    import composite_label as C
    img, region = C.blank_can_plate()
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    img.save(path)
    return [v * 2 for v in region]


def test_perspective_warp_lands_corners_on_the_quad(pp):
    art = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
    quad = [(30, 40), (170, 30), (180, 120), (20, 110)]
    out = np.asarray(pp.warp_art(art, quad, (200, 150)))
    inside = out[..., 3] > 128
    ys, xs = np.nonzero(inside)
    assert abs(xs.min() - 20) <= 2 and abs(xs.max() - 180) <= 2 and abs(ys.min() - 30) <= 2 and abs(ys.max() - 120) <= 2
    assert out[75, 100, 3] == 255 and out[5, 5, 3] == 0


def test_clean_plate_passes_intake_and_text_plate_is_flagged(pp, tmp_path):
    pytest.importorskip("rapidocr_onnxruntime", reason="INTEGRATION UNAVAILABLE: no OCR engine")
    clean = tmp_path / "clean.png"; can_plate(clean)
    pp.cmd_intake(type("A", (), dict(image=str(clean), plate_id="badshah_can", prompt_file=None, generated_on="2026-10-22")))
    rec = json.loads(pp.REGISTER.read_text())[-1]
    assert rec["auto_verdict"] == "pass" and rec["checks"]["text_clean"] and "not a photograph" in rec["classification"].lower()
    dirty = tmp_path / "dirty.png"
    im = Image.open(clean).convert("RGB"); f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 120)
    ImageDraw.Draw(im).text((300, 700), "BADSHAH 5.2% ABV", font=f, fill=(250, 250, 250)); im.save(dirty)
    pp.cmd_intake(type("A", (), dict(image=str(dirty), plate_id="amba_can", prompt_file=None, generated_on="x")))
    bad = [r for r in json.loads(pp.REGISTER.read_text()) if r["plate_id"] == "amba_can"][-1]
    assert bad["auto_verdict"] == "needs attention" and bad["checks"]["text_found"]


def test_composite_requires_human_acceptance_and_a_filled_config(pp, tmp_path):
    plate = tmp_path / "can.png"; region = can_plate(plate)
    pp.cmd_intake(type("A", (), dict(image=str(plate), plate_id="badshah_can", prompt_file=None, generated_on="2026-10-22")))
    with pytest.raises(SystemExit):                         # pending review -> refused
        pp.cmd_composite(type("A", (), dict(plate_id="badshah_can", variant="primary")))
    rec = json.loads(pp.REGISTER.read_text())[-1]
    if rec["auto_verdict"] != "pass":
        pytest.skip("OCR unavailable here; text check not performed")
    pp.cmd_review(type("A", (), dict(plate_id="badshah_can", decision="accepted", by="Ritesh", note="test", override=False)))
    cfg = json.loads((ROOT / "visuals/compositing-configs/badshah_can.json").read_text())
    (pp.CONFIGS / "badshah_can.json").write_text(json.dumps(cfg))
    with pytest.raises(SystemExit):                         # still a TEMPLATE -> refused
        pp.cmd_composite(type("A", (), dict(plate_id="badshah_can", variant="primary")))
    cfg.update(status="READY (test)", region=region)
    (pp.CONFIGS / "badshah_can.json").write_text(json.dumps(cfg))
    for variant in ("primary", "g1"):
        pp.cmd_composite(type("A", (), dict(plate_id="badshah_can", variant=variant)))
    reg = json.loads(pp.COMP_REGISTER.read_text())
    assert len(reg) == 2 and {r["variant"] for r in reg} == {"primary", "g1"}
    assert all("not a photograph" in r["classification"].lower() and r["artwork"] for r in reg)
    assert pp.cmd_qa(type("A", (), dict(plate_id=None))) == 0


def test_g1_is_refused_outside_cans_glass_signage(pp):
    cfg = {"mode": "print", "plate_kind": "apparel", "status": "READY", "items": [{"art": "hoodie-symbol-gold.png", "art_g1": "glass-etch-g1-white.png", "quad": [[0, 0], [9, 0], [9, 9], [0, 9]]}]}
    assert any("G1" in e for e in pp.validate_config(cfg, "g1"))
    assert pp.validate_config(cfg, "primary") == []


def test_all_seven_config_templates_exist_and_reference_real_artwork(pp):
    for pid in pp.SUBJECTS:
        cfg = json.loads((ROOT / f"visuals/compositing-configs/{pid}.json").read_text())
        errs = [e for e in pp.validate_config(cfg, "primary") + pp.validate_config(cfg, "g1") if "TEMPLATE" not in e]
        assert errs == [], (pid, errs)
