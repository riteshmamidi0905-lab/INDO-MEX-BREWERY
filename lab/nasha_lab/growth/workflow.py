"""Governed lead-qualification workflow (D-90 Phase B): synthetic lead -> source and consent validation -> evidence-backed qualification recommendation -> THE WEIR authorization -> held for approval ->
a DIFFERENT authorised person approves or rejects that exact action -> the CRM lead is updated -> append-only audit and workflow trace -> traceable result.

It follows the pattern of the existing governed procurement workflow and reuses its pieces: THE WEIR gateway and approval store, the tenant `identity.Authority` for sessions, and the state-machine / classified-failure /
idempotency / reconcile-after-failure approach. State lives in PostgreSQL (workflow_runs, workflow_events) under row-level security. NOTHING is ever sent: there is no send path, and the tests block the network.
This is a deterministic, explicitly rule-based workflow; it does NOT run on the Production AI Agent Platform (see docs/growth-os/AGENT-PLATFORM-INTEGRATION.md)."""
import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from mcp_weir.gateway import Gateway
from mcp_weir.policy import parse_policy
from mcp_weir.store import Store as WeirStore
from psycopg.types.json import Jsonb

from .. import identity as ID
from ..governed.tenants import make_authority
from ..warehouse.ops_ai_weir import call_hash
from . import qualification as Q, service as SV, weir_growth as WG

FAILURES = ("AUTH_DENIED", "ROLE_DENIED", "TOOL_DENIED", "TOOL_TIMEOUT", "TOOL_BAD_RESPONSE", "TOOL_ERROR", "DB_ERROR", "INVALID_SOURCE", "SUPPRESSED_CONTACT", "NO_SUCH_LEAD", "INVALID_EVIDENCE", "VALIDATION_FAILED",
            "APPROVAL_EXPIRED", "APPROVAL_REPLAY", "APPROVAL_MISMATCH", "NOT_AWAITING_APPROVAL", "MAKER_CHECKER", "STALE_PROPOSAL", "DUPLICATE_REQUEST", "REAPPROVAL_REQUIRED", "TENANT_MISMATCH")
TOOL_TIMEOUT_S = 5.0
WORKFLOW = "lead_qualification"


@dataclass
class GrowthEnv:
    tenant_id: str
    dsn: str
    schema: str
    root: Path
    authority: object
    people: dict = field(default_factory=dict)
    weir_db: Path = None


def provision_env(root, dsn, schema, tenant_id, name, vertical, users, clock=None, ttl=900):
    """users: {user_id: (display_name, role)}. Passcodes are the synthetic dev convention `{tenant}-{user}-dev-passcode`."""
    root = Path(root) / tenant_id
    root.mkdir(parents=True, exist_ok=True)
    SV.provision(dsn, schema, tenant_id, name, vertical, [(u, d, r) for u, (d, r) in users.items()])
    people = {u: (r, f"{tenant_id}-{u}-dev-passcode") for u, (d, r) in users.items()}
    extra = {"clock": clock} if clock else {}
    return GrowthEnv(tenant_id, dsn, schema, root, make_authority(tenant_id, people, grant_ttl=ttl, session_ttl=ttl, **extra), people, root / "weir.db")


