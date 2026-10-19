import datetime as dt
from nasha_lab.duplicate_triage import Candidate, assess

T = dt.datetime(2026, 3, 2, 12, 0, 0)
B = (("M01", 1, 1400),)

def row(oid, seconds=0, basket=B, location="L01"):
    return Candidate(oid, location, T + dt.timedelta(seconds=seconds), basket)

def test_legitimate_transactions_are_review_not_confirmed_duplicate():
    a, b = row("A"), row("B", 1)
    assert assess(b, [a]).decision == "REQUIRES_REVIEW"
    assert assess(a, [b]).decision == "REQUIRES_REVIEW"

def test_multiple_candidates_and_input_order_are_invariant():
    target = row("Z", 1)
    peers = [row("B"), row("A"), row("C", 2), row("X", 3)]
    one = assess(target, peers)
    assert one.decision == "REQUIRES_REVIEW"
    assert one.candidates == ("A", "B", "C")
    assert assess(target, list(reversed(peers))) == one

def test_timestamp_boundaries_and_nonmatches():
    a = row("A")
    assert assess(row("B", 1), [a]).decision == "REQUIRES_REVIEW"
    assert assess(row("B", 1.001), [a]).decision == "NO_CANDIDATE"
    assert assess(row("B", 0), [row("A", basket=(("M02", 1, 1300),))]).decision == "NO_CANDIDATE"
    assert assess(row("B", 0), [row("A", location="L02")]).decision == "NO_CANDIDATE"

def test_missing_identity_fails_closed_and_does_not_self_match():
    assert assess(row(""), [row("A")]).decision == "REQUIRES_REVIEW"
    assert assess(row("A"), [row("A")]).decision == "NO_CANDIDATE"

def test_synthetic_ambiguity_confusion_matrix():
    # Independently labelled legitimate close-in-time transactions (negative class).
    negatives = [(row("N" + str(i), 1), row("P" + str(i))) for i in range(20)]
    fp = sum(assess(a, [b]).decision == "CONFIRMED_DUPLICATE" for a, b in negatives)
    tn = len(negatives) - fp
    assert (fp, tn) == (0, 20)
    # Review outcomes are not counted as proven true negatives in production.
    assert all(assess(a, [b]).decision == "REQUIRES_REVIEW" for a, b in negatives)
