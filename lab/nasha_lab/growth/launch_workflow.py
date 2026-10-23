"""Governed procurement recommendation for a launch project, on THE WEIR with PostgreSQL state and a human decision:

 request -> read stored supplier data (through THE WEIR) -> demand from the financial scenario -> ingredient needs (existing recipe BOM) -> agent-assisted supplier research (Production AI Agent Platform engine,
 read-only tools; deterministic fallback if unavailable) -> independent claim verification -> deterministic quote comparison -> independent re-derivation -> proposal fingerprint -> THE WEIR holds the write ->
 a DIFFERENT owner approves or rejects -> the recommendation is recorded and audited. Nothing is ordered, nobody is contacted.

The agent contributes the research brief and its cited claims; every number in the recommendation is computed from stored quotes and re-derived independently, never taken from agent text."""
import asyncio
import hashlib
import json
import time
import uuid
from datetime import date

import psycopg
from psycopg.types.json import Jsonb

from .. import identity as ID
from . import agent_research as AR, launch as L, model_boundary as MB, procurement as PRC, service as SV, weir_launch as WL
from .workflow import WeirCaller, WeirStore, Gateway, parse_policy

WORKFLOW = "procurement_recommendation"
FAILURES = ("AUTH_DENIED", "ROLE_DENIED", "TOOL_DENIED", "TOOL_TIMEOUT", "TOOL_BAD_RESPONSE", "TOOL_ERROR", "DB_ERROR", "NO_SUCH_PROJECT", "NO_SCENARIO", "NO_VALID_QUOTES", "VERIFICATION_FAILED", "APPROVAL_EXPIRED",
            "APPROVAL_REPLAY", "APPROVAL_MISMATCH", "NOT_AWAITING_APPROVAL", "MAKER_CHECKER", "STALE_PROPOSAL", "DUPLICATE_REQUEST", "REAPPROVAL_REQUIRED")
TOOL_TIMEOUT_S, AGENT_TIMEOUT_S = 5.0, 120.0
COLS = ("id", "requester", "role", "project_id", "period", "state", "agent_mode", "items", "totals", "research", "proposal_hash", "approval_id", "failure", "decided_by", "version")


class LaunchStore:
    """procurement_recommendations / launch_events for ONE tenant, over a connection of the unprivileged application role with the tenant set (row-level security applies)."""

    def __init__(self, env):
        self.tenant = env.tenant_id
        self.con = psycopg.connect(SV.app_dsn(env.dsn), autocommit=True)
        self.con.execute(f'SET search_path TO "{env.schema}", pg_catalog, public')
        self.con.execute("SELECT set_config('app.tenant_id', %s, false)", (env.tenant_id,))

    def close(self):
        self.con.close()

    def start(self, corr, requester, role, project_id, period, idem):
        r = self.con.execute("INSERT INTO procurement_recommendations (tenant_id,id,requester,role,project_id,period,idem_key,state) VALUES (%s,%s,%s,%s,%s,%s,%s,'STARTED') ON CONFLICT (tenant_id, idem_key) DO NOTHING RETURNING id",
                             (self.tenant, corr, requester, role, project_id, period, idem)).fetchone()
        if r:
            return corr, False
        return self.con.execute("SELECT id FROM procurement_recommendations WHERE tenant_id=%s AND idem_key=%s", (self.tenant, idem)).fetchone()[0], True

    def run(self, corr):
        r = self.con.execute(f"SELECT {', '.join(COLS)} FROM procurement_recommendations WHERE tenant_id=%s AND id=%s", (self.tenant, corr)).fetchone()
        return None if not r else dict(zip(COLS, r))

    def set(self, corr, state, **f):
        cols, vals = ["state=%s"], [state]
        for k, v in f.items():
            cols.append(f"{k}=%s"); vals.append(Jsonb(v) if k in ("items", "totals", "research") and v is not None else v)
        self.con.execute(f"UPDATE procurement_recommendations SET {', '.join(cols)} WHERE tenant_id=%s AND id=%s", (*vals, self.tenant, corr))

    def event(self, corr, kind, **detail):
        with self.con.transaction():
            n = self.con.execute("SELECT coalesce(max(seq),0)+1 FROM launch_events WHERE tenant_id=%s AND run_id=%s", (self.tenant, corr)).fetchone()[0]
            self.con.execute("INSERT INTO launch_events (tenant_id,run_id,seq,kind,detail) VALUES (%s,%s,%s,%s,%s)", (self.tenant, corr, n, kind, Jsonb(json.loads(json.dumps(detail, default=str)))))

    def events(self, corr):
        return [dict(seq=r[0], ts=r[1].isoformat(), kind=r[2], **r[3]) for r in self.con.execute("SELECT seq, ts, kind, detail FROM launch_events WHERE tenant_id=%s AND run_id=%s ORDER BY seq", (self.tenant, corr))]


