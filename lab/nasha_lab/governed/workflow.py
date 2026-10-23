"""Governed procurement workflow: inventory discrepancy -> evidence -> AI proposal -> THE WEIR -> human approval -> audited DRAFT purchase order (D-89).

Every stage is traced under ONE correlation id (the run id) plus the caller's request id. The workflow is a small persistent state machine (ledger.runs) so an interrupted run can be
recovered, a retried request is idempotent, and every failure is classified. Nothing is ever transmitted: the ledger cannot represent a sent order, and tests run with the network
blocked. SYNTHETIC data only.

Stages: S01 request/identity . S02 tenant dataset provenance . S03 recipes->consumption . S04 inventory movement . S05 discrepancy detected . S06 quantified . S07 forecast
        S08 retrieval (via THE WEIR) . S09 explanation . S10 proposal . S11 WEIR authorisation . S12 held for approval . S13 human decision . S14 draft PO . S15 audit . S16 no transmission
(S01-S07 are produced by the warehouse scenario; this module records which tables and run produced them and re-reads them as evidence.)
"""
import asyncio
import json
import sqlite3
import time
import uuid

from mcp_weir.gateway import Gateway
from mcp_weir.policy import parse_policy
from mcp_weir.store import Store as WeirStore

from .. import identity as ID
from ..trace import Store as TraceStore
from ..warehouse.ops_ai import OpsAI, Principal
from ..warehouse.ops_ai_weir import call_hash
from . import agent as AG, weir_bridge as WB
from .ledger import Ledger

FAILURES = ("AUTH_DENIED", "ROLE_DENIED", "RATE_LIMITED", "TOOL_TIMEOUT", "TOOL_BAD_RESPONSE", "TOOL_ERROR", "TOOL_DENIED", "DB_ERROR", "MODEL_UNAVAILABLE", "MALFORMED_AGENT_OUTPUT",
            "VALIDATION_FAILED", "INJECTION_SUSPECTED", "APPROVAL_EXPIRED", "APPROVAL_REPLAY", "APPROVAL_MISMATCH", "NOT_AWAITING_APPROVAL", "MAKER_CHECKER", "STALE_PROPOSAL",
            "SUPPLIER_DATA_MISSING", "UNSAFE_PROPOSAL", "DUPLICATE_REQUEST", "REAPPROVAL_REQUIRED", "NO_EVIDENCE", "CONTRADICTORY_EVIDENCE")
TOOL_TIMEOUT_S = 5.0
SECRET_KEYS = ("passcode", "secret", "token", "password", "session")


