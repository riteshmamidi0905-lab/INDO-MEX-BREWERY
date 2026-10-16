"""Knowledge authority rules v2 (Milestone 2). SYNTHETIC / OFFLINE. conftest pins the frozen Block 3 corpus."""
import os
import pytest
from nasha_lab import knowledge as K, knowledge_authority as KA
from nasha_lab.ops import alerts as A, faults as F, runner as R
from nasha_lab.ops.util import RESULTS_DIR, load_json

Q = "What is the dietary policy on beef, pork and hidden derivatives such as stock, bouillon, shortening and natural flavors?"
D = F.STALE_DOCS
doc = lambda v: dict(source_path=D[v]["source_path"], text=D[v]["text"], **{"class": D[v]["cls"]})


ids = lambda r: [(c['document_id'], c['effective_status']) for c in r['citations']]          # scores shift when a document changes corpus statistics; identity and status must not


def kb_with(*docs, rules="v2"): return KA.AuthorityKB(R.shared_kb(list(docs)), rules)


def test_v1_is_a_pass_through():
    kb = R.shared_kb([doc("superseded_policy_doc")]); assert KA.AuthorityKB(kb, "v1").ask(Q) == kb.ask(Q)
    with pytest.raises(ValueError): KA.AuthorityKB(kb, "v3")


def test_polarity_rules():
    assert KA.polarity("Bouillon with natural flavors is always permitted.") == "PERMIT"
    assert KA.polarity("Beef stock is not allowed in any sauce.") == "PROHIBIT"
    assert KA.polarity("The concept is beef-free and pork-free.") == "PROHIBIT"
    assert KA.polarity("Plain statement allowed: we do not serve beef or pork.") == "MIXED"        # v2.0 read this as PERMIT: a measured false conflict
    assert KA.polarity("The kitchen is open on Tuesdays.") is None


def test_quantity_rules_ignore_enumerators_and_ids():
    assert KA.numerals("Sprint 22: (1) Lane A, D-81 on 2026-10-10") == set()
    assert KA.numerals("Cap spend at $500 and 20% of revenue, 30 days") == {"$500", "20%", "30days"}


def test_r1_conflict_unit_and_r2_is_advisory():
    qt = set(K.tokenize(Q)); a = dict(text="Bouillon with natural flavors is always permitted."); b = dict(text="Bouillon and natural flavors are not allowed.")
    assert KA.pair_conflicts(qt, a, b)[0]["rule"] == "R1_POLARITY"
    assert KA.pair_conflicts(qt, a, dict(text="Bouillon with natural flavors is common in soups.")) == []
    c = dict(text="Dietary policy review budget for beef pork stock is $500."); d = dict(text="Dietary policy review budget for beef pork stock is $900.")
    assert KA.pair_conflicts(qt, c, d)[0]["rule"] == "R2_NUMERIC"


def test_excluded_sources_are_surfaced_with_status_gap03_regression():
    base = R.shared_kb([doc("superseded_policy_doc")]).ask(Q)
    assert "docs/company/OLD-MENU-POLICY.md" not in str(base["non_authoritative_matches"])             # v1: the GAP-03 miss
    r = kb_with(doc("superseded_policy_doc")).ask(Q); ex = [m for m in r["non_authoritative_matches"] if m.get("document_id") == "docs/company/OLD-MENU-POLICY.md"]
    assert ex and ex[0]["effective_status"] == "SUPERSEDED" and ex[0]["tier"] == "EXCLUDED" and ex[0]["authority_rank"] == 9 and ex[0]["kind"] == "excluded_source"
    assert "docs/company/OLD-MENU-POLICY.md" not in [c["document_id"] for c in r["citations"]]
    assert [c["document_id"] for c in r["citations"]] == [c["document_id"] for c in base["citations"]]          # the answer is unchanged


def test_superseded_and_unverified_contradictions_are_resolved_by_status_not_abstained():
    for v, ct in (("superseded_policy_doc", "SUPERSEDED_CONTRADICTS_CURRENT"), ("unverified_note", "EXCLUDED_CONTRADICTS_CURRENT")):
        r = kb_with(doc(v)).ask(Q); cf = [m for m in r["non_authoritative_matches"] if m.get("kind") == "authority_conflict"]
        assert not r["abstained"] and cf and all(c["resolved"] and not c["blocking"] for c in cf) and cf[0]["conflict_type"] == ct and cf[0]["winner"] == "D-54"
        assert any("governs by status" in n for n in r["status_notes"])


def test_conflicting_current_document_abstains_and_escalates_citing_neither():
    r = kb_with(doc("contradictory_canonical")).ask(Q)
    assert r["abstained"] and r["answer"] == K.ABSTAIN and r["citations"] == [] and r["authority_escalation"] and r["reason"].startswith("AUTHORITY_CONFLICT")
    u = [m for m in r["non_authoritative_matches"] if m.get("kind") == "authority_conflict" and m["blocking"]]
    assert u and {s["document_id"] for s in u[0]["sources"]} == {"D-54", "docs/company/ROGUE-CANONICAL.md"} and {s["tier"] for s in u[0]["sources"]} == {"AUTHORITATIVE"}
    assert "D-54" in r["reason"] and "ROGUE-CANONICAL" in r["reason"]


