"""Characterisation of the boundary on the shape of the claim that voided both governed-workflow model outputs in model-live run 40242794366 (no model is called; no behaviour is changed).
The run record keeps only the first 200 characters of that claim and its rule codes (COMPARATIVE_FALSE + PRICE_NOT_FROM_NAMED_SUPPLIER), so the wording below is a CONSTRUCTED candidate, not the model's text. These tests document what the current rules do with
listing-style claims over the run's real stored quotes; they pin today's behaviour (including the over-strict part) so that any later change to it is deliberate and reviewed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_growth_comparative_claims import P, S, cite, codes, ev, review  # noqa: E402

NAME = "Firm white fish fillet, skinless (species TBD: mahi/redfish/cod)"
A, B, I = "Synthetic Broadline Distributor A (broadline)", "Synthetic Broadline Distributor B (broadline)", "Synthetic Specialty Importer (specialty)"
DIRECTORY = [S("a", A, P(NAME, "i-white-fish", 1167.41)), S("b", B, P(NAME, "i-white-fish", 1189.12)), S("i", I, P(NAME, "i-white-fish", 1215.67))]   # the run's stored quotes: A $11.67 (lowest), B $11.89, Importer $12.16
EVIDENCE = ev(*DIRECTORY)
HEAD = f"{NAME} (i-white-fish) is quoted by {I} at $12.16 per kg, {A} at"


def verdict(text):
    return review(text, DIRECTORY, EVIDENCE, list(EVIDENCE))


def test_a_plain_listing_of_every_true_quote_is_accepted():
    v = verdict(HEAD + f" $11.67 per kg and {B} at $11.89 per kg.")
    assert v["status"] == "accepted", codes(v)


def test_a_true_listing_that_also_says_which_quote_is_lowest_is_rejected_today_because_every_named_supplier_must_hold_the_extreme():
    v = verdict(HEAD + f" $11.67 per kg and {B} at $11.89 per kg, with {A} the lowest.")
    assert v["status"] == "rejected" and codes(v) == {"COMPARATIVE_FALSE"}
    assert v["comparisons"][0]["reason"] == "a named supplier is not the lowest quote in the comparison set"


def test_a_compact_respectively_listing_with_a_superlative_yields_exactly_the_two_codes_the_run_recorded():
    v = verdict(f"{NAME} is quoted by {I}, {A} and {B} at $12.16, $11.67 and $11.89 per kg respectively, the lowest being {A}.")
    assert codes(v) == {"COMPARATIVE_FALSE", "PRICE_NOT_FROM_NAMED_SUPPLIER"}


def test_a_genuinely_false_superlative_is_rejected_with_the_same_comparative_code_so_the_two_cases_cannot_be_told_apart_from_the_code_alone():
    v = verdict(f"{I} quotes the lowest price for {NAME} at $12.16 per kg, while {A} quotes $11.67 per kg.")
    assert codes(v) == {"COMPARATIVE_FALSE"}
