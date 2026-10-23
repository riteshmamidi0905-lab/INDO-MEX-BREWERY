"""Evaluation and mutation tests for the launch workflow: each mutant removes ONE control; the matching probe must pass on the real system and fail under the mutant. Defence in depth is documented where a single removed
layer is correctly stopped by the next one (see docs/growth-os/MUTATION-REVIEW.md). SYNTHETIC data only."""
import contextlib
import os
import uuid
from datetime import date
from unittest import mock

import pytest

pytest.importorskip("mcp_weir", reason="INTEGRATION UNAVAILABLE: THE WEIR (mcp_weir) not installed")
psycopg = pytest.importorskip("psycopg", reason="INTEGRATION UNAVAILABLE: psycopg not installed")

from nasha_lab.growth import agent_research as AR, launch_seed as LS, launch_workflow as LW, procurement as PRC, schema as S, seed as SD, service as SV, testing as TT, weir_launch as WL, workflow as WF
from nasha_lab.warehouse import pg_hardening as H

AS_OF = date(2026, 10, 23)
USERS = {"ada": ("Ada", "OWNER"), "omar": ("Omar", "OWNER"), "ana": ("Ana", "ANALYST"), "sam": ("Sam", "SALES"), "vic": ("Vic", "VIEWER")}


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


class Lab:
    def __init__(self, dsn, root, agent=None):
        self.dsn, self.schema = dsn, "glev_" + uuid.uuid4().hex[:8]
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(f'CREATE SCHEMA "{self.schema}"')
        H.migrate(dsn, self.schema, specs=S.migrations(self.schema))
        self.env = WF.provision_env(root / self.schema, dsn, self.schema, "tenant-nasha", "tenant-nasha", "hospitality", USERS)
        s = SV.GrowthService(dsn, self.schema, "tenant-nasha", "ada"); SD.seed_nasha(s, None, with_accounts=False)
        self.pid = LS.seed_nasha_launch(s, today=AS_OF)["project"]; s.close()
        self.wf = LW.LaunchProcurement(self.env, agent=agent, as_of=AS_OF)

    def tok(self, u): return self.wf.login(u, f"tenant-nasha-{u}-dev-passcode")

    def sql(self, sql, params=()):
        with psycopg.connect(self.dsn, autocommit=True) as c:
            c.execute(f'SET search_path TO "{self.schema}", pg_catalog, public')
            cur = c.execute(sql, params)
            return cur.fetchall() if cur.description else []

    def recorded(self, run): return self.sql("SELECT count(*) FROM audit_log WHERE action='procurement.record' AND entity_id=%s", (run,))[0][0]

    def close(self): self.wf.close()


class Lie:
    async def research(self, docs, q, v):
        return dict(mode=AR.MODE_OFFLINE, provider="offline", run_id="x", report=dict(title="t", answer="a", claims=[dict(text="Synthetic Supplier 03 (produce) quotes Lime at $0.01 per each.", evidence_ids=["e1"])], limitations=[]),
                    verification=dict(ok=True, groundedness=1, citation_validity=1), evidence={"e1": dict(doc_id="d", title="t", text="Lime: $0.01 per each")}, tool_calls=[])
    async def close(self): return None


# ---------------------------------------------------------------- probes: True = the control holds
def p_claim_verification(lab):                                         # a fabricated agent claim must be rejected
    lab.wf.agent = Lie()
    r = lab.wf.run(lab.tok("ana"), lab.pid, 2)
    return bool(lab.wf.status(r["corr_id"])["research"]["rejected_agent_output"])


def p_cheapest_quote(lab):                                             # the recommendation equals the brute-force cheapest
    r = lab.wf.run(lab.tok("ana"), lab.pid, 2)
    run = lab.wf.status(r["corr_id"]) if r.get("corr_id") else None
    return r["status"] == "AWAITING_APPROVAL" and not CHECK_PLAN(_dir(lab), run["items"], AS_OF)


def _dir(lab):
    s = SV.GrowthService(lab.dsn, lab.schema, "tenant-nasha", "ada")
    try:
        return s.supplier_directory(AS_OF, lab.pid)
    finally:
        s.close()


def p_expired_quotes(lab):                                             # quotes past their validity date must not be used
    lab.wf.as_of = date(2027, 6, 1); lab.wf._gw.clear()
    r = lab.wf.run(lab.tok("ana"), lab.pid, 2)
    return r["status"] == "BLOCKED" and r["failure"] == "NO_VALID_QUOTES"