def _dates(directory):
    """JSON round trip of the supplier directory loses date types; restore them."""
    for s in directory:
        s["verified_on"] = date.fromisoformat(s["verified_on"]) if s.get("verified_on") else None
        for p in s["products"]:
            for k in ("valid_from", "valid_to"):
                p[k] = date.fromisoformat(p[k]) if p.get(k) else None
    return directory


class LaunchProcurement(WeirCaller):
    def __init__(self, env, agent=None, clock=time.time, ttl=900, as_of=None, fault=None, tool_timeout=TOOL_TIMEOUT_S, agent_timeout=AGENT_TIMEOUT_S):
        self.env, self.agent, self.clock, self.ttl, self.fault, self.tool_timeout, self.agent_timeout = env, agent, clock, ttl, fault, tool_timeout, agent_timeout
        self.as_of = as_of or date.today()
        self.store = LaunchStore(env)
        self.weir = WeirStore(str(env.weir_db), clock)
        self.loop = asyncio.new_event_loop()
        self._gw, self._svc = {}, {}

    def close(self):
        for s in self._svc.values():
            s.close()
        if self.agent:
            self.loop.run_until_complete(self.agent.close())
        self.store.close(); self.loop.close()

    def _service(self, identity):
        if identity.id not in self._svc:
            self._svc[identity.id] = SV.GrowthService(self.env.dsn, self.env.schema, self.env.tenant_id, identity.id)
        return self._svc[identity.id]

    def _gateway(self, identity):
        key = (identity.role, identity.id)
        if key not in self._gw:
            svc, ups, rec = self._service(identity), {}, None
            if identity.role in WL.READ_ROLES:
                ups["launch"] = WL.LaunchReadUpstream(svc, self.as_of, self.fault)
            if identity.role in WL.INITIATE_ROLES:
                rec = WL.ProcureUpstream(svc, self.store, self.as_of); ups["procure"] = rec
            gw = Gateway(parse_policy(WL.policy_for(identity.role, self.ttl)), self.weir, ups, clock=self.clock)
            self.loop.run_until_complete(gw.start())
            self._gw[key] = (gw, rec)
        return self._gw[key]

    def _identify(self, session):
        return self.env.authority.identify(session)

    def login(self, user, passcode):
        return self.env.authority.login(user, passcode)

    def _result(self, corr, status, **kw):
        run = self.store.run(corr) or {}
        return dict(corr_id=corr, tenant=self.env.tenant_id, workflow=WORKFLOW, status=status, state=run.get("state"), project_id=run.get("project_id"), side_effects=dict(orders_placed=0, suppliers_contacted=0, emails_sent=0), **kw)

    def _fail(self, corr, cls, status="BLOCKED", state="BLOCKED", detail="", **kw):
        assert cls in FAILURES, cls
        self.store.event(corr, "failure", failure_class=cls, detail=str(detail)[:200])
        if self.store.run(corr) and self.store.run(corr)["state"] not in ("EXECUTED", "REJECTED"):
            self.store.set(corr, state, failure=f"{cls}:{str(detail)[:80]}")
        return self._result(corr, status, failure=cls, detail=str(detail)[:200], **kw)

    def _audit_deny(self, who, action, corr, why, codes=None):
        """A refusal is also written to the tenant's hash-chained audit log (not only the workflow's own trail and THE WEIR's ledger), in its own short transaction."""
        try:
            self._service(who)._audit(action, "procurement_recommendations", corr, "deny", dict({"why": why}, **({"codes": list(codes)} if codes else {})))      # the per-user service connection is cached and shared: never closed here
        except Exception:  # noqa: BLE001 - never let the audit of a refusal change the refusal
            pass

    def _args(self, run):
        return dict(proposal_id=run["id"], project_id=run["project_id"], proposal_hash=run["proposal_hash"], period_weeks=int(run["period"].split()[0]), note=f"Record procurement recommendation for {run['period']}")

    # ---------------------------------------------------------------- the run
    def run(self, session, project_id, period_weeks=4, idempotency_key=None, request_id=None):
        corr = "pr-" + uuid.uuid4().hex[:12]
        idem = idempotency_key or f"auto-{corr}"
        try:
            who = self._identify(session)
        except ID.AuthError as e:
            return dict(corr_id=corr, tenant=self.env.tenant_id, workflow=WORKFLOW, status="DENIED", state=None, failure="AUTH_DENIED", detail=e.code, side_effects=dict(orders_placed=0, suppliers_contacted=0, emails_sent=0))
        svc = self._service(who)
        if svc.role != who.role:
            return dict(corr_id=corr, tenant=self.env.tenant_id, workflow=WORKFLOW, status="DENIED", state=None, failure="AUTH_DENIED", detail="ROLE_MISMATCH", side_effects=dict(orders_placed=0, suppliers_contacted=0, emails_sent=0))
        if not isinstance(period_weeks, int) or not 1 <= period_weeks <= 26:
            return dict(corr_id=corr, tenant=self.env.tenant_id, workflow=WORKFLOW, status="DENIED", state=None, failure="NO_SUCH_PROJECT", detail="period_weeks must be 1-26", side_effects=dict(orders_placed=0, suppliers_contacted=0, emails_sent=0))
        if not svc.con.execute("SELECT 1 FROM launch_projects WHERE tenant_id=%s AND id=%s", (self.env.tenant_id, project_id)).fetchone():
            return dict(corr_id=corr, tenant=self.env.tenant_id, workflow=WORKFLOW, status="DENIED", state=None, failure="NO_SUCH_PROJECT", detail="no such project in this tenant", side_effects=dict(orders_placed=0, suppliers_contacted=0, emails_sent=0))
        first, dup = self.store.start(corr, who.id, who.role, project_id, f"{period_weeks} weeks", idem)
        if dup:
            self.store.event(first, "failure", failure_class="DUPLICATE_REQUEST", request=request_id)
            return self._result(first, "DUPLICATE", failure="DUPLICATE_REQUEST", duplicate_of=first)
        self.store.event(corr, "stage", stage="P01", name="request_received", project_id=project_id, period_weeks=period_weeks, request_id=request_id)
        self.store.event(corr, "auth", decision="allow", user=who.id, role=who.role, tenant=self.env.tenant_id)
        if who.role not in WL.READ_ROLES | WL.INITIATE_ROLES:
            self._audit_deny(who, "procurement.request", corr, f"role {who.role} may not request a recommendation")
            return self._fail(corr, "ROLE_DENIED", status="DENIED", detail=who.role)
        gw, rec = self._gateway(who)
        sess = gw.open_session(corr)
        out, parsed, fail = self._call(gw, sess, WL.READ_TOOL, dict(project_id=project_id), corr, "P03")
        if fail:
            if fail == "TOOL_DENIED":
                self._audit_deny(who, "procurement.request", corr, f"role {who.role} may not read the project's supplier data")
            return self._fail(corr, fail, state="FAILED" if fail != "TOOL_DENIED" else "BLOCKED", detail="could not read the project's supplier data")
        if not parsed.get("project"):
            return self._fail(corr, "NO_SUCH_PROJECT", detail=project_id)
        if not parsed.get("requirements") and not (parsed.get("use_recipes") and parsed.get("scenario")):
            return self._fail(corr, "NO_SCENARIO", detail="the project has no stated requirements and no priced products to derive needs from")
        directory = _dates(parsed["directory"]); scen = parsed["scenario"]
        self.store.event(corr, "stage", stage="P03", name="data_read", suppliers=len(directory), priced_suppliers=sum(1 for s in directory if s["priced_products"]), project=parsed["project"]["name"])
        plan = PRC.plan(directory, scen, period_weeks, self.as_of, parsed.get("requirements") or [], bool(parsed.get("use_recipes")))
        self.store.event(corr, "stage", stage="P04", name="demand_and_needs", ingredients=len(plan["items"]), portions=sum(plan["portions"].values()), needs_from=plan["needs_from"], industry=parsed["project"]["industry"])
        if not any(i["chosen"] for i in plan["items"]):
            return self._fail(corr, "NO_VALID_QUOTES", detail="no valid priced quote exists for any needed ingredient")
        # P05: agent-assisted research (read-only), verified independently; deterministic fallback
        research = self._research(corr, directory, plan)
        # P06: deterministic recommendation, re-derived independently
        problems = PRC.check_plan(directory, plan, self.as_of)
        if problems:
            return self._fail(corr, "VERIFICATION_FAILED", state="FAILED", detail=problems[0])
        self.store.event(corr, "stage", stage="P06", name="recommendation", total_cost_cents=plan["total_cost_cents"], suppliers=len(plan["supplier_totals"]), flags=[f["kind"] for f in plan["flags"]])
        self.store.event(corr, "stage", stage="P06", name="independent_check", result="every chosen quote is the cheapest valid whole-pack option and all totals add up")
        h = PRC.digest(plan)
        self.store.set(corr, "PROPOSED", items=plan, totals=dict(total_cost_cents=plan["total_cost_cents"], suppliers=plan["supplier_totals"], flags=plan["flags"]), research=research, agent_mode=research["mode"], proposal_hash=h)
        self.store.event(corr, "stage", stage="P07", name="proposal", proposal_hash=h[:16])
        out_w, _, fail = self._call(gw, sess, WL.WRITE_TOOL, self._args(self.store.run(corr)), corr, "P08")
        if out_w is None:
            return self._fail(corr, fail or "TOOL_ERROR", state="FAILED")
        if out_w.forwarded:
            return self._fail(corr, "TOOL_ERROR", state="FAILED", detail="write forwarded without approval")
        if not out_w.approval_id:
            self.store.event(corr, "stage", stage="P08", name="weir_denied", codes=out_w.codes)
            self._audit_deny(who, "procurement.request", corr, f"THE WEIR refused the write: the {who.role.lower()} role has no permission to record a procurement recommendation", out_w.codes)
            return self._fail(corr, "TOOL_DENIED", detail=",".join(out_w.codes) or "denied by policy")
        self.store.set(corr, "AWAITING_APPROVAL", approval_id=out_w.approval_id)
        self.store.event(corr, "stage", stage="P08", name="held_for_approval", approval_id=out_w.approval_id, codes=out_w.codes, ttl_s=self.ttl)
        return self._result(corr, "AWAITING_APPROVAL", approval_id=out_w.approval_id, agent_mode=research["mode"], total_cost_cents=plan["total_cost_cents"])

    def _research(self, corr, directory, plan):
        """Agent run when an agent is configured and healthy, otherwise (or if its output fails independent verification) the deterministic summary. Always records what ran."""
        names = {i["ingredient_ref"] for i in plan["items"]}
        q = ("Which suppliers quote the lowest published prices for the ingredients needed, and what are the verification status, data freshness and price limitations of each supplier's data? "
             "Cite the supplier records.")
        docs = AR.supplier_documents(directory)
        version = hashlib.sha256(json.dumps({k: v[1] for k, v in sorted(docs.items())}).encode()).hexdigest()
        res, why = None, None
        if self.agent is None:
            why = "no agent configured"
        else:
            try:
                res = self.loop.run_until_complete(asyncio.wait_for(self.agent.research(docs, q, version), self.agent_timeout))
            except AR.AgentUnavailable as e:
                why = f"agent unavailable: {e.reason}"
            except asyncio.TimeoutError:
                why = "agent timed out"
            except Exception as e:  # noqa: BLE001 - any engine failure degrades to the fallback; it must never block or alter the deterministic recommendation
                why = f"agent error: {type(e).__name__}"
        rejected = None
        if res is not None:
            problems = AR.verify_claims(res["report"], res["evidence"], directory)
            rv = MB.review(res["report"], res["evidence"], directory, res.get("tool_calls", []))
            problems = problems + [p for p in rv["problems"] if p not in problems]
            self.store.event(corr, "stage", stage="P05", name="agent_research", mode=res["mode"], provider=res["provider"], agent_run=res["run_id"], claims=len(res["report"].get("claims", [])) if isinstance(res["report"], dict) and isinstance(res["report"].get("claims", []), list) else 0, evidence=len(res["evidence"]),
                             platform_verification=res["verification"] and dict(ok=res["verification"]["ok"], groundedness=res["verification"]["groundedness"]), independent_problems=problems,
                             boundary=dict(status=rv["status"], accepted=len(rv["claims_accepted"]), rejected=[dict(codes=r["codes"]) for r in rv["claims_rejected"]], report_codes=rv["report_codes"], flags=rv["flags"]))
            if rv["status"] == "abstained":
                rejected = None; why = "agent abstained: the records do not support a conclusion"; res = None
            elif problems or rv["status"] != "accepted" or (res["verification"] and not res["verification"]["ok"]):
                rejected = dict(problems=problems, platform_ok=res["verification"] and res["verification"]["ok"], codes=sorted({c for r in rv["claims_rejected"] for c in r["codes"]} | set(rv["report_codes"]))); res = None; why = "agent output failed verification"
            else:
                res["boundary"] = dict(status=rv["status"], uncertainty=rv["uncertainty"], flags=rv["flags"], claims_accepted=len(rv["claims_accepted"]))
        if res is None:
            res = AR.deterministic_summary(directory, names)
            self.store.event(corr, "stage", stage="P05", name="agent_fallback", reason=why, mode=res["mode"])
        res["fallback_reason"] = why; res["rejected_agent_output"] = rejected
        if "boundary" not in res:
            res["boundary"] = dict(status="not_applicable", uncertainty=MB.computed_uncertainty(directory, {s["id"] for s in directory if s["priced_products"]}), flags=[], claims_accepted=0)
        return res

    # ---------------------------------------------------------------- the human decision and execution
    def decide(self, corr_id, session, approve=True, comment="", execute=True, request_id=None):
        run = self.store.run(corr_id)
        deny = lambda **k: dict(corr_id=corr_id, tenant=self.env.tenant_id, status="DENIED", side_effects=dict(orders_placed=0, suppliers_contacted=0, emails_sent=0), **k)
        if run is None:
            return deny(failure="NOT_AWAITING_APPROVAL", detail="no such run in this tenant")
        try:
            who = self._identify(session)
        except ID.AuthError as e:
            self.store.event(corr_id, "approval_decision", decision="deny", code=e.code)
            return self._fail(corr_id, "AUTH_DENIED", status="DENIED", state=run["state"], detail=e.code)
        if not ID.Authority.role_allowed(who.role, "record_procurement_recommendation", {}):
            self.store.event(corr_id, "approval_decision", decision="deny", code="ROLE_NOT_PERMITTED", user=who.id, role=who.role)
            self._audit_deny(who, "procurement.approve", corr_id, f"role {who.role} may not approve")
            return self._fail(corr_id, "ROLE_DENIED", status="DENIED", state=run["state"], detail=f"{who.role} may not approve")
        if who.id == run["requester"]:
            self.store.event(corr_id, "approval_decision", decision="deny", code="MAKER_CHECKER", user=who.id)
            self._audit_deny(who, "procurement.approve", corr_id, "the requester may not approve their own request")
            return self._fail(corr_id, "MAKER_CHECKER", status="DENIED", state=run["state"], detail="requester may not approve their own request")
        if run["state"] != "AWAITING_APPROVAL":
            cls = "APPROVAL_REPLAY" if run["state"] in ("EXECUTED", "APPROVED") else "NOT_AWAITING_APPROVAL"
            self.store.event(corr_id, "approval_decision", decision="deny", code=cls, state=run["state"])
            self._audit_deny(who, "procurement.approve", corr_id, f"{cls}: the recommendation is {run['state']}")
            return self._result(corr_id, "DENIED", failure=cls, detail=run["state"])
        aid = run["approval_id"]
        ap = self.weir.get_approval(aid) if aid else None
        if ap is None or ap.session_id != corr_id or ap.tool != WL.WRITE_TOOL:
            self._audit_deny(who, "procurement.approve", corr_id, "the approval does not belong to this run")
            return self._fail(corr_id, "APPROVAL_MISMATCH", status="DENIED", state=run["state"], detail="approval does not belong to this run")
        if not approve:
            self.weir.resolve_approval(aid, False, by=who.id)
            self.store.set(corr_id, "REJECTED", failure=f"rejected: {comment[:60]}", decided_by=who.id)
            self.store.event(corr_id, "approval_decision", decision="reject", by=who.id, comment=comment[:120])
            return self._result(corr_id, "REJECTED")
        state = self.weir.resolve_approval(aid, True, by=who.id)
        self.store.event(corr_id, "approval_decision", decision="approve" if state == "approved" else state, by=who.id, role=who.role, approval_id=aid, comment=comment[:120])
        if state == "expired":
            return self._fail(corr_id, "APPROVAL_EXPIRED", status="EXPIRED", state="FAILED", detail="approval expired before it was granted")
        if state != "approved":
            return self._fail(corr_id, "APPROVAL_REPLAY" if state.startswith("already") else "APPROVAL_MISMATCH", status="DENIED", state=run["state"], detail=state)
        self.store.set(corr_id, "APPROVED", decided_by=who.id)
        if not execute:
            return self._result(corr_id, "APPROVED_NOT_EXECUTED", approval_id=aid)
        return self.execute_approved(corr_id, approver=who)

    def execute_approved(self, corr_id, approver=None):
        run = self.store.run(corr_id)
        if run is None or run["state"] != "APPROVED":
            return self._result(corr_id, "DENIED", failure="NOT_AWAITING_APPROVAL", detail=(run or {}).get("state"))
        ident = ID.Identity(run["requester"], run["role"])
        gw, rec = self._gateway(ident)
        sess = gw.open_session(corr_id)
        approver_id = approver.id if approver else (self.weir.get_approval(run["approval_id"]).resolved_by or "unknown")
        rec.context = dict(approval_id=run["approval_id"], approved_by=approver_id, corr_id=corr_id)
        out, parsed, fail = self._call(gw, sess, WL.WRITE_TOOL, self._args(run), corr_id, "P09")
        rec.context = None
        if out is not None and not out.forwarded:
            self.store.set(corr_id, "AWAITING_APPROVAL", approval_id=out.approval_id, failure="REAPPROVAL_REQUIRED:approved call no longer matches")
            self.store.event(corr_id, "failure", failure_class="REAPPROVAL_REQUIRED", new_approval=out.approval_id, codes=out.codes)
            return self._result(corr_id, "REAPPROVAL_REQUIRED", failure="REAPPROVAL_REQUIRED", approval_id=out.approval_id)
        err = (parsed or {}).get("error", "") if isinstance(parsed, dict) else ""
        if fail:
            cls = "STALE_PROPOSAL" if err == "STALE_PROPOSAL" else fail
            if cls not in FAILURES:
                cls = "TOOL_ERROR"
            self.store.set(corr_id, "FAILED", failure=f"{cls}:{err or fail}"[:120])
            self.store.event(corr_id, "failure", failure_class=cls, detail=(err or fail))
            return self._result(corr_id, "FAILED", failure=cls, detail=err or fail)
        self.store.event(corr_id, "stage", stage="P09", name="recommendation_recorded")
        self.store.event(corr_id, "stage", stage="P10", name="no_order_no_contact", orders_placed=0, suppliers_contacted=0)
        return self._result(corr_id, "EXECUTED")

    def status(self, corr_id):
        r = self.store.run(corr_id)
        return None if r is None else dict(r, events=self.store.events(corr_id))

    def trace(self, corr_id):
        return self.store.events(corr_id)
