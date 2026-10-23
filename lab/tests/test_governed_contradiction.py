"""Regression: the planner abstains (escalates) when two evidence sources disagree about the discrepancy, and does not when they agree."""
import sqlite3
import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
from nasha_lab.governed import evaluation as EV, tenants as T


@pytest.fixture(scope="module")
def h(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("contra")
    return EV.Harness(tmp, T.default_pair(tmp))


def _run(h, corrupt):
    env = h.env(copy=True); loc, ing = h.target(env)
    if corrupt:
        c = sqlite3.connect(env.warehouse)
        wk = c.execute("SELECT week FROM scn_variance_flag WHERE location_id=? AND ingredient_id=? ORDER BY excess_pct DESC LIMIT 1", (loc, ing)).fetchone()[0]
        c.execute("UPDATE scn_variance_week SET variance_pct=-0.5 WHERE location_id=? AND ingredient_id=? AND week=?", (loc, ing, wk)); c.commit(); c.close()
    wf = h.wf(env)
    try:
        r = wf.run(h.tok(wf, "buyer"), loc, ing)
        pos = wf.ledger.con.execute("SELECT COUNT(*) FROM po_drafts").fetchone()[0]
        props = wf.ledger.con.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]
        return r, pos, props
    finally:
        wf.close()


def test_planner_abstains_on_contradictory_evidence(h):
    r, pos, props = _run(h, corrupt=True)
    assert r["failure"] == "CONTRADICTORY_EVIDENCE"
    assert pos == 0 and props == 0, "no proposal and no purchase order may exist when the evidence contradicts itself"
    assert "disagree" in str(r["explanation"]["summary"]).lower()


def test_consistent_evidence_still_proposes(h):
    r, pos, props = _run(h, corrupt=False)
    assert r["state"] == "AWAITING_APPROVAL" and props == 1 and pos == 0