def p_stale_proposal(lab):                                             # quotes that change after the proposal must stop the recording
    r = lab.wf.run(lab.tok("ana"), lab.pid, 2)
    s = SV.GrowthService(lab.dsn, lab.schema, "tenant-nasha", "ada")
    ids = [x[0] for x in lab.sql("SELECT id FROM supplier_products WHERE tenant_id='tenant-nasha'")]
    with TT.audited(s, "supplier_products", ids[0], also=[f"supplier_products:{i}" for i in ids]):
        s.con.execute("UPDATE supplier_products SET unit_price_cents = unit_price_cents * 0.5 WHERE tenant_id='tenant-nasha'")        # every quote halves
    s.close()
    d = lab.wf.decide(r["corr_id"], lab.tok("ada"), True)
    return d["status"] != "EXECUTED" and lab.recorded(r["corr_id"]) == 0


def p_audit_on_record(lab):                                            # an approved recommendation is recorded WITH its audit row
    r = lab.wf.run(lab.tok("ana"), lab.pid, 2)
    d = lab.wf.decide(r["corr_id"], lab.tok("ada"), True)
    return d["status"] == "EXECUTED" and lab.recorded(r["corr_id"]) == 1 and lab.sql("SELECT state FROM procurement_recommendations WHERE id=%s", (r["corr_id"],))[0][0] == "EXECUTED"


def p_approval_single_use(lab):                                        # the WEIR approval cannot be used twice at the gateway
    r = lab.wf.run(lab.tok("ana"), lab.pid, 2)
    if lab.wf.decide(r["corr_id"], lab.tok("ada"), True)["status"] != "EXECUTED":
        return False
    run = lab.wf.store.run(r["corr_id"])
    gw, _ = lab.wf._gateway(WF.ID.Identity(run["requester"], run["role"]))
    out = lab.wf.loop.run_until_complete(gw.call_tool_detailed(gw.open_session(r["corr_id"]), WL.WRITE_TOOL, lab.wf._args(run)))
    return out.forwarded is False


def p_role_policy(lab):                                                # a SALES user must not be able to get a recommendation recorded
    r = lab.wf.run(lab.tok("sam"), lab.pid, 2)
    if r["status"] == "AWAITING_APPROVAL":
        lab.wf.decide(r["corr_id"], lab.tok("ada"), True)
    return r["status"] != "EXECUTED" and lab.recorded(r.get("corr_id")) == 0


def p_no_invented_contacts(lab):                                       # supplier contacts cannot be stored
    s = SV.GrowthService(lab.dsn, lab.schema, "tenant-nasha", "ada")
    try:
        s.add_supplier("Contactful", "c", "a", "lead_unverified", "search_result", source_url="https://example.org/x", contact_channel="info@x.example"); ok = False
    except psycopg.errors.CheckViolation:
        ok = True
    s.close(); return ok


def lax_valid(p, as_of):
    return p["price_class"] != "NONE_PUBLISHED" and p["unit_price_cents"] is not None


def worst_compare(directory, need_map, as_of):                        # mutant: picks the MOST expensive quote
    items, totals, flags = PRC_COMPARE(directory, need_map, as_of)
    return items, totals, flags


PRC_COMPARE = PRC.compare
CHECK_PLAN = PRC.check_plan                    # the real re-derivation, captured before any mutant patches the module


def skip_digest(orig):
    return lambda plan: "constant"


def lax_consume(self, session_id, call_hash):
    row = self._db.execute("SELECT id FROM approvals WHERE session_id=? AND call_hash=? AND state IN ('approved','consumed') ORDER BY created LIMIT 1", (session_id, call_hash)).fetchone()
    return str(row[0]) if row else None


def no_claim_check(report, evidence, directory):
    return []


def drop_record_audit(orig):
    def f(self, action, entity, entity_id, decision, detail=None):
        return None if action == "procurement.record" else orig(self, action, entity, entity_id, decision, detail)
    return f


def cheapest_broken():
    return mock.patch.object(PRC, "check_plan", lambda *a, **k: []), mock.patch.object(PRC, "compare", lambda d, n, a: _reverse(PRC_COMPARE(d, n, a)))


def _reverse(res):
    items, totals, flags = res
    return items, totals, flags


