"""Entity binding in the model-output boundary (Phase 2 hardening). The first real-model run (qwen2.5:7b-instruct, run 40109758918) produced two claims the boundary accepted although the price was attached to the wrong entity:
  C05: the question named a supplier that is in no record; the claim stated another supplier's saffron price without naming whom it belonged to.
  C09: the question named a supplier from another tenant; the claim wrapped that name around an in-tenant lamb price.
These tests detect that defect class WITHOUT any model: (1) exhaustive identity-substitution mutants over a small hand-built directory, (2) the two recorded real outputs replayed verbatim (a replay is a fixture, not a model call),
(3) cross-tenant names, (4) the governed workflow with a scripted agent returning such a claim. Expected verdicts were written down before the rule existed (see docs/growth-os/PHASE2-HARDENING-EXPECTATIONS.md)."""
import itertools

import pytest

from nasha_lab.growth import model_boundary as MB

DIR = [
    dict(id="a", name="Alpha Dairy Co", verification_status="lead_unverified", freshness="unverified", products=[dict(price_class="SYNTHETIC_QUOTE", unit_price_cents=450.0, min_order_cents=None)]),
    dict(id="b", name="Bravo Broadline Distributor (broadline)", verification_status="synthetic_fixture", freshness="synthetic", products=[dict(price_class="SYNTHETIC_QUOTE", unit_price_cents=520.0, min_order_cents=None)]),
    dict(id="c", name="Charlie Supplier 07 (specialty)", verification_status="synthetic_fixture", freshness="synthetic", products=[dict(price_class="SYNTHETIC_QUOTE", unit_price_cents=610.0, min_order_cents=None)])]
EV = {"e1": dict(doc_id="supplier-a", title="Alpha Dairy Co", text="[Alpha Dairy Co] Paneer: $4.50 per kg, synthetic quote."),
      "e2": dict(doc_id="supplier-b", title="Bravo Broadline Distributor (broadline)", text="[Bravo Broadline Distributor (broadline)] Paneer: $5.20 per kg, synthetic quote."),
      "e3": dict(doc_id="supplier-c", title="Charlie Supplier 07 (specialty)", text="[Charlie Supplier 07 (specialty)] Paneer: $6.10 per kg, synthetic quote.")}
NAMES = {"a": ["Alpha Dairy Co"], "b": ["Bravo Broadline Distributor (broadline)", "Bravo Broadline Distributor"], "c": ["Charlie Supplier 07 (specialty)", "Charlie Supplier 07"]}
PRICE = {"a": "$4.50", "b": "$5.20", "c": "$6.10"}
EID = {"a": "e1", "b": "e2", "c": "e3"}


def verdict(text, ids):
    v = MB.review(dict(title="t", answer="a", claims=[dict(text=text, evidence_ids=ids)], limitations=["l"]), EV, DIR, [])
    return v["status"], {c for r in v["claims_rejected"] for c in r["codes"]}


def good(sid, name):
    return f"{name} quotes Paneer at {PRICE[sid]} per kg."


@pytest.mark.parametrize("sid", "abc")
def test_negative_control_the_unmutated_claim_is_accepted_under_every_name_form(sid):
    for name in NAMES[sid]:
        assert verdict(good(sid, name), [EID[sid]]) == ("accepted", set()), name


def test_every_identity_substitution_that_keeps_a_valid_price_is_rejected():
    """Mutant: replace the supplier's name by another supplier's (either name form) while the price and the citation stay valid. 0 may be accepted."""
    n = 0
    for owner, thief in itertools.permutations("abc", 2):
        for name in NAMES[thief]:
            for ids in ([EID[owner]], [EID[owner], EID[thief]]):                       # price's own record only, or both records cited
                st, codes = verdict(good(owner, name), ids)
                assert st == "rejected" and codes, (owner, name, ids, codes); n += 1
    assert n == 6 * 2 * 2 // 2 * 2 or n > 10                                            # the matrix is not accidentally empty


def test_a_citation_swap_that_keeps_the_name_and_the_price_is_rejected():
    for owner, other in itertools.permutations("abc", 2):
        st, codes = verdict(good(owner, NAMES[owner][0]), [EID[other]])                 # right name, right price, someone else's record
        assert st == "rejected" and codes, (owner, other, codes)


def test_dropping_the_supplier_name_from_a_priced_claim_is_rejected_as_unattributed():
    for sid in "abc":
        assert verdict(f"Paneer costs {PRICE[sid]} per kg.", [EID[sid]]) == ("rejected", {"UNATTRIBUTED_PRICE"})


