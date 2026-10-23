"""Reproducible incident investigation: an unauthorised procurement attempt can be fully reconstructed from recorded data, without secrets. SYNTHETIC data."""
import dataclasses
import json
import sqlite3

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
from nasha_lab.governed import incident as INC, tenants as T, workflow as W


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    return T.default_pair(tmp_path_factory.mktemp("inc"))


def fresh(env, tmp):
    tmp.mkdir(parents=True, exist_ok=True)
    return dataclasses.replace(env, root=tmp, ledger_path=tmp / "ledger.db", weir_db=tmp / "weir.db", trace_db=tmp / "trace.db", memory_db=tmp / "memory.db", authority=T.make_authority(env.tenant_id, env.people))


def target(env):
    c = sqlite3.connect(env.warehouse)
    r = c.execute("SELECT f.location_id, f.ingredient_id FROM scn_variance_flag f JOIN scn_procurement_reco r ON r.location_id=f.location_id AND r.ingredient_id=f.ingredient_id ORDER BY f.excess_pct DESC LIMIT 1").fetchone()
    c.close()
    return r


def test_unauthorised_procurement_attempt_is_fully_explained(pair, tmp_path):
    env = fresh(pair[0], tmp_path)
    wf = W.GovernedProcurement(env)
    try:
        quality = wf.login("tenant-a-quality", "tenant-a-quality-dev-passcode")
        r = wf.run(quality, *target(env))
        rep = INC.investigate(wf, r["corr_id"])
        a = rep["answers"]
        assert rep["found"] and rep["who"] == {"requester": "tenant-a-quality", "role": "QUALITY_LEAD"} and rep["tenant"] == "tenant-a"
        assert rep["attempted"]["ingredient_id"] == target(env)[1] and rep["attempted"]["final_state"] == "BLOCKED"
        called = [t["tool"] for t in rep["tools_called"]]
        assert "warehouse__variance_flags" in called and called[-1] == "procurement__create_draft_purchase_order"
        assert rep["tools_called"][-1]["forwarded"] is False and rep["tools_called"][-1]["held_for_approval"] is False
        assert any(e["id"].endswith("supplier_notes") and e["trust"] == "untrusted" for e in rep["evidence_retrieved"])
        assert rep["why_blocked"]["layer"] == "THE WEIR" and "procurement__create_draft_purchase_order" not in rep["why_blocked"]["policy_tools_for_role"] and rep["authorization"]["policy_rules"]["gate_write"] == "approve"
        assert rep["side_effects"]["purchase_orders_created"] == 0 and rep["side_effects"]["external_transmissions"] == 0 and rep["side_effects"]["ledger_audit_chain_valid"] and rep["side_effects"]["weir_chain_valid"]
        assert rep["authorization"]["approvals"] == []                                    # no approval was even requested
        assert set(a) == {"Who initiated the request?", "Which tenant?", "What did the agent attempt?", "Which tools were called?", "What evidence was retrieved?", "Which policy applied?", "Why was the action blocked?", "Did any side effect occur?"}
        md = INC.render_markdown(rep)
        assert "tenant-a-quality" in md and "THE WEIR" in md
    finally:
        wf.close()


def test_reports_contain_no_secrets_and_do_not_cross_tenants(pair, tmp_path):
    ea, eb = fresh(pair[0], tmp_path / "a"), fresh(pair[1], tmp_path / "b")
    wa, wb = W.GovernedProcurement(ea), W.GovernedProcurement(eb)
    try:
        t = wa.login("tenant-a-buyer", "tenant-a-buyer-dev-passcode")
        r = wa.run(t, *target(ea))
        wa.decide(r["corr_id"], wa.login("tenant-a-founder", "tenant-a-founder-dev-passcode"), True, "ok")
        rep = INC.investigate(wa, r["corr_id"])
        blob = json.dumps(rep, default=str) + INC.render_markdown(rep)
        for secret in (t, "dev-passcode", ea.authority.secret.hex()):
            assert secret not in blob
        assert rep["side_effects"]["purchase_orders_created"] == 1 and rep["authorization"]["approvals"][0]["state"] == "consumed"
        other = INC.investigate(wb, r["corr_id"])                                         # tenant B cannot see tenant A's incident
        assert other["found"] is False
    finally:
        wa.close(); wb.close()
