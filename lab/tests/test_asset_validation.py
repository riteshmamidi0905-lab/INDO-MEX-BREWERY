import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("validate_assets", ROOT / "visuals/tools/validate_assets.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_committed_assets_validate():
    assert _load().validate() == []


def test_tampered_asset_and_missing_provenance_are_caught(tmp_path):
    m = _load()
    d = tmp_path / "visuals" / "concepts"
    d.mkdir(parents=True)
    for f in (ROOT / "visuals/concepts").glob("*"):
        shutil.copy(f, d / f.name)
    m.DIR = d
    (d / "hoodie-01-courtyard-back.png").write_bytes(b"x" * 10 + (d / "hoodie-01-courtyard-back.png").read_bytes())
    prov = json.loads((d / "PROVENANCE.json").read_text())
    prov[1]["status"] = "ready to publish"
    del prov[2]
    (d / "PROVENANCE.json").write_text(json.dumps(prov))
    probs = m.validate()
    assert any("hash differs" in p for p in probs) and any("LOCAL-ONLY" in p for p in probs) and any("no provenance record" in p for p in probs)
