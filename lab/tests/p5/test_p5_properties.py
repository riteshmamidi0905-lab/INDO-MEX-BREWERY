"""Property tests (hypothesis): invariants that must hold for any input."""
from __future__ import annotations


from hypothesis import given, settings, strategies as st

from nasha_lab.service import store as ST
from nasha_lab.service.ratelimit import TokenBucketLimiter
from nasha_lab.service.schemas import RunStartIn, DecisionIn
from nasha_lab.service.obs import scrub


@given(st.lists(st.tuples(st.floats(0, 5), st.sampled_from(["a", "b", "c"])), min_size=1, max_size=60), st.floats(1, 8), st.floats(0.1, 5))
@settings(max_examples=60, deadline=None)
def test_token_bucket_never_admits_more_than_capacity_plus_refill(events, cap, refill):
    now = [0.0]; lim = TokenBucketLimiter(cap, refill, clock=lambda: now[0]); admitted = {"a": 0, "b": 0, "c": 0}
    for dt, key in events:
        now[0] += dt
        if lim.take(key)[0]: admitted[key] += 1
    for k, v in admitted.items(): assert v <= cap + refill * now[0] + 1e-6


@given(st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), max_size=6))
def test_request_hash_ignores_key_order_and_changes_with_content(d):
    a = ST.request_hash("POST", "/r", {}, d); b = ST.request_hash("POST", "/r", {}, dict(reversed(list(d.items()))))
    assert a == b and ST.request_hash("POST", "/r", {}, dict(d, extra_field_zz=1)) != a


@given(st.text(max_size=200))
def test_no_request_model_accepts_control_characters(s):
    bad = any(ord(ch) < 32 and ch not in "\t\n\r" or ord(ch) == 127 for ch in s)
    try: DecisionIn(note=s[:300]); accepted = True
    except Exception: accepted = False
    assert not (bad and accepted)


@given(st.text(max_size=80))
def test_event_id_pattern_rejects_everything_but_the_documented_shape(s):
    import re
    try: RunStartIn(event_id=s); ok = True
    except Exception: ok = False
    assert ok == bool(re.fullmatch(r"EV-[A-Z]\d+", s))


@given(st.text(max_size=100), st.text(alphabet="abcdef0123456789", min_size=6, max_size=20))
def test_scrub_never_leaks_a_password_in_an_assignment_or_url(prefix, pw):
    out = scrub(f"{prefix} password={pw} postgresql://u:{pw}@h/db")
    assert f"password={pw}" not in out and f":{pw}@" not in out