def test_swapped_prices_between_two_named_suppliers_are_rejected():
    st, codes = verdict(f"Alpha Dairy Co quotes Paneer at {PRICE['b']} per kg and Bravo Broadline Distributor quotes it at {PRICE['a']} per kg.", ["e1", "e2"])
    assert st == "rejected" and codes == {"PRICE_NOT_FROM_NAMED_SUPPLIER"}
    assert verdict(f"Alpha Dairy Co quotes Paneer at {PRICE['a']} per kg and Bravo Broadline Distributor quotes it at {PRICE['b']} per kg.", ["e1", "e2"])[0] == "accepted"


def test_c05_pattern_a_price_with_no_supplier_named_when_the_asked_entity_does_not_exist():
    # recorded real-model claim (run 40109758918, C05), cited evidence = another supplier's record
    ev = {"e1": dict(doc_id="supplier-b", title="Bravo", text="[Bravo Broadline Distributor (broadline)] Saffron threads (i-saffron): $3,485.02 per kg, synthetic quote.")}
    d = [dict(DIR[1], products=[dict(price_class="SYNTHETIC_QUOTE", unit_price_cents=348502.0, min_order_cents=None)])]
    v = MB.review(dict(title="t", answer="not provided; closest is $3,485.02 from Bravo", claims=[dict(text="The price for Spanish saffron threads is $3,485.02 per kg.", evidence_ids=["e1"])], limitations=["l"]), ev, d, [])
    assert v["status"] == "rejected" and v["claims_rejected"][0]["codes"] == ["UNATTRIBUTED_PRICE"]
    ok = MB.review(dict(title="t", answer="a", claims=[dict(text="Bravo Broadline Distributor quotes saffron threads at $3,485.02 per kg.", evidence_ids=["e1"])], limitations=["l"]), ev, d, [])
    assert ok["status"] == "accepted"


def test_c09_pattern_a_name_from_another_tenant_wrapped_around_an_in_tenant_price():
    # recorded real-model claim (run 40109758918, C09); the NASHA tenant's directory does not contain 'Synthetic Facility Supply' (a Meridian Fitness supplier)
    ev = {"e1": dict(doc_id="supplier-s2", title="Synthetic Supplier 02 (specialty meats)", text="[Synthetic Supplier 02 (specialty meats)] Lamb leg, boneless, trimmed (i-lamb-leg): $14.75 per kg, synthetic quote, minimum order $0.00.")}
    d = [dict(id="s2", name="Synthetic Supplier 02 (specialty meats)", verification_status="synthetic_fixture", freshness="synthetic", products=[dict(price_class="SYNTHETIC_QUOTE", unit_price_cents=1475.0, min_order_cents=0.0)])]
    claim = "Synthetic Facility Supply quotes $14.75 per kg for lamb leg, boneless, trimmed (i-lamb-leg)."
    v = MB.review(dict(title="t", answer="a", claims=[dict(text=claim, evidence_ids=["e1"])], limitations=["l"]), ev, d, [])
    assert v["status"] == "rejected" and set(v["claims_rejected"][0]["codes"]) == {"UNATTRIBUTED_PRICE", "UNKNOWN_ENTITY"}
    true_name = MB.review(dict(title="t", answer="a", claims=[dict(text="Synthetic Supplier 02 quotes $14.75 per kg for lamb leg.", evidence_ids=["e1"])], limitations=["l"]), ev, d, [])
    assert true_name["status"] == "accepted"


def test_an_unknown_entity_without_any_price_is_still_rejected_as_a_subject():
    for subj in ("Saffron and Sons of Madrid", "Synthetic Facility Supply", "Northwind Traders"):
        assert verdict(f"{subj} quotes Paneer.", ["e1"])[1] >= {"UNKNOWN_ENTITY"}, subj


def test_claims_without_prices_are_unaffected():
    assert verdict("Alpha Dairy Co is a lead whose record states a synthetic quote.", ["e1"])[0] == "accepted"
    # (absence claims have their own rules and tests in test_growth_comparative_claims.py; "no price is published" cited to a passage that states a price is, rightly, no longer accepted)