def role_open():
    st = contextlib.ExitStack()
    st.enter_context(mock.patch.object(WL, "INITIATE_ROLES", WL.INITIATE_ROLES | {"SALES"}))
    st.enter_context(mock.patch.dict(SV.POLICY, {"procurement.record": SV.POLICY["procurement.record"] | {"SALES"}}))
    return st


def no_check_and_costly():
    """Mutant: the independent re-derivation is removed AND the comparison chooses the most expensive valid quote."""
    import math
    def costly(directory, need_map, as_of):
        items, totals, flags = PRC_COMPARE(directory, need_map, as_of)
        for it in items:
            if it["chosen"] is None:
                continue
            worst = None
            for s in directory:
                for p in s["products"]:
                    if p["ingredient_ref"] == it["ingredient_ref"] and PRC._valid(p, as_of):
                        pack = float(p["pack_qty"] or 1); packs = max(1, math.ceil(it["need_qty"] / pack - 1e-9))
                        c = round(packs * pack * float(p["unit_price_cents"]))
                        if worst is None or c > worst["cost_cents"]:
                            worst = dict(it["chosen"], supplier_id=s["id"], supplier=s["name"], cost_cents=c, buy_qty=packs * pack, packs=packs)
            it["chosen"] = worst
        tot = {}
        for it in items:
            c = it["chosen"]
            if c:
                t = tot.setdefault(c["supplier_id"], dict(supplier_id=c["supplier_id"], supplier=c["supplier"], cost_cents=0, min_order_cents=0, items=0, price_classes={"SYNTHETIC_QUOTE"}, below_minimum_order=False))
                t["cost_cents"] += c["cost_cents"]; t["items"] += 1
        for t in tot.values():
            t["price_classes"] = sorted(t["price_classes"])
        return items, list(tot.values()), flags
    st = contextlib.ExitStack()
    st.enter_context(mock.patch.object(PRC, "compare", costly)); st.enter_context(mock.patch.object(PRC, "check_plan", lambda *a, **k: []))
    return st


MUTANTS = [
    ("agent claim verification removed", p_claim_verification, None, lambda: mock.patch.object(AR, "verify_claims", no_claim_check)),
    ("most expensive quote chosen and independent re-derivation removed", p_cheapest_quote, None, no_check_and_costly),
    ("quote validity dates ignored", p_expired_quotes, None, lambda: mock.patch.object(PRC, "_valid", lax_valid)),
    ("stale-proposal check removed (proposal fingerprint ignored)", p_stale_proposal, None, lambda: mock.patch.object(PRC, "digest", skip_digest(PRC.digest))),
    ("audit row for the recorded recommendation dropped", p_audit_on_record, None, lambda: mock.patch.object(SV.GrowthService, "_audit", drop_record_audit(SV.GrowthService._audit))),
    ("approval never consumed", p_approval_single_use, None, lambda: mock.patch.object(WF.WeirStore, "consume_approval", lax_consume)),
    ("SALES role allowed to record recommendations at THE WEIR and in the service", p_role_policy, None, role_open),
    ("supplier contact rule dropped", p_no_invented_contacts, "ALTER TABLE suppliers DROP CONSTRAINT suppliers_check", None)]
PROBES = [m[1] for m in MUTANTS]


@pytest.mark.parametrize("probe", sorted(set(PROBES), key=lambda f: f.__name__), ids=lambda f: f.__name__)
def test_every_probe_passes_on_the_unmutated_system(dsn, tmp_path, probe):
    lab = Lab(dsn, tmp_path)
    try:
        assert probe(lab) is True, probe.__name__
    finally:
        lab.close()


@pytest.mark.parametrize("name,probe,sql,patch", MUTANTS, ids=[m[0].split(" (")[0][:40] for m in MUTANTS])
def test_each_mutant_is_detected_by_its_probe(dsn, tmp_path, name, probe, sql, patch):
    lab = Lab(dsn, tmp_path)
    try:
        if sql:
            cons = lab.sql("SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass AND contype='c' AND pg_get_constraintdef(oid) LIKE %s", (f'"{lab.schema}".suppliers', "%contact_channel%"))
            for (c,) in cons:
                lab.sql(f'ALTER TABLE "{lab.schema}".suppliers DROP CONSTRAINT "{c}"')
        if patch:
            with patch():
                held = probe(lab)
        else:
            held = probe(lab)
        assert held is False, f"mutant survived: {name}"
    finally:
        lab.close()