def test_metamorphic_adding_superseded_or_unverified_docs_never_changes_a_current_answer():
    base = kb_with().ask(Q)
    for v in ("superseded_policy_doc", "unverified_note"):
        r = kb_with(doc(v)).ask(Q); assert r["answer"] == base["answer"] and ids(r) == ids(base) and r["abstained"] == base["abstained"]
    both = kb_with(doc("superseded_policy_doc"), doc("unverified_note")).ask(Q); assert both["answer"] == base["answer"] and ids(both) == ids(base)


def test_metamorphic_adding_a_conflicting_current_doc_forces_abstain_for_every_phrasing():
    for text in ("Bouillon with natural flavors is always permitted.", "Beef stock and pork bouillon are allowed in sauces and soups.", "Shortening made from pork lard is approved for tortillas."):
        d = dict(source_path="docs/company/EXTRA-CANONICAL.md", text="# Dietary policy\nThe dietary policy on beef, pork and hidden derivatives such as stock, bouillon, shortening and natural flavors: " + text, **{"class": "CANONICAL"})
        assert kb_with(d).ask(Q)["abstained"], text
    agree = dict(source_path="docs/company/EXTRA-CANONICAL.md", text="# Dietary policy\nThe dietary policy on beef, pork and hidden derivatives such as stock, bouillon, shortening and natural flavors: all of them are prohibited.", **{"class": "CANONICAL"})
    r = kb_with(agree).ask(Q); assert not r["abstained"] and r["citations"]          # an agreeing current document must not trigger abstention
    unrelated = dict(source_path="docs/company/EXTRA.md", text="# Parking\nThe parking lot is permitted for staff on weekdays after noon.", **{"class": "CANONICAL"})
    assert kb_with(unrelated).ask(Q)["answer"] == kb_with().ask(Q)["answer"]


def test_no_blocking_conflicts_on_the_unmodified_corpus_golden_questions():
    from nasha_lab import eval_rag
    a = KA.AuthorityKB(R.shared_kb([]), "v2")
    bad = [r["id"] for r in eval_rag.load_gold() if any(c["blocking"] for c in a.scan(r["question"])[1])]
    assert bad == [], bad


# ---- stale_document fault trials re-run
@pytest.mark.parametrize("variant,seed", [("contradictory_canonical", 301), ("superseded_policy_doc", 302), ("unverified_note", 303)])
def test_stale_document_trials_under_v2_detect_and_contain(variant, seed):
    row, det, env, rid = F.f_stale(seed, variant=variant, authority_rules="v2")
    assert row["detected"] and row["contained"] and not row["stale_source_cited"]
    ids = {a["rule_id"] for a in A.AlertEvaluator().scan_run_full(env.svc.store.events(rid), env.ops.record(rid))}
    assert ("AR-26" in ids) == (variant == "contradictory_canonical") and ("AR-27" in ids)          # AR-27 also fires for the rogue canonical doc: it contradicts excluded historical menus too


def test_v1_contradictory_canonical_is_not_contained_regression():
    row, det, env, rid = F.f_stale(301, variant="contradictory_canonical")
    assert row["stale_source_cited"] and not row["contained"] and not row["detected"]


def test_clean_run_raises_no_authority_alert_and_same_action():
    sc = next(s for s in R.clean_pool()["heldout"] if s.event_family == "POLICY")
    r1, ev1, _ = R.run_scenario(sc); r2, ev2, env2 = R.run_scenario(sc, authority_rules="v2")
    assert r1["action"] == r2["action"] and r2["retrieval"]["authority_conflicts"] == 0 and r2["retrieval"]["excluded_contradictions"] == 0
    assert not {"AR-26", "AR-27"} & {a["rule_id"] for a in A.AlertEvaluator().scan_run_full(ev2, r2)}


def test_alert_rule_taxonomy_and_runbook_are_consistent():
    rules = {r["id"]: r for r in A.load_rules()["rules"]}; cls = {c["id"]: c for c in A.load_taxonomy()["classes"]}
    assert rules["AR-26"]["class"] == "AUTHORITY_CONFLICT" in cls and cls["AUTHORITY_CONFLICT"]["runbook"] == "RB-AUTHORITY-CONFLICT"
    assert os.path.exists(os.path.join(os.path.dirname(A.RULES_PATH), "runbooks", "RB-AUTHORITY-CONFLICT.md")) and rules["AR-27"]["class"] == "STALE_SOURCE"


def test_committed_trial_results():
    d = load_json(os.path.join(RESULTS_DIR, "authority_trials.json")); s = d["stale_document_20_trials"]
    assert s["v1"]["ALL"] == dict(n=20, detected=7, contained=16, stale_source_cited=4) and s["v2"]["ALL"] == dict(n=20, detected=20, contained=20, stale_source_cited=0)
    assert d["gap03_set_7_per_variant"]["contradictory_canonical"]["v1"]["stale_source_cited"] == 7 and d["gap03_set_7_per_variant"]["contradictory_canonical"]["v2"]["contained"] == 7
    assert d["clean_control"]["runs_where_action_changed"] == 0 and "AR-26" not in d["clean_control"]["v2"]["alerts_by_rule"] and d["golden_false_conflict_check"]["blocking"] == 0
