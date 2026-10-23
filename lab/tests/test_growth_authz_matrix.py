"""Authorisation correctness for both businesses: every role against every launch write, with expected outcomes written from the intended policy. A role that may not do something gets 403 and leaves a denial in the audit log;
a role that may, succeeds. Policy-widening mutants must be noticed. SYNTHETIC tenants; the writes are throwaway test data."""
import pytest

psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")
pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
pytest.importorskip("fastapi")
from test_growth_journey import A, B, H, sql, world  # noqa: E402,F401

from nasha_lab.growth import authz_eval as AZ  # noqa: E402


def run_both(world):
    c, envs, _ = world
    rows = []
    for t in (A, B):
        pid = c.get(f"/v1/tenants/{t}/projects", headers=H(envs, "vic", t)).json()["items"][0]["id"]
        sid = c.get(f"/v1/tenants/{t}/suppliers", headers=H(envs, "vic", t)).json()["items"][0]["id"]
        rows += AZ.run(c, envs, t, pid, sid)
    return rows


def test_every_role_gets_exactly_the_access_the_policy_intends_in_both_businesses(world):
    s = AZ.summary(run_both(world))
    assert s["checks"] == 9 * 6 * 2 and s["correct"] == s["checks"] and not s["wrong"], s["wrong"]
    assert s["allowed_checked"] > 0 and s["denied_checked"] > s["allowed_checked"], "default deny: most (role, operation) pairs are refusals"


def test_every_refusal_is_in_the_chained_audit_log_and_changes_nothing(world):
    before = {t: sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND decision='deny'", (t,))[0][0] for t in (A, B)}
    rows = run_both(world)
    denied = {t: sum(1 for r in rows if r["tenant"] == t and r["expected"] == "deny") for t in (A, B)}
    for t in (A, B):
        added = sql(world, "SELECT count(*) FROM audit_log WHERE tenant_id=%s AND decision='deny'", (t,))[0][0] - before[t]
        assert added >= denied[t], (t, added, denied[t])
    c, envs, _ = world
    assert all(c.get(f"/v1/tenants/{t}/audit/verify", headers=H(envs, "ada", t)).json()["chain_valid"] for t in (A, B))


@pytest.mark.parametrize("name", sorted(AZ.MUTANTS))
def test_a_quietly_widened_policy_is_noticed_by_the_matrix(world, name):
    action, role = AZ.MUTANTS[name]
    with AZ.widened(action, role):
        s = AZ.summary(run_both(world))
    assert s["wrong"], f"widening {action} for {role} must make at least one check fail"
