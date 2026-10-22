"""Beer specifications (D-85): formulas are correct, the structured spec, generated documents, labels and website agree, and no document overclaims."""
import importlib.util
import json
import pathlib
import re

import pytest

from nasha_lab import beer_specs as S, brewing as B

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_formulas_match_hand_calculations():
    assert B.abv_simple(1.050, 1.012) == pytest.approx(4.9875)
    assert B.apparent_attenuation(1.048, 1.012) == pytest.approx(0.75)
    assert B.plato(1.048) == pytest.approx(11.9, abs=0.1)
    assert B.tinseth_ibu(28.35, 5, 18.93, 60, 1.050) == pytest.approx(17.3, abs=0.2)        # 1 oz of 5% alpha in 5 gal, 60 min, OG 1.050
    grist_kg, split = B.grist_for_og(1.048, {"wheat malt": 55, "pilsner malt": 45}, 100, 0.72)
    assert B.og_from_grist(split, 100, 0.72) == pytest.approx(1.048, abs=0.0005) and sum(split.values()) == pytest.approx(grist_kg, abs=0.05)
    assert B.base_og_for_target_abv(6.0, 1.015, 5.76) + 0.00576 == pytest.approx(1.015 + 6.0 / 131.25)


def test_targets_are_founder_values_and_expected_abv_lands_within_tolerance():
    sp = S.specs()
    bd, am = sp["beers"]
    assert (bd["target_abv_pct"], am["target_abv_pct"]) == (4.7, 6.0)
    assert abs(bd["expected_abv_formula_pct"] - 4.7) <= 0.1 and abs(am["expected_abv_formula_pct"] - 6.0) <= 0.1
    assert "not brewed or tested" in bd["status"].lower() and "not brewed or tested" in am["status"].lower()
    assert "not measured" in sp["disclaimer"].lower() and "not laboratory-verified" in sp["disclaimer"].lower()
    assert 1.044 <= bd["og"] <= 1.053 and 1.008 <= bd["fg"] <= 1.014                              # inside the BJCP 10A ranges quoted in the repo
    assert sum(bd["grist_percent"].values()) == 100 and sum(am["grist_percent"].values()) == 100


def test_generated_docs_and_json_are_current():
    spec = importlib.util.spec_from_file_location("bbd", ROOT / "lab/tools/build_beer_docs.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    sp = m.S.specs()
    assert json.loads((ROOT / "beer/specs/beer_specs.json").read_text()) == json.loads(json.dumps(sp))
    assert (ROOT / "beer/specs/BEER-SPECIFICATIONS-V1.md").read_text() == m.spec_doc(sp)
    assert (ROOT / "beer/pilot-briefs/06-badshah-formulation-brief.md").read_text() == m.badshah_doc(sp["beers"][0])
    assert (ROOT / "beer/pilot-briefs/07-amba-haze-formulation-brief.md").read_text() == m.amba_doc(sp["beers"][1])


def test_documents_never_present_the_targets_as_results():
    for f in ("beer/specs/BEER-SPECIFICATIONS-V1.md", "beer/pilot-briefs/06-badshah-formulation-brief.md", "beer/pilot-briefs/07-amba-haze-formulation-brief.md"):
        t = (ROOT / f).read_text()
        assert "NOT BREWED OR TESTED" in t
        if "pilot-briefs" in f:
            assert "[NASHA-UNTESTED]" in t and "[EST]" in t and "Established vs untested" in t
        assert not re.search(r"\b(we brewed|was brewed|tasted (?:as|like)|panel (?:scored|found)|laboratory-verified (?:at|abv))\b", t, re.I)
        t_no_rule = "\n".join(l for l in t.splitlines() if 'bare "' not in l)                  # the rule text quotes the forbidden form on purpose
        for bare in re.findall(r"\b\d\.\d%\s*ABV\b", t_no_rule):
            pytest.fail(f"bare ABV statement in {f}: {bare}")
    assert "gluten-free" in (ROOT / "beer/pilot-briefs/07-amba-haze-formulation-brief.md").read_text().lower()