class Store:
    """workflow_runs / workflow_events for ONE tenant, over a connection of the unprivileged application role with the tenant set (row-level security applies)."""
    def __init__(self, env):
        self.tenant = env.tenant_id
        self.con = psycopg.connect(SV.app_dsn(env.dsn), autocommit=True)
        self.con.execute(f'SET search_path TO "{env.schema}", pg_catalog, public')
        self.con.execute("SELECT set_config('app.tenant_id', %s, false)", (env.tenant_id,))

    def close(self):
        self.con.close()

    def start(self, corr, requester, role, lead_id, idem):
        r = self.con.execute("INSERT INTO workflow_runs (tenant_id,id,workflow,requester,role,lead_id,idem_key,state) VALUES (%s,%s,%s,%s,%s,%s,%s,'STARTED') ON CONFLICT (tenant_id, idem_key) DO NOTHING RETURNING id",
                             (self.tenant, corr, WORKFLOW, requester, role, lead_id, idem)).fetchone()
        if r:
            return corr, False
        return self.con.execute("SELECT id FROM workflow_runs WHERE tenant_id=%s AND idem_key=%s", (self.tenant, idem)).fetchone()[0], True

    def run(self, corr):
        r = self.con.execute("SELECT id, requester, role, lead_id, state, proposal, proposal_hash, lead_version, approval_id, failure, result, version FROM workflow_runs WHERE tenant_id=%s AND id=%s", (self.tenant, corr)).fetchone()
        return None if not r else dict(zip(("id", "requester", "role", "lead_id", "state", "proposal", "proposal_hash", "lead_version", "approval_id", "failure", "result", "version"), r))

    def set(self, corr, state, **f):
        cols, vals = ["state=%s"], [state]
        for k, v in f.items():
            cols.append(f"{k}=%s"); vals.append(Jsonb(v) if k in ("proposal", "result") and v is not None else v)
        self.con.execute(f"UPDATE workflow_runs SET {', '.join(cols)} WHERE tenant_id=%s AND id=%s", (*vals, self.tenant, corr))

    def event(self, corr, kind, **detail):
        with self.con.transaction():
            n = self.con.execute("SELECT coalesce(max(seq),0)+1 FROM workflow_events WHERE tenant_id=%s AND run_id=%s", (self.tenant, corr)).fetchone()[0]
            self.con.execute("INSERT INTO workflow_events (tenant_id,run_id,seq,kind,detail) VALUES (%s,%s,%s,%s,%s)", (self.tenant, corr, n, kind, Jsonb(json.loads(json.dumps(detail, default=str)))))

    def events(self, corr):
        return [dict(seq=r[0], ts=r[1].isoformat(), kind=r[2], **r[3]) for r in self.con.execute("SELECT seq, ts, kind, detail FROM workflow_events WHERE tenant_id=%s AND run_id=%s ORDER BY seq", (self.tenant, corr))]

    def list_runs(self, limit=50, offset=0):
        return self.con.execute("SELECT id, lead_id, state, requester, failure, created_at FROM workflow_runs WHERE tenant_id=%s ORDER BY created_at DESC, id LIMIT %s OFFSET %s", (self.tenant, limit, offset)).fetchall()