def redact(obj):
    if isinstance(obj, dict):
        return {k: ("***" if any(w in k.lower() for w in SECRET_KEYS) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


class RateLimiter:
    def __init__(self, limit, window, clock):
        self.limit, self.window, self.clock, self.hits = limit, window, clock, {}

    def allow(self, key):
        now = self.clock()
        q = [t for t in self.hits.get(key, []) if now - t < self.window]
        if len(q) >= self.limit:
            self.hits[key] = q
            return False
        q.append(now)
        self.hits[key] = q
        return True


class GovernedProcurement:
    def __init__(self, env, planner=None, clock=time.time, policy_kb=None, ttl=900, fault=None, warehouse_wrapper=None, tool_timeout=TOOL_TIMEOUT_S, rate_limit=None):
        self.env, self.clock, self.ttl, self.fault, self.warehouse_wrapper, self.tool_timeout = env, clock, ttl, fault, warehouse_wrapper, tool_timeout
        self.planner = planner or AG.RulePlanner()
        self.policy_kb = policy_kb
        self.ledger = Ledger(env.ledger_path, env.tenant_id, clock)
        self.trace = TraceStore(str(env.trace_db))
        self.weir = WeirStore(str(env.weir_db), clock)
        self.memory, self.knowledge = env.memory(), env.knowledge()
        self.loop = asyncio.new_event_loop()
        self._gw = {}
        self.limiter = RateLimiter(*rate_limit, clock) if rate_limit else None

    def close(self):
        for gw, _, ops in self._gw.values():
            ops.close()
        self.ledger.close()
        self.loop.close()

    # ------------------------------------------------------------------ infrastructure
    def _gateway(self, identity):
        """One gateway per (role, user): its Ops AI principal is the requester, so the warehouse's own role gate also applies."""
        key = (identity.role, identity.id)
        if key not in self._gw:
            ops = OpsAI(self.env.warehouse, self.env.root / f"ops-{identity.id}.audit.db")
            who = WB.ops_principal(identity)
            ups, proc = WB.make_upstreams(self.env, ops, who, self.ledger, identity.role, self.fault, self.warehouse_wrapper)
            gw = Gateway(parse_policy(WB.policy_for(identity.role, self.ttl)), self.weir, ups, clock=self.clock)
            self.loop.run_until_complete(gw.start())
            self._gw[key] = (gw, proc, ops)
        return self._gw[key]

    def _tr(self, corr):
        return self.trace.trace(corr, getattr(self, "_req", ""))

    def _call(self, gw, sess, tool, args, corr, stage):
        """One WEIR-mediated tool call with timeout, response validation and a full trace record. Returns (outcome|None, parsed|None, failure|None)."""
        t0 = time.perf_counter()
        tr = self._tr(corr)
        try:
            out = self.loop.run_until_complete(asyncio.wait_for(gw.call_tool_detailed(sess, tool, args), self.tool_timeout))
        except asyncio.TimeoutError:
            tr.event("tool_call", stage=stage, tool=tool, args=redact(args), failure="TOOL_TIMEOUT", ms=round((time.perf_counter() - t0) * 1000, 2))
            return None, None, "TOOL_TIMEOUT"
        except sqlite3.Error as e:
            tr.event("tool_call", stage=stage, tool=tool, failure="DB_ERROR", detail=type(e).__name__, ms=round((time.perf_counter() - t0) * 1000, 2))
            return None, None, "DB_ERROR"
        ms = round((time.perf_counter() - t0) * 1000, 2)
        base = dict(stage=stage, tool=tool, args=redact(args), forwarded=out.forwarded, call_hash=call_hash(tool, args)[:16], weir_call=out.call_id, codes=out.codes, approval_id=out.approval_id, ms=ms)
        if not out.forwarded:
            tr.event("tool_call", failure="TOOL_DENIED" if not out.approval_id else None, held_for_approval=bool(out.approval_id), **base)
            return out, None, ("TOOL_DENIED" if not out.approval_id else None)
        try:
            text = out.result["content"][0]["text"]
            if out.result.get("isError"):                       # an error result (including the gateway's own "upstream raised" text) is a TOOL_ERROR, whatever its body
                try:
                    parsed = json.loads(text)
                except ValueError:
                    parsed = {"error": text[:160]}
                tr.event("tool_call", failure="TOOL_ERROR", error=str(parsed.get("error", parsed))[:160] if isinstance(parsed, dict) else "error", **base)
                return out, (parsed if isinstance(parsed, dict) else {"error": "error"}), "TOOL_ERROR"
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise ValueError("not an object")
        except (KeyError, IndexError, TypeError, ValueError):
            tr.event("tool_call", failure="TOOL_BAD_RESPONSE", **base)
            return out, None, "TOOL_BAD_RESPONSE"
        tr.event("tool_call", ok=True, **base)
        return out, parsed, None

    def _runner(self, gw, sess, corr):
        def run(tool, args):
            out, parsed, fail = self._call(gw, sess, f"warehouse__{tool}", args, corr, "S08")
            if fail:
                return dict(ok=False, code=fail)
            if "rows" not in parsed:
                self._tr(corr).event("tool_call", stage="S08", tool=tool, failure="TOOL_BAD_RESPONSE", detail="no rows key")
                return dict(ok=False, code="TOOL_BAD_RESPONSE")
            return dict(ok=True, rows=parsed["rows"], provenance=parsed.get("provenance", {}))
        return run

    def _side_effects(self, corr=None):
        n = len(self.ledger.po_drafts())
        return dict(purchase_orders_created=n, external_transmissions=0)

    def _result(self, corr, status, **kw):
        run = self.ledger.run(corr) or {}
        return dict(corr_id=corr, tenant=self.env.tenant_id, status=status, state=run.get("state"), side_effects=self._side_effects(), **kw)

    def _fail(self, corr, cls, status="BLOCKED", state="BLOCKED", detail="", actor="system", role=None, **kw):
        assert cls in FAILURES, cls
        self._tr(corr).event("failure", failure_class=cls, detail=str(detail)[:200])
        if self.ledger.run(corr):
            self.ledger.set_state(corr, state, actor, role, failure=f"{cls}:{str(detail)[:80]}")
        else:
            self.ledger.audit(actor, role, f"failure:{cls}", corr, "", str(detail)[:120])
        return self._result(corr, status, failure=cls, detail=str(detail)[:200], **kw)

    # ------------------------------------------------------------------ authentication helpers
    def login(self, user, passcode):
        return self.env.authority.login(user, passcode)

    # ------------------------------------------------------------------ the run (S01-S12)
    def run(self, session, location_id, ingredient_id=None, idempotency_key=None, request_id=None, planner=None):
        self._req = request_id or "req-" + uuid.uuid4().hex[:8]
        corr = self.trace.create_run(idempotency_key or "", self._req)
        tr = self._tr(corr)
        tr.event("stage", stage="S01", name="request_received", tenant=self.env.tenant_id, location_id=location_id, ingredient_id=ingredient_id, idempotency_key=bool(idempotency_key))
        try:
            who = self.env.authority.identify(session)
        except ID.AuthError as e:
            tr.event("auth", decision="deny", code=e.code)
            self.trace.set_status(corr, "COMPLETED", "AUTH_DENIED", True)
            return self._fail(corr, "AUTH_DENIED", status="DENIED", detail=e.code, actor="anonymous")
        tr.event("auth", decision="allow", user=who.id, role=who.role, tenant=self.env.tenant_id)
        if who.role not in WB.INITIATE_ROLES:
            self.trace.set_status(corr, "COMPLETED", "ROLE_DENIED", True)
            return self._fail(corr, "ROLE_DENIED", status="DENIED", detail=who.role, actor=who.id, role=who.role)
        if self.limiter and not self.limiter.allow((self.env.tenant_id, who.id)):
            self.trace.set_status(corr, "COMPLETED", "RATE_LIMITED", True)
            return self._fail(corr, "RATE_LIMITED", status="DENIED", detail="too many requests", actor=who.id, role=who.role)
        first, dup = self.ledger.start_run(corr, who.id, who.role, location_id, ingredient_id, idempotency_key)
        if dup:
            tr.event("failure", failure_class="DUPLICATE_REQUEST", original=first)
            self.trace.set_status(corr, "COMPLETED", "DUPLICATE_REQUEST", True)
            r = self._result(first, "DUPLICATE", failure="DUPLICATE_REQUEST", duplicate_of=first)
            return r
        gw, proc, ops = self._gateway(who)
        sess = gw.open_session(corr)
        scn = sqlite3.connect(f"file:{self.env.warehouse}?mode=ro", uri=True)
        try:
            meta = scn.execute("SELECT scenario_id, pricing_config FROM scn_scenario_run").fetchone()
        finally:
            scn.close()
        tr.event("stage", stage="S02", name="dataset_provenance", scenario=meta[0], pricing_config=meta[1], warehouse=self.env.warehouse.name, synthetic=True)
        for stg, name, src in (("S03", "recipes_to_consumption", "scn_recipe_bom,scn_depletion_week"), ("S04", "inventory_movement", "scn_inventory_week"), ("S05", "discrepancy_detected", "scn_variance_week,scn_variance_flag"),
                               ("S06", "discrepancy_quantified", "scn_variance_week"), ("S07", "demand_forecast", "scn_demand_forecast,scn_forecast_backtest")):
            tr.event("stage", stage=stg, name=name, source_tables=src)
        # S08 retrieval through THE WEIR
        try:
            book, ing, target = AG.collect_evidence(self._runner(gw, sess, corr), self.knowledge, self.memory, location_id, ingredient_id, self.policy_kb)
        except Exception as e:                                          # noqa: BLE001  (an unexpected collector failure must fail safe, never half-run)
            return self._fail(corr, "TOOL_ERROR", state="FAILED", detail=f"{type(e).__name__}", actor=who.id, role=who.role)
        tr.event("stage", stage="S08", name="retrieval_complete", evidence=[dict(id=e.id, ok=e.ok, trust=e.trust, injection=e.injection_suspected, provenance=e.provenance) for e in book.items.values()], gaps=book.gaps)
        inj = [e.id for e in book.items.values() if e.injection_suspected]
        if inj:
            tr.event("injection_flagged", evidence=inj)
        tools_failed = [g for g in book.gaps if g["code"] in ("TOOL_TIMEOUT", "DB_ERROR", "TOOL_BAD_RESPONSE", "TOOL_ERROR", "TOOL_DENIED")]
        if not any(e.usable() for e in book.items.values() if e.tool == "variance_flags"):
            cls = tools_failed[0]["code"] if tools_failed else "NO_EVIDENCE"
            self.ledger.set_state(corr, "ABSTAINED", who.id, who.role, failure=f"{cls}:no usable discrepancy evidence")
            self.trace.set_status(corr, "COMPLETED", "ABSTAINED", True)
            tr.event("failure", failure_class=cls, detail="no usable variance evidence")
            return self._result(corr, "ABSTAINED", failure=cls, evidence_gaps=book.gaps)
        self.ledger.set_state(corr, "EVIDENCE_COLLECTED", who.id, who.role)
        # S09/S10 explanation and proposal
        ctx = dict(location_id=location_id, ingredient_id=ing, tenant=self.env.tenant_id)
        pl = planner or self.planner
        raw = pl.decide(book, ctx)
        out, val = AG.validate_output(raw, book, ctx)
        tr.event("stage", stage="S09", name="explanation", planner=getattr(pl, "name", "?"), planner_version=getattr(pl, "version", ""), claims_kept=val.claims_kept, claims_dropped=val.claims_dropped, violations=val.violations,
                 raw_action=raw.get("action"), final_action=out["action"], summary=out["summary"][:300], claims=[dict(text=c["text"], evidence=c["evidence"]) for c in out["claims"]])
        if val.violations:
            tr.event("validation", violations=val.violations)
        if getattr(pl, "failure", None):
            tr.event("failure", failure_class=pl.failure.split(":")[0], detail=pl.failure)
        if out["action"] != "PROPOSE_REORDER":
            cls = self._classify_abstain(out, val, pl)
            self.ledger.set_state(corr, "ABSTAINED", who.id, who.role, failure=f"{cls}:{out.get('abstain_reason') or ''}"[:120])
            self.trace.set_status(corr, "COMPLETED", "ABSTAINED", True)
            self.memory.remember(corr, f"{location_id}/{ing}", f"abstained: {out.get('abstain_reason')}", self.clock())
            return self._result(corr, "ABSTAINED", failure=cls, explanation=out, validation=val.violations)
        prop = out["proposal"]
        pid = self.ledger.add_proposal(corr, prop, out, [e.id for e in book.items.values() if e.usable()], who.id, who.role)
        self.ledger.set_state(corr, "PROPOSED", who.id, who.role, proposal_id=pid)
        tr.event("stage", stage="S10", name="proposal", proposal_id=pid, ingredient=prop["ingredient_id"], qty=prop["qty"], supplier=prop["supplier_id"], est_cost_usd=prop["est_cost_usd"], price_class=prop["price_class"])
        # S11/S12 THE WEIR evaluates the write call; it is held for approval
        args = self._po_args(pid)
        out_w, parsed, fail = self._call(gw, sess, WB.PROC_TOOL, args, corr, "S11")
        if out_w is None:
            return self._fail(corr, fail or "TOOL_ERROR", state="FAILED", actor=who.id, role=who.role, proposal_id=pid)
        if out_w.forwarded:                                             # must not happen: a write without approval
            return self._fail(corr, "TOOL_ERROR", state="FAILED", detail="write forwarded without approval", actor=who.id, role=who.role, proposal_id=pid)
        if not out_w.approval_id:
            self.ledger.set_proposal_state(pid, "REJECTED", "weir", None, corr)
            self.trace.set_status(corr, "COMPLETED", "BLOCKED_BY_WEIR", True)
            tr.event("stage", stage="S11", name="weir_denied", codes=out_w.codes)
            return self._fail(corr, "TOOL_DENIED", detail=",".join(out_w.codes) or "denied by policy", actor=who.id, role=who.role, proposal_id=pid, explanation=out)
        self.ledger.set_state(corr, "AWAITING_APPROVAL", who.id, who.role, approval_id=out_w.approval_id)
        tr.event("stage", stage="S12", name="held_for_approval", approval_id=out_w.approval_id, codes=out_w.codes, ttl_s=self.ttl)
        self.memory.remember(corr, f"{location_id}/{ing}", f"proposed {prop['qty']} {prop['unit']} from {prop['supplier_id']} (awaiting approval)", self.clock())
        return self._result(corr, "AWAITING_APPROVAL", approval_id=out_w.approval_id, proposal_id=pid, explanation=out)

    @staticmethod
    def _classify_abstain(out, val, pl):
        r = out.get("abstain_reason") or ""
        for pref, cls in (("MALFORMED_AGENT_OUTPUT", "MALFORMED_AGENT_OUTPUT"), ("MODEL_UNAVAILABLE", "MODEL_UNAVAILABLE"), ("UNSAFE", "UNSAFE_PROPOSAL"), ("MISSING_EVIDENCE", "NO_EVIDENCE"), ("SUPPLIER_DATA_MISSING", "SUPPLIER_DATA_MISSING"),
                          ("PROPOSAL_MISMATCH", "VALIDATION_FAILED"), ("PROPOSAL_NOT_IN", "VALIDATION_FAILED"), ("INSTRUCTION", "INJECTION_SUSPECTED"), ("CONTRADICTORY", "CONTRADICTORY_EVIDENCE"), ("NO_", "NO_EVIDENCE")):
            if r.startswith(pref):
                return cls
        return "VALIDATION_FAILED" if val.violations else "NO_EVIDENCE"

    def _po_args(self, proposal_id):
        p = self.ledger.proposal(proposal_id)
        return dict(proposal_id=p["proposal_id"], reco_id=p["reco_id"], inputs_hash=p["inputs_hash"], qty=p["qty"], est_cost_usd=p["est_cost_usd"], supplier_id=p["supplier_id"], quote_id=p["quote_id"],
                    idempotency_key=f"po-{self.env.tenant_id}-{p['proposal_id']}", note=f"Draft PO for {p['ingredient_id']} at {p['location_id']} (proposal {p['proposal_id']})")

    # ------------------------------------------------------------------ the human decision (S13) and execution (S14)
    def decide(self, corr_id, session, approve=True, comment="", execute=True, request_id=None):
        self._req = request_id or "req-" + uuid.uuid4().hex[:8]
        tr = self._tr(corr_id)
        run = self.ledger.run(corr_id)
        if run is None:                                                  # also the answer for another tenant's corr id: this tenant's ledger has no such run
            return dict(corr_id=corr_id, tenant=self.env.tenant_id, status="DENIED", failure="NOT_AWAITING_APPROVAL", detail="no such run in this tenant", side_effects=self._side_effects())
        try:
            who = self.env.authority.identify(session)
        except ID.AuthError as e:
            tr.event("approval_decision", decision="deny", code=e.code)
            return self._fail(corr_id, "AUTH_DENIED", status="DENIED", state=run["state"], detail=e.code, actor="anonymous")
        if not ID.Authority.role_allowed(who.role, "create_draft_purchase_order", {}):
            tr.event("approval_decision", decision="deny", code="ROLE_NOT_PERMITTED", user=who.id, role=who.role)
            return self._fail(corr_id, "ROLE_DENIED", status="DENIED", state=run["state"], detail=f"{who.role} may not approve", actor=who.id, role=who.role)
        if who.id == run["requester"]:
            tr.event("approval_decision", decision="deny", code="MAKER_CHECKER", user=who.id)
            return self._fail(corr_id, "MAKER_CHECKER", status="DENIED", state=run["state"], detail="requester may not approve their own request", actor=who.id, role=who.role)
        if run["state"] != "AWAITING_APPROVAL":
            tr.event("approval_decision", decision="deny", code="NOT_AWAITING", state=run["state"])
            cls = "APPROVAL_REPLAY" if run["state"] in ("EXECUTED", "APPROVED") else "NOT_AWAITING_APPROVAL"
            self.ledger.audit(who.id, who.role, f"decision_refused:{cls}", corr_id, run["approval_id"] or "", run["state"])
            return self._result(corr_id, "DENIED", failure=cls, detail=run["state"])
        aid = run["approval_id"]
        ap = self.weir.get_approval(aid) if aid else None
        if ap is None or ap.session_id != corr_id or ap.tool != WB.PROC_TOOL:
            return self._fail(corr_id, "APPROVAL_MISMATCH", status="DENIED", state=run["state"], detail="approval does not belong to this run", actor=who.id, role=who.role)
        if not approve:
            self.weir.resolve_approval(aid, False, by=who.id)
            self.ledger.set_proposal_state(run["proposal_id"], "REJECTED", who.id, who.role, corr_id)
            self.ledger.set_state(corr_id, "REJECTED", who.id, who.role, failure=f"rejected: {comment[:60]}")
            self.trace.set_status(corr_id, "COMPLETED", "REJECTED_BY_HUMAN", True)
            tr.event("approval_decision", decision="reject", by=who.id, comment=comment[:120])
            return self._result(corr_id, "REJECTED")
        state = self.weir.resolve_approval(aid, True, by=who.id)
        tr.event("approval_decision", decision="approve" if state == "approved" else state, by=who.id, role=who.role, approval_id=aid, comment=comment[:120])
        self.ledger.audit(who.id, who.role, f"approval_{state}", corr_id, aid, comment[:120])
        if state == "expired":
            return self._fail(corr_id, "APPROVAL_EXPIRED", status="EXPIRED", state="FAILED", detail="approval expired before it was granted", actor=who.id, role=who.role)
        if state != "approved":
            return self._fail(corr_id, "APPROVAL_REPLAY" if state.startswith("already") else "APPROVAL_MISMATCH", status="DENIED", state=run["state"], detail=state, actor=who.id, role=who.role)
        self.ledger.set_state(corr_id, "APPROVED", who.id, who.role)
        if not execute:
            return self._result(corr_id, "APPROVED_NOT_EXECUTED", approval_id=aid)
        return self.execute_approved(corr_id, approver=who)

    def execute_approved(self, corr_id, approver=None):
        """Re-issue the identical WEIR call. THE WEIR forwards it only if an unexpired, unconsumed approval for exactly this call hash exists for this session."""
        tr = self._tr(corr_id)
        run = self.ledger.run(corr_id)
        if run is None or run["state"] != "APPROVED":
            return self._result(corr_id, "DENIED", failure="NOT_AWAITING_APPROVAL", detail=(run or {}).get("state"))
        req = self.env.authority.reviewers.get(run["requester"])
        ident = ID.Identity(run["requester"], run["role"])
        gw, proc, ops = self._gateway(ident)
        sess = gw.open_session(corr_id)
        args = self._po_args(run["proposal_id"])
        approver_id = approver.id if approver else (self.weir.get_approval(run["approval_id"]).resolved_by or "unknown")
        proc.context = dict(approval_id=run["approval_id"], approved_by=approver_id, corr_id=corr_id)
        out, parsed, fail = self._call(gw, sess, WB.PROC_TOOL, args, corr_id, "S14")
        proc.context = None
        if out is not None and not out.forwarded:
            # the approval did not cover THIS call (arguments changed after approval, approval expired or already used): THE WEIR created a NEW pending approval
            cls = "REAPPROVAL_REQUIRED"
            self.ledger.set_state(corr_id, "AWAITING_APPROVAL", "system", None, approval_id=out.approval_id, failure=f"{cls}:approved call no longer matches")
            tr.event("failure", failure_class=cls, new_approval=out.approval_id, codes=out.codes)
            return self._result(corr_id, "REAPPROVAL_REQUIRED", failure=cls, approval_id=out.approval_id)
        if fail in ("TOOL_TIMEOUT", "DB_ERROR", "TOOL_BAD_RESPONSE"):
            # the write may or may not have happened: reconcile against the ledger (idempotency key) instead of guessing
            po = self.ledger.con.execute("SELECT po_id FROM po_drafts WHERE idem_key=?", (args["idempotency_key"],)).fetchone()
            if po:
                tr.event("recovery", action="reconciled_existing_po", po_id=po[0], after=fail)
                self.ledger.set_state(corr_id, "EXECUTED", "system", None)
                self.trace.set_status(corr_id, "COMPLETED", "EXECUTED_DRAFT_PO", True)
                return self._result(corr_id, "EXECUTED", po_id=po[0], recovered_from=fail)
            return self._fail(corr_id, fail, status="FAILED", state="FAILED", detail="draft not created; the approval was consumed: recovery requires re-approval", actor="system")
        if fail:
            err = (parsed or {}).get("error", "") if isinstance(parsed, dict) else ""
            cls = {"STALE_PROPOSAL": "STALE_PROPOSAL", "SUPPLIER_DATA_MISSING": "SUPPLIER_DATA_MISSING", "UNSAFE_QUANTITY": "UNSAFE_PROPOSAL", "UNSAFE_AMOUNT": "UNSAFE_PROPOSAL", "PROPOSAL_MISMATCH": "VALIDATION_FAILED"}.get(err, fail)
            return self._fail(corr_id, cls, status="FAILED", state="FAILED", detail=err or fail, actor="system")
        po = parsed.get("po_id")
        self.ledger.set_state(corr_id, "EXECUTED", "system", None, proposal_id=run["proposal_id"])
        self.trace.set_status(corr_id, "COMPLETED", "EXECUTED_DRAFT_PO", True)
        tr.event("stage", stage="S14", name="draft_po_created", po_id=po, state=parsed.get("state"), duplicate=parsed.get("duplicate"))
        tr.event("stage", stage="S16", name="no_external_transmission", external_transmissions=0)
        return self._result(corr_id, "EXECUTED", po_id=po, po_state=parsed.get("state"))

    def recover(self, corr_id, session):
        """Controlled recovery of a FAILED run whose draft was not created: the consumed approval cannot be reused, so the proposal goes back to the WEIR for a NEW approval."""
        run = self.ledger.run(corr_id)
        who = self.env.authority.identify(session)
        if run is None or run["state"] not in ("FAILED", "PROPOSED") or not run["proposal_id"]:
            return self._result(corr_id, "DENIED", failure="NOT_AWAITING_APPROVAL", detail=(run or {}).get("state"))
        if who.id != run["requester"] and who.role not in WB.PROCUREMENT_ROLES:
            return self._fail(corr_id, "ROLE_DENIED", status="DENIED", state="FAILED", detail="not permitted to recover", actor=who.id, role=who.role)
        if self.ledger.con.execute("SELECT 1 FROM po_drafts WHERE proposal_id=?", (run["proposal_id"],)).fetchone():
            self.ledger.set_state(corr_id, "EXECUTED", who.id, who.role)
            return self._result(corr_id, "EXECUTED", recovered_from="existing_draft")
        ident = ID.Identity(run["requester"], run["role"])
        gw, proc, ops = self._gateway(ident)
        sess = gw.open_session(corr_id)
        out, parsed, fail = self._call(gw, sess, WB.PROC_TOOL, self._po_args(run["proposal_id"]), corr_id, "S11")
        if out is None or out.forwarded or not out.approval_id:
            return self._fail(corr_id, fail or "TOOL_ERROR", status="FAILED", state="FAILED", detail="recovery could not obtain a new approval request", actor=who.id, role=who.role)
        self.ledger.set_state(corr_id, "AWAITING_APPROVAL", who.id, who.role, approval_id=out.approval_id, failure="")
        self._tr(corr_id).event("recovery", action="new_approval_requested", approval_id=out.approval_id)
        return self._result(corr_id, "AWAITING_APPROVAL", approval_id=out.approval_id, recovered=True)

    def status(self, corr_id):
        run = self.ledger.run(corr_id)
        return None if run is None else dict(run, side_effects=self._side_effects())