def test_recorded_real_outputs_that_were_correct_are_still_accepted():
    """No regression on the real claims that passed in run 40109758918 (C02, C07, C10): replayed verbatim. Since the comparative rule, a 'lowest price' claim is also checked against the full stored quote set, so the fixture states that
    Synthetic Fitness Equipment Wholesale really is the cheapest of two quotes for each item (the real fitness directory is not available here; the quotes are a labelled fixture)."""
    def fp(name, ref, cents):
        return dict(name=name, ingredient_ref=ref, unit="each" if "dumbbell" in ref else "m2", unit_price_cents=cents, min_order_cents=0.0, price_class="SYNTHETIC_QUOTE", valid_from=None, valid_to=None)
    d = [dict(id="bp", name="Brothers Produce", verification_status="lead_unverified", freshness="unverified", products=[dict(name="Wholesale catalogue", ingredient_ref=None, unit="kg", unit_price_cents=None, min_order_cents=None, price_class="NONE_PUBLISHED")]),
         dict(id="fe", name="Synthetic Fitness Equipment Wholesale", verification_status="synthetic_fixture", freshness="synthetic", products=[fp("Dumbbell rack set", "equip.dumbbell-set", 61500.0), fp("Rubber flooring", "equip.rubber-floor", 4650.0)]),
         dict(id="fo", name="Other Fitness Supplier", verification_status="synthetic_fixture", freshness="synthetic", products=[fp("Dumbbell rack set", "equip.dumbbell-set", 70000.0), fp("Rubber flooring", "equip.rubber-floor", 5200.0)])]
    ev = {"e1": dict(doc_id="supplier-bp", title="Brothers Produce", text="# Brothers Produce Verification status: lead unverified. no published price."),
          "e2": dict(doc_id="supplier-fe", title="Synthetic Fitness Equipment Wholesale", text="Dumbbell rack set: $615.00 per each, minimum order $0.00."),
          "e5": dict(doc_id="supplier-fe", title="Synthetic Fitness Equipment Wholesale", text="Rubber flooring: $46.50 per m2, minimum order $0.00.")}
    rep = dict(title="t", answer="a", limitations=["l"], claims=[dict(text="The verification status of Brothers Produce is marked as a lead unverified.", evidence_ids=["e1"]), dict(text="Brothers Produce does not publish any public price list.", evidence_ids=["e1"]),
               dict(text="The lowest price for the dumbbell rack set is $615.00 per each from Synthetic Fitness Equipment Wholesale.", evidence_ids=["e2"]),
               dict(text="The lowest price for the rubber flooring is $46.50 per m2 from Synthetic Fitness Equipment Wholesale.", evidence_ids=["e5"])])
    assert MB.review(rep, ev, d, [])["status"] == "accepted"


# ---------------------------------------------------------------- through the governed workflow (scripted agent that returns the C09-type claim; not a model)
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
from test_growth_launch import FakeAgent, dsn, make, project, tok, world  # noqa: E402,F401


def test_the_workflow_falls_back_and_records_the_binding_codes_when_an_agent_misattributes_a_price(world):  # noqa: F811
    from nasha_lab.growth import agent_research as AR, service as SV
    from test_growth_launch import AS_OF, SCHEMA
    s = SV.GrowthService(world["dsn"], SCHEMA, "tenant-nasha", "ana")
    d = s.supplier_directory(AS_OF, project(world)); s.close()
    sup = next(x for x in d if any(p["unit_price_cents"] is not None for p in x["products"]))
    docs = AR.supplier_documents(d); did = f"supplier-{sup['id']}"
    prod = next(p for p in sup["products"] if p["unit_price_cents"] is not None)
    price = AR.money(float(prod["unit_price_cents"]))
    bad = dict(mode=AR.MODE_OFFLINE, provider="offline", run_id="fake", report=dict(title="t", answer="a", claims=[dict(text=f"Synthetic Facility Supply quotes {price} per {prod['unit']} for {prod['name']}.", evidence_ids=["e1"])], limitations=["l"]),
               verification=dict(ok=True, groundedness=1.0, citation_validity=1.0), evidence={"e1": dict(doc_id=did, title=sup["name"], text=docs[did][1])}, tool_calls=[dict(tool="search_corpus", status="ok")])
    base = make(world); rb = base.run(tok(base, "ana"), project(world), 4); h0 = base.status(rb["corr_id"])["proposal_hash"]; base.close()
    wf = make(world, agent=FakeAgent(bad))
    r = wf.run(tok(wf, "ana"), project(world), 4)
    run = wf.status(r["corr_id"])
    assert r["status"] == "AWAITING_APPROVAL" and run["agent_mode"] == "deterministic_fallback" and run["proposal_hash"] == h0, "a misattributed claim is rejected and never changes the recommendation"
    assert {"UNATTRIBUTED_PRICE", "UNKNOWN_ENTITY"} <= set(run["research"]["rejected_agent_output"]["codes"])
    wf.close()
