"""Second synthetic customer: two warehouses (different seed, size, mix) behind one tenant gateway. SYNTHETIC. Isolation is design-level, not a security certification."""
import sqlite3

import pytest

from nasha_lab import enterprise_sim as es
from nasha_lab.warehouse import pipeline
from nasha_lab.warehouse.tenancy import TenantGateway, TenantPrincipal as TP

A = es.SimConfig(name="cust-a", seed=111, months=4, fast_casual=3, beer_gardens=1, target_orders=12_000, loyalty_profiles=2_000, employees=60, open_at_start=3)
B = es.SimConfig(name="cust-b", seed=222, months=4, fast_casual=2, beer_gardens=2, target_orders=20_000, loyalty_profiles=2_500, employees=70, open_at_start=4)


@pytest.fixture(scope="module")
def whs(tmp_path_factory):
    out = {}
    for t, cfg in (("alpha", A), ("bravo", B)):
        d = tmp_path_factory.mktemp(t); es.generate(cfg, d / "src"); pipeline.run(d / "src", d / "w.db"); out[t] = d / "w.db"
    return out


@pytest.fixture()
def gw(whs, tmp_path):
    g = TenantGateway(whs, {"ann": {"alpha"}, "bob": {"bravo"}, "root": {"alpha", "bravo"}}, tmp_path / "audit"); yield g; g.close()


def month(wh):
    c = sqlite3.connect(wh); m = c.execute("SELECT month FROM mart_company_month ORDER BY month").fetchall()[1][0]; c.close(); return m


def test_each_tenant_sees_only_its_own_warehouse(gw, whs):
    ma, mb = month(whs["alpha"]), month(whs["bravo"])
    ra = gw.call(TP("ann", "exec", "alpha"), "company_month", {"month": ma})["rows"][0]
    rb = gw.call(TP("bob", "exec", "bravo"), "company_month", {"month": mb})["rows"][0]
    assert ra["orders"] != rb["orders"] and ra["net_cents"] != rb["net_cents"]
    for t, ru in (("alpha", ra), ("bravo", rb)):                         # independent oracle per tenant
        c = sqlite3.connect(whs[t]); n = c.execute("SELECT count(*) FROM fact_order f JOIN dim_date d USING(date_key) WHERE d.month=?", (ma if t == "alpha" else mb,)).fetchone()[0]; c.close()
        assert ru["orders"] == n


def test_default_deny_across_tenants_and_override_attempts(gw, whs):
    m = month(whs["bravo"])
    assert gw.call(TP("ann", "exec", "bravo"), "company_month", {"month": m})["code"] == "tenant_not_granted"
    assert gw.call(TP("ann", "exec", "ghost"), "list_months")["code"] == "unknown_tenant"
    assert gw.call(TP("ann", "exec", "alpha"), "company_month", {"month": m, "tenant": "bravo"})["code"] == "tenant_override"
    assert gw.call(TP("ann", "exec", "alpha"), "company_month", {"month": m, "Warehouse": "/x/bravo.db"})["code"] == "tenant_override"
    mt = gw.metrics()
    assert mt["_gateway"] == {"tenant_not_granted": 1, "unknown_tenant": 1, "tenant_override": 2}


def test_same_location_id_resolves_per_tenant_and_site_scope_still_applies(gw, whs):
    ma = month(whs["alpha"])
    sm = TP("ann", "site_manager", "alpha", "L01")
    assert gw.call(sm, "location_month", {"month": ma, "location_id": "L01"})["ok"]
    assert gw.call(sm, "location_month", {"month": ma, "location_id": "L02"})["code"] == "site_scope"
    root = TP("root", "exec", "bravo")                                    # a multi-tenant user must name the tenant explicitly each call
    assert gw.call(root, "list_months")["tenant"] == "bravo"


def test_audit_databases_are_separate_per_tenant(gw, whs, tmp_path):
    gw.call(TP("ann", "exec", "alpha"), "list_months"); gw.call(TP("bob", "exec", "bravo"), "list_months")
    ca = sqlite3.connect(tmp_path / "audit/alpha.audit.db"); cb = sqlite3.connect(tmp_path / "audit/bravo.audit.db")
    assert [r[0] for r in ca.execute("SELECT user FROM ops_ai_audit")] == ["ann"] and [r[0] for r in cb.execute("SELECT user FROM ops_ai_audit")] == ["bob"]