class GovernedLeadQualification:
    def __init__(self, env, clock=time.time, ttl=900, fault=None, crm_fault=None, tool_timeout=TOOL_TIMEOUT_S):
        self.env, self.clock, self.ttl, self.fault, self.crm_fault, self.tool_timeout = env, clock, ttl, fault, crm_fault, tool_timeout
        self.store = Store(env)
        self.weir = WeirStore(str(env.weir_db), clock)
        self.loop = asyncio.new_event_loop()
        self._gw, self._svc = {}, {}

    def close(self):
        for s in self._svc.values():
            s.close()
        self.store.close(); self.loop.close()

    # ---------------------------------------------------------------- infrastructure
    def _service(self, identity):
        if identity.id not in self._svc:
            self._svc[identity.id] = SV.GrowthService(self.env.dsn, self.env.schema, self.env.tenant_id, identity.id)
        return self._svc[identity.id]

    def _gateway(self, identity):
        key = (identity.role, identity.id)
        if key not in self._gw:
            svc = self._service(identity)
            ups = {}
            crm = None
            if identity.role in WG.READ_ROLES:
                ups["growth"] = WG.GrowthReadUpstream(svc, self.fault)
            if identity.role in WG.INITIATE_ROLES:
                crm = WG.CrmUpstream(svc, self.store, self.crm_fault); ups["crm"] = crm
            gw = Gateway(parse_policy(WG.policy_for(identity.role, self.ttl)), self.weir, ups, clock=self.clock)
            self.loop.run_until_complete(gw.start())
            self._gw[key] = (gw, crm)
        return self._gw[key]

    def _call(self, gw, sess, tool, args, corr, stage):
        t0 = time.perf_counter()
        try:
            out = self.loop.run_until_complete(asyncio.wait_for(gw.call_tool_detailed(sess, tool, args), self.tool_timeout))
        except asyncio.TimeoutError:
            self.store.event(corr, "tool_call", stage=stage, tool=tool, failure="TOOL_TIMEOUT")
            return None, None, "TOOL_TIMEOUT"
        except psycopg.Error as e:
            self.store.event(corr, "tool_call", stage=stage, tool=tool, failure="DB_ERROR", detail=type(e).__name__)
            return None, None, "DB_ERROR"
        ms = round((time.perf_counter() - t0) * 1000, 2)
        base = dict(stage=stage, tool=tool, forwarded=out.forwarded, call_hash=call_hash(tool, args)[:16], codes=out.codes, approval_id=out.approval_id, ms=ms)
        if not out.forwarded:
            self.store.event(corr, "tool_call", failure="TOOL_DENIED" if not out.approval_id else None, held_for_approval=bool(out.approval_id), **base)
            return out, None, ("TOOL_DENIED" if not out.approval_id else None)
        try:
            text = out.result["content"][0]["text"]
            if out.result.get("isError"):
                try:
                    parsed = json.loads(text)
                except ValueError:
                    parsed = {"error": text[:160]}
                self.store.event(corr, "tool_call", failure="TOOL_ERROR", error=str(parsed.get("error", parsed))[:160] if isinstance(parsed, dict) else "error", **base)
                return out, (parsed if isinstance(parsed, dict) else {"error": "error"}), "TOOL_ERROR"
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValueError("not an object")
        except (KeyError, IndexError, TypeError, ValueError):
            self.store.event(corr, "tool_call", failure="TOOL_BAD_RESPONSE", **base)
            return out, None, "TOOL_BAD_RESPONSE"
        self.store.event(corr, "tool_call", ok=True, **base)
        return out, parsed, None

    def _result(self, corr, status, **kw):
        run = self.store.run(corr) or {}
        n = self.store.con.execute("SELECT count(*) FROM leads WHERE tenant_id=%s AND qualified_by_run=%s", (self.env.tenant_id, corr)).fetchone()[0]
        return dict(corr_id=corr, tenant=self.env.tenant_id, workflow=WORKFLOW, status=status, state=run.get("state"), lead_id=run.get("lead_id"), side_effects=dict(crm_updates=n, emails_sent=0, external_contacts=0), **kw)

    def _fail(self, corr, cls, status="BLOCKED", state="BLOCKED", detail="", **kw):
        assert cls in FAILURES, cls
        self.store.event(corr, "failure", failure_class=cls, detail=str(detail)[:200])
        if self.store.run(corr) and self.store.run(corr)["state"] not in ("EXECUTED", "REJECTED"):
            self.store.set(corr, state, failure=f"{cls}:{str(detail)[:80]}")
        return self._result(corr, status, failure=cls, detail=str(detail)[:200], **kw)

    def _identify(self, session):
        return self.env.authority.identify(session)

    def login(self, user, passcode):
        return self.env.authority.login(user, passcode)

    @staticmethod
    def _hash(proposal):
        return hashlib.sha256(json.dumps(proposal, sort_keys=True, default=str).encode()).hexdigest()

    def _args(self, run):
        p = run["proposal"]
        return dict(proposal_id=run["id"], lead_id=p["lead_id"], status=p["proposed_status"], score=p["score"], expected_lead_version=p["expected_lead_version"], evidence_hash=run["proposal_hash"],
                    note=f"Apply qualification {p['proposed_status']} (score {p['score']}) to lead {p['lead_id']}")

    # ---------------------------------------------------------------- the run (G01-G07)
    def run(self, session, lead_id, idempotency_key=None, request_id=None):
        corr = "wf-" + uuid.uuid4().hex[:12]
        idem = idempotency_key or f"auto-{corr}"
        try:
            who = self._identify(session)
        except ID.AuthError as e:
            return self._anon_denied(corr, lead_id, e.code)
        svc = self._service(who)
        if svc.role != who.role:                                                    # the session's role must match the tenant's own user record
            return self._anon_denied(corr, lead_id, "ROLE_MISMATCH")
        lead_ok = svc.con.execute("SELECT 1 FROM leads WHERE tenant_id=%s AND id=%s", (self.env.tenant_id, lead_id)).fetchone()
        if not lead_ok:
            return self._anon_denied(corr, lead_id, "NO_SUCH_LEAD", who=who)           # also the answer for another tenant's lead id
        first, dup = self.store.start(corr, who.id, who.role, lead_id, idem)
        if dup:
            self.store.event(first, "failure", failure_class="DUPLICATE_REQUEST", request=request_id)
            return self._result(first, "DUPLICATE", failure="DUPLICATE_REQUEST", duplicate_of=first)
        self.store.event(corr, "stage", stage="G01", name="request_received", tenant=self.env.tenant_id, lead_id=lead_id, request_id=request_id, idempotency_key=bool(idempotency_key))
        self.store.event(corr, "auth", decision="allow", user=who.id, role=who.role, tenant=self.env.tenant_id)
        if who.role not in WG.READ_ROLES | WG.INITIATE_ROLES:
            return self._fail(corr, "ROLE_DENIED", status="DENIED", detail=who.role)
        gw, crm = self._gateway(who)
        sess = gw.open_session(corr)
        out, parsed, fail = self._call(gw, sess, WG.READ_TOOL, dict(lead_id=lead_id), corr, "G03")
        if fail:
            return self._fail(corr, fail, state="FAILED" if fail != "TOOL_DENIED" else "BLOCKED", detail="could not read the lead context")
        rows = parsed.get("rows") or []
        if not rows:
            return self._fail(corr, "NO_SUCH_LEAD", detail=lead_id)
        ctx = rows[0]
        self.store.event(corr, "stage", stage="G03", name="evidence_collected", evidence=dict(source=ctx["source"], consent_status=ctx["consent_status"], suppressed=ctx["suppressed"], lead_version=ctx["lead_version"], has_signals=ctx["signals"] is not None))
        # G04: source and consent validation
        if not str(ctx["source"]).startswith(Q.ALLOWED_SOURCE_PREFIX):
            return self._fail(corr, "INVALID_SOURCE", detail=ctx["source"])
        if ctx["suppressed"] or ctx["consent_status"] == "opt_out":
            return self._fail(corr, "SUPPRESSED_CONTACT", detail="contact is suppressed or opted out; no qualification is proposed")
        self.store.event(corr, "stage", stage="G04", name="source_and_consent_validated", consent_status=ctx["consent_status"], outreach_allowed=(ctx["consent_status"] == "opt_in"))
        # G05: evaluation + validation gate
        try:
            rec = Q.recommend(ctx)
        except Q.InvalidEvidence as e:
            self.store.set(corr, "ABSTAINED", failure=f"INVALID_EVIDENCE:{'; '.join(e.problems)[:100]}")
            self.store.event(corr, "failure", failure_class="INVALID_EVIDENCE", problems=e.problems)
            return self._result(corr, "ABSTAINED", failure="INVALID_EVIDENCE", problems=e.problems)
        problems = Q.validate_recommendation(rec, ctx)
        if problems:
            return self._fail(corr, "VALIDATION_FAILED", state="FAILED", detail=problems[0])
        self.store.set(corr, "EVIDENCE_COLLECTED", lead_version=ctx["lead_version"])
        self.store.event(corr, "stage", stage="G05", name="recommendation", proposed_status=rec["proposed_status"], score=rec["score"], reasons=rec["reasons"], notice=rec["notice"])
        # G06: proposal
        h = self._hash(rec)
        self.store.set(corr, "PROPOSED", proposal=rec, proposal_hash=h)
        self.store.event(corr, "stage", stage="G06", name="proposal", proposal_hash=h[:16])
        # G07: THE WEIR evaluates the write; it is held for approval (or denied by policy)
        out_w, _, fail = self._call(gw, sess, WG.CRM_TOOL, self._args(self.store.run(corr)), corr, "G07")
        if out_w is None:
            return self._fail(corr, fail or "TOOL_ERROR", state="FAILED")
        if out_w.forwarded:
            return self._fail(corr, "TOOL_ERROR", state="FAILED", detail="write forwarded without approval")
        if not out_w.approval_id:
            self.store.event(corr, "stage", stage="G07", name="weir_denied", codes=out_w.codes)
            return self._fail(corr, "TOOL_DENIED", detail=",".join(out_w.codes) or "denied by policy", recommendation=rec)
        self.store.set(corr, "AWAITING_APPROVAL", approval_id=out_w.approval_id)
        self.store.event(corr, "stage", stage="G07", name="held_for_approval", approval_id=out_w.approval_id, codes=out_w.codes, ttl_s=self.ttl)
        return self._result(corr, "AWAITING_APPROVAL", approval_id=out_w.approval_id, recommendation=rec)

    def _anon_denied(self, corr, lead_id, code, who=None):
        # no run row can exist without a valid lead in this tenant, so the denial is returned (and logged by the caller's transport) without a workflow row
        return dict(corr_id=corr, tenant=self.env.tenant_id, workflow=WORKFLOW, status="DENIED", state=None, lead_id=None, failure="AUTH_DENIED" if code != "NO_SUCH_LEAD" else "NO_SUCH_LEAD", detail=code,
                    side_effects=dict(crm_updates=0, emails_sent=0, external_contacts=0))

    # ---------------------------------------------------------------- the human decision (G08) and execution (G09)
    def decide(self, corr_id, session, approve=True, comment="", execute=True, request_id=None):
        run = self.store.run(corr_id)
        if run is None:
            return dict(corr_id=corr_id, tenant=self.env.tenant_id, status="DENIED", failure="NOT_AWAITING_APPROVAL", detail="no such run in this tenant", side_effects=dict(crm_updates=0, emails_sent=0, external_contacts=0))
        try:
            who = self._identify(session)
        except ID.AuthError as e:
            self.store.event(corr_id, "approval_decision", decision="deny", code=e.code)
            return self._fail(corr_id, "AUTH_DENIED", status="DENIED", state=run["state"], detail=e.code)
        if not ID.Authority.role_allowed(who.role, "apply_lead_qualification", {}):
            self.store.event(corr_id, "approval_decision", decision="deny", code="ROLE_NOT_PERMITTED", user=who.id, role=who.role)
            return self._fail(corr_id, "ROLE_DENIED", status="DENIED", state=run["state"], detail=f"{who.role} may not approve")
        if who.id == run["requester"]:
            self.store.event(corr_id, "approval_decision", decision="deny", code="MAKER_CHECKER", user=who.id)
            return self._fail(corr_id, "MAKER_CHECKER", status="DENIED", state=run["state"], detail="requester may not approve their own request")
        if run["state"] != "AWAITING_APPROVAL":
            cls = "APPROVAL_REPLAY" if run["state"] in ("EXECUTED", "APPROVED") else "NOT_AWAITING_APPROVAL"
            self.store.event(corr_id, "approval_decision", decision="deny", code=cls, state=run["state"])
            return self._result(corr_id, "DENIED", failure=cls, detail=run["state"])
        aid = run["approval_id"]
        ap = self.weir.get_approval(aid) if aid else None
        if ap is None or ap.session_id != corr_id or ap.tool != WG.CRM_TOOL:
            return self._fail(corr_id, "APPROVAL_MISMATCH", status="DENIED", state=run["state"], detail="approval does not belong to this run")
        if not approve:
            self.weir.resolve_approval(aid, False, by=who.id)
            self.store.set(corr_id, "REJECTED", failure=f"rejected: {comment[:60]}")
            self.store.event(corr_id, "approval_decision", decision="reject", by=who.id, comment=comment[:120])
            return self._result(corr_id, "REJECTED")
        state = self.weir.resolve_approval(aid, True, by=who.id)
        self.store.event(corr_id, "approval_decision", decision="approve" if state == "approved" else state, by=who.id, role=who.role, approval_id=aid, comment=comment[:120])
        if state == "expired":
            return self._fail(corr_id, "APPROVAL_EXPIRED", status="EXPIRED", state="FAILED", detail="approval expired before it was granted")
        if state != "approved":
            return self._fail(corr_id, "APPROVAL_REPLAY" if state.startswith("already") else "APPROVAL_MISMATCH", status="DENIED", state=run["state"], detail=state)
        self.store.set(corr_id, "APPROVED")
        if not execute:
            return self._result(corr_id, "APPROVED_NOT_EXECUTED", approval_id=aid)
        return self.execute_approved(corr_id, approver=who)

    def execute_approved(self, corr_id, approver=None):
        """Re-issue the identical call; THE WEIR forwards it only if an unexpired, unconsumed approval for exactly this call hash exists for this session."""
        run = self.store.run(corr_id)
        if run is None or run["state"] != "APPROVED":
            return self._result(corr_id, "DENIED", failure="NOT_AWAITING_APPROVAL", detail=(run or {}).get("state"))
        ident = ID.Identity(run["requester"], run["role"])
        gw, crm = self._gateway(ident)
        sess = gw.open_session(corr_id)
        args = self._args(run)
        approver_id = approver.id if approver else (self.weir.get_approval(run["approval_id"]).resolved_by or "unknown")
        crm.context = dict(approval_id=run["approval_id"], approved_by=approver_id, corr_id=corr_id)
        out, parsed, fail = self._call(gw, sess, WG.CRM_TOOL, args, corr_id, "G09")
        crm.context = None
        if out is not None and not out.forwarded:
            self.store.set(corr_id, "AWAITING_APPROVAL", approval_id=out.approval_id, failure="REAPPROVAL_REQUIRED:approved call no longer matches")
            self.store.event(corr_id, "failure", failure_class="REAPPROVAL_REQUIRED", new_approval=out.approval_id, codes=out.codes)
            return self._result(corr_id, "REAPPROVAL_REQUIRED", failure="REAPPROVAL_REQUIRED", approval_id=out.approval_id)
        err = (parsed or {}).get("error", "") if isinstance(parsed, dict) else ""
        known = {"STALE_PROPOSAL", "SUPPRESSED_CONTACT", "VALIDATION_FAILED", "PROPOSAL_MISMATCH", "BLOCKED", "DENIED", "NO_SUCH_LEAD", "NO_SUCH_PROPOSAL", "PROPOSAL_NOT_OPEN", "NO_APPROVAL_CONTEXT", "MISSING_ARGUMENT"}
        if fail in ("TOOL_TIMEOUT", "DB_ERROR", "TOOL_BAD_RESPONSE") or (fail == "TOOL_ERROR" and err not in known):
            if self._service(ident).qualified_by(run["lead_id"]) == corr_id:                  # the write happened but the response was lost: reconcile against the CRM, never guess
                self.store.event(corr_id, "recovery", action="reconciled_existing_update", after=fail)
                self.store.set(corr_id, "EXECUTED")
                return self._result(corr_id, "EXECUTED", recovered_from=fail)
            return self._fail(corr_id, fail, status="FAILED", state="FAILED", detail="CRM update not applied; the approval was consumed: recovery requires re-approval")
        if fail:
            err = (parsed or {}).get("error", "") if isinstance(parsed, dict) else ""
            cls = {"STALE_PROPOSAL": "STALE_PROPOSAL", "SUPPRESSED_CONTACT": "SUPPRESSED_CONTACT", "VALIDATION_FAILED": "VALIDATION_FAILED", "PROPOSAL_MISMATCH": "VALIDATION_FAILED"}.get(err, fail)
            return self._fail(corr_id, cls, status="FAILED", state="FAILED", detail=err or fail)
        self.store.set(corr_id, "EXECUTED", result=dict(applied=True, status=parsed.get("status")))
        self.store.event(corr_id, "stage", stage="G09", name="crm_updated", lead_status=parsed.get("status"))
        self.store.event(corr_id, "stage", stage="G10", name="no_external_contact", emails_sent=0, external_contacts=0)
        return self._result(corr_id, "EXECUTED", lead_status=parsed.get("status"))

    def status(self, corr_id):
        r = self.store.run(corr_id)
        return None if r is None else dict(r, events=self.store.events(corr_id))

    def trace(self, corr_id):
        return self.store.events(corr_id)
