"""Growth OS read tools on the Production AI Agent Platform's tool layer: typed validation, timeouts, classified failures, tenant binding, and the guarantee that no consequential tool or second approval path exists here."""
import os
import uuid

import pytest

ap = pytest.importorskip("agentplatform", reason="INTEGRATION UNAVAILABLE: the separate Production AI Agent Platform package is not installed (pip install -e <repo>)")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from agentplatform.models import FailureClass
from agentplatform.orchestrator.executor import ToolFailure
from agentplatform.tools.base import Risk, Tool, ToolRegistry

from nasha_lab.growth import agent_tools as AT, schema as S, service as SV, workflow as WF
from nasha_lab.warehouse import pg_hardening as H

SCHEMA = "growth_at"
USERS = {"ada": ("Ada", "OWNER"), "sam": ("Sam", "SALES"), "vic": ("Vic", "VIEWER")}
GOOD = {"budget_confirmed": True, "decision_maker": True, "timeline_days": 20, "fit": 0.9, "engagement": 0.8}


@pytest.fixture(scope="module")
def dsn(tmp_path_factory):
    if os.environ.get("NASHA_PG_DSN"):
        yield os.environ["NASHA_PG_DSN"]; return
    try:
        import pixeltable_pgserver as pg
        srv = pg.get_server(str(tmp_path_factory.mktemp("pgdata")), cleanup_mode="stop")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"INTEGRATION UNAVAILABLE: no PostgreSQL ({type(e).__name__})")
    yield srv.get_uri(); srv.cleanup()


@pytest.fixture(scope="module")
def tenants(dsn, tmp_path_factory):
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'); c.execute(f'CREATE SCHEMA "{SCHEMA}"')
    H.migrate(dsn, SCHEMA, specs=S.migrations(SCHEMA))
    root = tmp_path_factory.mktemp("gat")
    out = {}
    for t in ("tenant-nasha", "tenant-fit"):
        WF.provision_env(root, dsn, SCHEMA, t, t, "x", USERS)
        s = SV.GrowthService(dsn, SCHEMA, t, "ada")
        a = s.create_account(f"{t} acct"); c = s.create_contact(a, "P", f"{t[7:]}@example.invalid"); lead = s.create_lead(c, "synthetic-x", GOOD)
        pid = s.create_product(f"{t} product", "dish", 555); s.set_price(pid, 1850, __import__("datetime").date(2026, 10, 23), "current", "synthetic")
        out[t] = dict(lead=lead, product=pid)
        s.close()
    return dsn, out


def rt(tenants, tenant, user="sam", **kw):
    dsn, _ = tenants
    return AT.GrowthToolRuntime(SV.GrowthService(dsn, SCHEMA, tenant, user), **kw)


def test_the_tool_layer_is_the_agent_platforms_and_registers_only_read_tools():
    reg = AT.build_registry()
    assert isinstance(reg, ToolRegistry) and reg.names() == ["get_lead_context", "pipeline_summary", "price_margin"]
    assert all(isinstance(t, Tool) and t.risk is Risk.READ for t in reg._tools.values())
    assert not [n for n in reg.names() if any(w in n for w in ("apply", "write", "send", "publish", "create", "update"))]
    assert all("inputSchema" in d and d["risk"] == "read" for d in reg.descriptors())


def test_read_tools_return_real_tenant_data_through_the_executor(tenants):
    _, ids = tenants
    r = rt(tenants, "tenant-nasha")
    res, rec = r.call("get_lead_context", {"lead_id": ids["tenant-nasha"]["lead"]})
    assert res.data["signals"] == GOOD and rec.status == "ok" and rec.attempts == 1
    res, _ = r.call("price_margin", {"product_id": ids["tenant-nasha"]["product"]})
    assert abs(res.data["margin"] - (1850 - 555) / 1850) < 1e-9
    assert r.call("pipeline_summary", {})[0].text == "no opportunities"
    assert [e[0] for e in r.events][:2] == ["tool.requested", "tool.completed"]


def test_invalid_arguments_are_rejected_before_any_data_is_touched(tenants):
    r = rt(tenants, "tenant-nasha")
    for args in ({"lead_id": "x"}, {"lead_id": "lead-aaaaaaaa", "tenant_id": "tenant-fit"}, {}, {"lead_id": "lead-aaaaaaaa; DROP TABLE leads"}):
        with pytest.raises(ToolFailure) as e:
            r.call("get_lead_context", args)
        assert e.value.failure is FailureClass.TOOL_ARGS_INVALID and e.value.record.status == "invalid_args"
    with pytest.raises(ToolFailure) as e:
        r.call("apply_lead_qualification", {"lead_id": "lead-aaaaaaaa"})
    assert e.value.failure is FailureClass.TOOL_ARGS_INVALID, "the write tool does not exist on this layer"


def test_tools_are_tenant_bound_and_cannot_read_another_tenants_rows(tenants):
    _, ids = tenants
    r = rt(tenants, "tenant-nasha")
    for tool, args in (("get_lead_context", {"lead_id": ids["tenant-fit"]["lead"]}), ("price_margin", {"product_id": ids["tenant-fit"]["product"]})):
        with pytest.raises(ToolFailure) as e:
            r.call(tool, args)
        assert e.value.failure is FailureClass.TOOL_ERROR and "no such" in e.value.record.error
    other = rt(tenants, "tenant-fit")
    assert other.call("get_lead_context", {"lead_id": ids["tenant-fit"]["lead"]})[0].data["lead_id"] == ids["tenant-fit"]["lead"]


def test_a_tool_that_times_out_is_classified_and_a_tool_registered_as_consequential_cannot_be_approved_here(tenants):
    import asyncio
    r = rt(tenants, "tenant-nasha", timeout_s=0.05)
    class Slow(Tool):
        name, description, args_model, risk = "slow", "x", AT.NoArgs, Risk.READ
        async def run(self, args, ctx):
            await asyncio.sleep(0.5)
    r.registry.register(Slow())
    with pytest.raises(ToolFailure) as e:
        r.call("slow", {})
    assert e.value.failure is FailureClass.TOOL_TIMEOUT
    class Writes(Tool):
        name, description, args_model, risk = "danger", "x", AT.NoArgs, Risk.CONSEQUENTIAL
        async def run(self, args, ctx):
            raise AssertionError("must never run")
    r.registry.register(Writes())
    r.settings.__dict__["approval_mode"] = "consequential"
    async def go():
        ctx = AT.ToolContext(run_id="x", retriever=None, settings=r.settings, extras={"growth_service": r.svc})
        return await r.executor.call("danger", {}, ctx, emit=r._emit, tracer=AT.Tracer(), approval_mode="consequential")
    with pytest.raises(RuntimeError, match="THE WEIR"):
        asyncio.run(go())


def test_role_policy_still_applies_beneath_the_tool_layer(tenants):
    _, ids = tenants
    r = rt(tenants, "tenant-nasha", user="vic")                       # a viewer may read ...
    assert r.call("get_lead_context", {"lead_id": ids["tenant-nasha"]["lead"]})[1].status == "ok"
    ghost = rt(tenants, "tenant-nasha", user="ghost")                 # ... an unknown user may not (default deny)
    with pytest.raises(ToolFailure) as e:
        ghost.call("get_lead_context", {"lead_id": ids["tenant-nasha"]["lead"]})
    assert e.value.failure is FailureClass.TOOL_ERROR
