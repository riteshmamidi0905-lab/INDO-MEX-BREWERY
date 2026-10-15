import ast, json, os, pathlib
import pytest
from nasha_lab import dq, evaluate, generator, pipeline

ROOT = pathlib.Path(__file__).resolve().parents[1]
DETECTABLE = [t for t in generator.DEFECT_TYPES if t != "near_duplicate_shifted"]


def run(seed=1, k=8, types=None, enabled=None):
    raw, truth = generator.generate(seed, k, types)
    con, rep = pipeline.run(raw, enabled_rules=enabled)
    return raw, truth, con, rep


def found(rep):
    return {(f.rule, f.table, f.key) for f in rep["findings"]}


def test_generator_is_deterministic_and_seed_sensitive():
    a, ta = generator.generate(7); b, tb = generator.generate(7); c, _ = generator.generate(8)
    assert a == b and ta == tb and a != c


def test_clean_dataset_has_no_findings_and_gate_passes():
    _, _, con, rep = run(k=0)
    assert rep["findings"] == [] and rep["gate"] == "PASSED"


def test_clean_menu_has_no_beef_or_pork_D54():
    raw, _ = generator.generate(1, 0)
    text = " ".join(m["ingredients"] for m in raw["menu_items"]).lower()
    assert not any(t in text for t in dq.FORBIDDEN_TOKENS)


@pytest.mark.parametrize("t", DETECTABLE)
def test_each_injected_defect_type_is_found_exactly(t):
    _, truth, _, rep = run(types=[t])
    f = {x for x in found(rep) if x[0] == t}
    assert f == truth and truth, (t, len(truth), len(f))


def test_known_limitation_one_second_shifted_duplicate_is_not_detected():
    """DOCUMENTED GAP: exact-signature near-duplicate detection misses a copy shifted by 1 s. If this starts failing, update docs/EVALUATION.md."""
    _, truth, _, rep = run(types=["near_duplicate_shifted"])
    assert truth and not (found(rep) & truth)


def test_lineage_conservation_every_raw_row_is_modeled_or_quarantined():
    _, _, con, rep = run()
    for t, (raw_n, mod_n, q_n) in rep["lineage"].items():
        assert raw_n == mod_n + q_n, (t, raw_n, mod_n, q_n)
    assert con.execute("select count(*) from quarantine").fetchone()[0] == sum(q for _, _, q in rep["lineage"].values())


def test_regression_dedup_keeps_the_original_order():
    """Bug found by the conservation report: the first version quarantined BOTH copies of a duplicated order."""
    raw0, _ = generator.generate(3, 0)
    con0, _ = pipeline.run(raw0)
    _, _, con1, _ = run(seed=3, types=["duplicate_order"])
    q = "select count(*), sum(total_cents) from fact_order"
    assert con1.execute(q).fetchone() == con0.execute(q).fetchone()


def test_modeled_layer_is_clean():
    _, _, con, _ = run()
    assert con.execute("select count(*) from fact_order_line l left join fact_order o using(order_id) where o.order_id is null").fetchone()[0] == 0
    assert con.execute("select count(*) from fact_order_line where qty<=0").fetchone()[0] == 0
    assert con.execute("select count(*) from fact_order where ts>'2026-05-01T00:00:00'").fetchone()[0] == 0
    assert con.execute("select count(*) from fact_order o join (select order_id, sum(qty*unit_price_cents) s from fact_order_line group by 1) l using(order_id) where l.s<>o.total_cents").fetchone()[0] == 0
    assert con.execute("select count(*) from fact_inventory_count where unit='lb'").fetchone()[0] == 0


def test_analytics_view_reconciles_with_fact_table():
    _, _, con, _ = run()
    assert con.execute("select sum(revenue_cents) from v_daily_sales").fetchone()[0] == con.execute("select sum(total_cents) from fact_order").fetchone()[0]


