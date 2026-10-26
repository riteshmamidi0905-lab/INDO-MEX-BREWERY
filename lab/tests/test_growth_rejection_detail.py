"""RECORDING of boundary rejections (recording format 2). Model-live run #4 voided both governed-workflow model outputs on one rejected supplier comparison, and the record kept only 120 characters of the claim, so it could not be judged afterwards whether the model
was wrong or the rule was too strict. These tests pin that the record now holds what is needed to decide it - for a correct comparison and for an incorrect one - WITHOUT changing any verdict (the rules are not loosened) and without exposing more than the tenant's own run.
No model is called."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from test_growth_comparative_claims import P, S, codes, ev, review  # noqa: E402
from nasha_lab.growth import launch_workflow as LW, model_boundary as MB  # noqa: E402

NAME = "Firm white fish fillet, skinless (species TBD: mahi/redfish/cod)"
A, B, I = "Synthetic Broadline Distributor A (broadline)", "Synthetic Broadline Distributor B (broadline)", "Synthetic Specialty Importer (specialty)"
DIRECTORY = [S("a", A, P(NAME, "i-white-fish", 1167.41)), S("b", B, P(NAME, "i-white-fish", 1189.12)), S("i", I, P(NAME, "i-white-fish", 1215.67))]
EVIDENCE = ev(*DIRECTORY)
IDS = list(EVIDENCE)
# a LONG correct listing (over 200 characters, the length run #4's record was cut at) that also says which quote is lowest
CORRECT = f"{NAME} (i-white-fish) is quoted by {I} at $12.16 per kg, {A} at $11.67 per kg and {B} at $11.89 per kg; of these three stored quotes, {A} holds the lowest at $11.67 per kg."
INCORRECT = f"{I} quotes the lowest price for {NAME} at $12.16 per kg, which is below {A} at $11.67 per kg and {B} at $11.89 per kg, according to the three stored supplier quotes in the retrieved records."


def rejected_entry(text):
    v = review(text, DIRECTORY, EVIDENCE, IDS)
    assert v["status"] == "rejected"
    return v, v["claims_rejected"][0]


def test_the_complete_rejected_claim_is_kept_whatever_its_length_and_the_old_short_fields_are_unchanged():
    assert len(CORRECT) > 200 and len(INCORRECT) > 200
    for text in (CORRECT, INCORRECT):
        v, r = rejected_entry(text)
        assert r["full_text"] == text and r["text_chars"] == len(text), "the whole claim, with its length so truncation is detectable"
        assert r["text"] == text[:120], "the historical short field is unchanged (backward compatible)"
        c = v["comparisons"][0]
        assert c["claim_full"] == text and c["claim"] == text[:200] and c["claim_chars"] == len(text)


def test_the_record_identifies_the_rule_the_cited_evidence_the_named_suppliers_and_the_stored_quotes_compared():
    for text in (CORRECT, INCORRECT):
        v, r = rejected_entry(text)
        assert r["codes"] and r["evidence_ids"] == IDS and r["mentioned_supplier_ids"] == ["a", "b", "i"] and r["cited_doc_ids"] == ["supplier-a", "supplier-b", "supplier-i"]
        d = r["detail"]["comparative"]
        assert d["verdict"] == "false" and d["reason"] == "a named supplier is not the lowest quote in the comparison set" and d["product"] == "i-white-fish"
        assert [(x["supplier_id"], x["price_cents"]) for x in d["set_detail"]] == [("a", 1167.41), ("b", 1189.12), ("i", 1215.67)], "every stored quote compared, by supplier id and price, cheapest first"
        assert d["extreme"]["suppliers"] == [A]


def test_the_record_lets_a_reader_tell_a_correct_comparison_from_an_incorrect_one_without_loosening_the_rule():
    """Both are still rejected today (the rule is unchanged); what differs is what the record shows. The adjudication below uses ONLY recorded data."""
    import re

    def judge(r):
        d = r["detail"]["comparative"]; truth = {x["supplier"]: round(x["price_cents"] / 100, 2) for x in d["set_detail"]}
        text = r["full_text"]
        stated = {n: float(p) for n, p in re.findall(rf"({'|'.join(map(re.escape, truth))}) at \$([\d.]+)", text)}
        before = text[:text.index("lowest")]
        called_lowest = max(truth, key=lambda n: before.rfind(n))                  # the supplier named closest before the word "lowest"
        return all(truth[n] == p for n, p in stated.items()), called_lowest == d["extreme"]["suppliers"][0]
    _, ok = rejected_entry(CORRECT); _, bad = rejected_entry(INCORRECT)
    assert judge(ok) == (True, True), "every stated price is the stored price and the lowest named is the true lowest: a valid comparison the rule rejects"
    prices_ok, lowest_named = judge(bad)
    assert prices_ok and not lowest_named, "the prices are real but the supplier called lowest is not: the model was wrong"


def test_the_price_to_supplier_binding_that_failed_is_recorded():
    text = f"{NAME} is quoted by {I}, {A} and {B} at $12.16, $11.67 and $11.89 per kg respectively, the lowest being {A}."
    v, r = rejected_entry(text)
    assert "PRICE_NOT_FROM_NAMED_SUPPLIER" in r["codes"]
    b = r["detail"]["price_binding"]
    assert b["bound_supplier_names"] and b["amount"] in (12.16, 11.67, 11.89)


def test_accepting_a_true_claim_records_nothing_extra_and_nothing_is_loosened():
    v = review(f"{A} quotes the lowest {NAME} price at $11.67 per kg.", DIRECTORY, EVIDENCE, IDS)
    assert v["status"] == "accepted" and v["claims_rejected"] == [] and v["comparisons"][0]["verdict"] == "verified" and v["comparisons"][0]["claim_full"].startswith(A)
    assert codes(review(CORRECT, DIRECTORY, EVIDENCE, IDS)) == {"COMPARATIVE_FALSE"}, "a multi-supplier listing that names a non-lowest supplier is still rejected: verification was not loosened"


def test_partial_acceptance_was_not_introduced_one_rejected_claim_still_voids_the_report():
    good = dict(text=f"{A} quotes the lowest {NAME} price at $11.67 per kg.", evidence_ids=IDS)
    v = MB.review(dict(title="t", answer="a", claims=[good, dict(text=CORRECT, evidence_ids=IDS)], limitations=["l"]), EVIDENCE, DIRECTORY, [])
    assert v["status"] == "rejected" and len(v["claims_accepted"]) == 1 and len(v["claims_rejected"]) == 1


def test_the_workflow_recording_is_scoped_capped_fingerprinted_and_leaks_nothing_beyond_the_tenants_own_run():
    secret = "SECRET-NOT-FOR-LOGS-4f9a"
    long_passage = "[Synthetic Specialty Importer (specialty)] " + "x" * 700 + secret
    res = dict(evidence={"e1": dict(doc_id="supplier-i", title=I, text=long_passage), "e2": dict(doc_id="supplier-a", title=A, text="[A] short")}, report=dict(title="t", answer="a", claims=[]), verification=dict(ok=True))
    rv = dict(status="rejected", report_codes=[], problems=["x"], claims_rejected=[dict(text="t", full_text=CORRECT, text_chars=len(CORRECT), codes=["COMPARATIVE_FALSE"], evidence_ids=["e1", "missing"], cited_doc_ids=["supplier-i"], mentioned_supplier_ids=["i"], detail={})])
    rec = LW.recording("the query", "corpus-v", res, rv)
    assert rec["recording_version"] == 2 and rec["query"] == "the query" and rec["corpus_version"] == "corpus-v"
    passage = rec["rejected_claims_full"][0]["cited_passages"]
    assert len(passage) == 1 and len(passage[0]["text"]) == LW.PASSAGE_CHARS and passage[0]["text_chars"] == len(long_passage), "a cited passage is capped, its true length is recorded"
    blob = json.dumps(rec)
    assert secret not in blob, "text beyond the cap is never written"
    assert [e["id"] for e in rec["evidence_context"]] == ["e1", "e2"] and all(len(e["text_sha256"]) == 64 and "text" not in e for e in rec["evidence_context"]), "the rest of the context is a fingerprint, not text"
    assert rec["report_reviewed"] == res["report"], "a rejected report is kept whole (it is bounded by the answer and claim limits)"


def test_an_accepted_report_is_not_copied_into_the_record_again():
    res = dict(evidence={}, report=dict(title="t", answer="a", claims=[]), verification=None)
    assert LW.recording("q", "v", res, dict(status="accepted", report_codes=[], problems=[], claims_rejected=[]))["report_reviewed"] is None


def test_another_tenants_names_cannot_enter_a_record_because_the_boundary_sees_only_the_tenants_own_directory():
    other = [S("z", "Meridian Fitness Wholesale", P("Protein powder", "i-protein", 3000.0)), S("y", "Meridian Gym Supply", P("Protein powder", "i-protein", 3100.0))]
    ev_other = ev(*other)
    v = review("Meridian Fitness Wholesale quotes the lowest Protein powder price at $31.00 per kg.", other, ev_other, list(ev_other))
    blob = json.dumps(v)
    assert v["status"] == "rejected" and all(n not in blob for n in (A, B, I)), "records hold only names from the directory the boundary was given"