def test_forbidden_protein_fails_publish_gate_and_flags_item_but_keeps_it_visible():
    _, truth, con, rep = run(types=["forbidden_protein"])
    assert rep["gate"].startswith("FAILED") and "forbidden_protein" in rep["gate"]
    assert con.execute("select count(*) from dim_menu_item where compliance_blocked=1").fetchone()[0] == len(truth)


def test_price_tolerance_boundary():
    raw, _ = generator.generate(2, 0)
    base = int(raw["menu_items"][0]["price_cents"])
    for p, expect in [(round(base * 1.20), False), (round(base * 1.30), True), (round(base * 0.9), False), (round(base * 0.6), True)]:
        raw["order_lines"][0].update(item_id=raw["menu_items"][0]["item_id"], unit_price_cents=str(p))
        st, _ = pipeline.stage(raw)
        hit = any(f.rule == "price_drift" and f.key.startswith(raw["order_lines"][0]["order_id"] + ":1") for f in dq.run_rules(st))
        assert hit == expect, (p, expect)


def test_price_drift_is_a_warning_not_a_quarantine():
    _, truth, con, rep = run(types=["price_drift"])
    assert con.execute("select count(*) from fact_order_line where price_flag=1").fetchone()[0] == len(truth)
    assert con.execute("select count(*) from quarantine").fetchone()[0] == 0


def test_rules_never_read_ground_truth():
    src = (ROOT / "nasha_lab" / "dq.py").read_text()
    imports = [n for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not any("truth" in ast.dump(n) for n in imports)
    names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Attribute)}
    assert "generate" not in names and not any("truth" in x.lower() for x in names)


def test_disabling_a_rule_creates_a_measurable_miss():
    _, truth, _, rep = run(types=["near_duplicate_order"], enabled=[r for r in dq.ALL_RULES if r != "near_duplicate_order"])
    assert not (found(rep) & truth)


def test_malformed_timestamps_are_rejected_in_staging_not_crashed():
    raw, truth, con, rep = run(types=["malformed_timestamp"])
    assert {k for r, t, k in found(rep) if r == "malformed_timestamp"} == {k for _, _, k in truth}


def test_committed_eval_results_show_the_fail_then_fix_story():
    v0 = json.loads((ROOT / "results" / "eval_v0_baseline.json").read_text())
    v1 = json.loads((ROOT / "results" / "eval_v1.json").read_text())
    assert v0["injected"]["per_rule"]["near_duplicate_order"]["recall"] == 0.0
    assert v1["injected"]["per_rule"]["near_duplicate_order"]["recall"] == 1.0
    assert v1["clean_dataset_findings"] == 0
    assert v1["injected"]["per_rule"]["near_duplicate_shifted"]["recall"] == 0.0   # honest remaining gap


def test_evaluate_matches_committed_results_exactly():
    fresh = evaluate.score(range(1, 6))
    assert json.loads(json.dumps(fresh["per_rule"])) == json.loads((ROOT / "results" / "eval_v1.json").read_text())["injected"]["per_rule"]


def test_write_raw_roundtrip(tmp_path):
    raw, _ = generator.generate(1, 2)
    pipeline.write_raw(raw, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {f"{t}.csv" for t in raw}


def test_forbidden_terms_are_a_superset_of_the_repo_diet_audit():
    """Integration with existing NASHA tooling: one D-54 policy, no silent drift between the audit and the data platform."""
    import re
    audit = (ROOT.parent / "tools" / "diet_audit.py").read_text()
    terms = re.search(r'TERMS=r"\\b\((.*?)\)\\b"', audit).group(1).split("|")
    assert terms and set(terms) <= set(dq.FORBIDDEN_TOKENS), set(terms) - set(dq.FORBIDDEN_TOKENS)


def test_word_boundary_does_not_flag_innocent_ingredients():
    assert not dq.FORBIDDEN_RE.search("chamoy") and not dq.FORBIDDEN_RE.search("shamrock") and dq.FORBIDDEN_RE.search("Pork lard")
