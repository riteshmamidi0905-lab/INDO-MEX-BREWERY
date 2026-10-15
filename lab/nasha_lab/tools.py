"""Typed business tools with a permission model. One registry feeds the agent, the FastAPI service and the MCP server.

Permission classes
  READ                automatic        query data, search knowledge
  ANALYZE             automatic        pure calculations over evidence
  DRAFT               automatic        create a DRAFT record that is not an action (no purchase, no message)
  MUTATE_SIMULATION   approval-bound   change simulation state; needs an approval bound to this exact tool + arguments
  EXTERNAL_ACTION     FORBIDDEN        contact a supplier, place an order: refused in this prototype, always, and logged
"""
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from . import dq, knowledge as K
from .world import RECIPES, STALE_DAYS, World

READ, ANALYZE, DRAFT, MUTATE, EXTERNAL = "READ", "ANALYZE", "DRAFT", "MUTATE_SIMULATION", "EXTERNAL_ACTION"
AUTO = {READ, ANALYZE, DRAFT}
HIDDEN_TERMS = ("stock", "broth", "bouillon", "shortening", "rennet", "natural flavor", "worcestershire", "flavour base", "flavor base", "base", "fining")
PLANT_OR_ALLOWED_SOURCE = re.compile(r"vegetable|plant|microbial|chicken|goat|lamb|fish|seafood", re.I)
SECRET_KEYS = re.compile(r"key|token|secret|password|credential", re.I)


# ----------------------------------------------------------------- models
class InventoryIn(BaseModel):
    location_id: str = Field(pattern=r"^L\d{2}$"); ingredient: str = Field(min_length=2, max_length=40)

class InventoryOut(BaseModel):
    location_id: str; ingredient: str; unit: str
    last_count_date: Optional[str]; last_count_qty: Optional[float]; days_since_count: Optional[int]
    receipts_since_count: float; usage_since_count_est: float; on_hand_estimate: Optional[float]
    avg_daily_usage_14d: float; days_of_cover: Optional[float]; newer_counts_quarantined: list[str]; data_flags: list[str]

class RiskIn(BaseModel):
    location_id: str = Field(pattern=r"^L\d{2}$"); ingredient: str

class RiskOut(BaseModel):
    lead_time_days: Optional[int]; supplier_id: Optional[str]; days_of_cover: Optional[float]; open_po_qty_arriving_in_time: float
    shortfall_before_lead_time: bool; count_variance_ratio: Optional[float]; recommended_qty_kg: Optional[float]; reasons: list[str]

class FindingIn(BaseModel):
    finding_id: int = Field(ge=1)

class FindingOut(BaseModel):
    finding_id: int; rule: str; table: str; key: str; severity: str; detail: str

class FindingsListIn(BaseModel):
    rule: Optional[str] = None; limit: int = Field(default=20, ge=1, le=100)

class FindingsListOut(BaseModel):
    findings: list[FindingOut]

class LineageIn(BaseModel):
    table: Literal["orders", "order_lines", "inventory_counts"]; key: str = Field(min_length=3, max_length=60)

class LineageOut(BaseModel):
    table: str; key: str; quarantined: bool; reasons: list[str]; findings: list[str]; affected_records: list[str]; in_modeled_layer: bool; revenue_cents_excluded: int

class POIn(BaseModel):
    ingredient: Optional[str] = None

class POOut(BaseModel):
    purchase_orders: list[dict]

class SupplierIn(BaseModel):
    supplier_id: Optional[str] = None; ingredient: Optional[str] = None

    @field_validator("ingredient")
    @classmethod
    def one_given(cls, v, info): return v

class SupplierOut(BaseModel):
    suppliers: list[dict]

class ProposalIn(BaseModel):
    proposal_id: str = Field(pattern=r"^P-\d+$")

class ProposalOut(BaseModel):
    proposal_id: str; supplier_id: str; ingredient_text: str; declared_source: str; spec_sheet_status: str

class SearchIn(BaseModel):
    query: str = Field(min_length=3, max_length=300); k: int = Field(default=4, ge=1, le=10); include_nonauthoritative: bool = False

class SearchOut(BaseModel):
    hits: list[dict]

class PolicyIn(BaseModel):
    question: str = Field(min_length=3, max_length=300)

class PolicyOut(BaseModel):
    abstained: bool; answer: str; reason: str; citations: list[dict]; injection_flagged: list[str]; non_authoritative_matches: list[dict]

class PolicyAssessIn(BaseModel):
    ingredient_text: str = Field(min_length=2, max_length=200); declared_source: str = Field(max_length=200); spec_sheet_status: Literal["ON_FILE", "MISSING"]

class PolicyAssessOut(BaseModel):
    verdict: Literal["PROHIBITED", "REQUIRES_REVIEW", "CLEARED_PENDING_HUMAN", "NO_POLICY_SIGNAL"]; basis: list[str]

class DraftPurchaseIn(BaseModel):
    location_id: str = Field(pattern=r"^L\d{2}$"); ingredient: str; qty_kg: float = Field(gt=0, le=500); supplier_id: str = Field(pattern=r"^S\d{2}$")
    rationale: str = Field(min_length=10, max_length=600); evidence_ids: list[str] = Field(min_length=1)

class DraftOut(BaseModel):
    draft_id: str; status: Literal["DRAFT_NOT_SUBMITTED"]; notice: str

class TicketIn(BaseModel):
    kind: Literal["QUALITY_REVIEW", "POLICY_REVIEW", "INVENTORY_RECOUNT"]; summary: str = Field(min_length=10, max_length=600); evidence_ids: list[str] = Field(min_length=1)

class AdjustIn(BaseModel):
    location_id: str = Field(pattern=r"^L\d{2}$"); ingredient: str; qty_delta: float = Field(ge=-200, le=200); reason: str = Field(min_length=10, max_length=300)

class AdjustOut(BaseModel):
    movement_id: int; applied: bool

class FlagIn(BaseModel):
    table: Literal["orders", "order_lines", "inventory_counts", "supplier_proposals"]; key: str = Field(min_length=3, max_length=60); reason: str = Field(min_length=10, max_length=300)

class FlagOut(BaseModel):
    review_item_id: int; applied: bool

class ReleaseIn(BaseModel):
    draft_id: str = Field(pattern=r"^DR-[0-9a-f]{8}$")

class ReleaseOut(BaseModel):
    draft_id: str; status: Literal["APPROVED_FOR_HUMAN_PROCUREMENT_REVIEW"]; notice: str


class ExternalIn(BaseModel):
    supplier_id: str = "S00"; message: str = ""; po_id: str = ""

class Anything(BaseModel):
    model_config = {"extra": "allow"}


@dataclass
class ToolSpec:
    name: str; permission: str; description: str; input_model: type; output_model: type; fn: Callable
    exposed: bool = True   # False: never offered over MCP/HTTP (still registered so a forbidden call is refused and logged)


@dataclass
class ToolContext:
    run_id: str = "adhoc"; request_id: str = ""; approval: Optional[dict] = None; kb: Any = None; trace: Any = None; timeout_s: float = 2.0


def args_hash(tool, args): return hashlib.sha256(json.dumps({"tool": tool, "args": args}, sort_keys=True, default=str).encode()).hexdigest()[:16]


def redact(obj):
    if isinstance(obj, dict): return {k: ("[REDACTED]" if SECRET_KEYS.search(k) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list): return [redact(x) for x in obj]
    return obj


# ----------------------------------------------------------------- implementations
class NotFound(Exception): pass


def _usage_since(w, loc, ing, since):
    r = w.q("""SELECT l.item_id, SUM(l.qty) q FROM fact_order_line l JOIN fact_order o USING(order_id) WHERE o.location_id=? AND o.order_date>? GROUP BY 1""", loc, since)
    return sum(x["q"] * RECIPES.get(x["item_id"], {}).get(ing, 0) for x in r)


def _daily_avg(w, loc, ing, end, days=14):
    start = (end - dt.timedelta(days=days)).isoformat()
    r = w.q("""SELECT l.item_id, SUM(l.qty) q FROM fact_order_line l JOIN fact_order o USING(order_id) WHERE o.location_id=? AND o.order_date>? AND o.order_date<=? GROUP BY 1""", loc, start, end.isoformat())
    return sum(x["q"] * RECIPES.get(x["item_id"], {}).get(ing, 0) for x in r) / days


def t_query_inventory(w: World, a: InventoryIn, ctx):
    unit = w.q("SELECT unit FROM ingredients WHERE ingredient=?", a.ingredient)
    if not unit: raise NotFound(f"unknown ingredient {a.ingredient!r}")
    c = w.q("SELECT count_date, qty FROM fact_inventory_count WHERE location_id=? AND ingredient=? ORDER BY count_date DESC LIMIT 1", a.location_id, a.ingredient)
    flags, newer = [], []
    qs = [r["key"] for r in w.q("SELECT key FROM quarantine WHERE tbl='inventory_counts' AND key LIKE ?", f"{a.location_id}:%:{a.ingredient}")]
    if c:
        newer = sorted(k for k in qs if k.split(":")[1] > c[0]["count_date"])
        since = c[0]["count_date"]; rec = w.q("SELECT COALESCE(SUM(qty),0) s FROM inventory_movements WHERE location_id=? AND ingredient=? AND move_date>? AND kind IN ('RECEIPT','ADJUSTMENT')", a.location_id, a.ingredient, since)[0]["s"]
        use = _usage_since(w, a.location_id, a.ingredient, since); on = round(c[0]["qty"] + rec - use, 2)
        age = (w.today - dt.date.fromisoformat(since)).days
        if age > STALE_DAYS: flags.append("STALE_COUNT")
        if newer: flags.append("NEWER_COUNT_QUARANTINED")
        if on < 0: flags.append("NEGATIVE_ESTIMATE"); on = 0.0
        avg = _daily_avg(w, a.location_id, a.ingredient, w.today)
        return dict(location_id=a.location_id, ingredient=a.ingredient, unit=unit[0]["unit"], last_count_date=since, last_count_qty=c[0]["qty"], days_since_count=age, receipts_since_count=round(rec, 2),
                    usage_since_count_est=round(use, 2), on_hand_estimate=on, avg_daily_usage_14d=round(avg, 3), days_of_cover=round(on / avg, 2) if avg > 0 else None, newer_counts_quarantined=newer, data_flags=flags)
    return dict(location_id=a.location_id, ingredient=a.ingredient, unit=unit[0]["unit"], last_count_date=None, last_count_qty=None, days_since_count=None, receipts_since_count=0, usage_since_count_est=0,
                on_hand_estimate=None, avg_daily_usage_14d=round(_daily_avg(w, a.location_id, a.ingredient, w.today), 3), days_of_cover=None, newer_counts_quarantined=qs, data_flags=["NO_COUNT"])


def t_assess_inventory_risk(w, a: RiskIn, ctx):
    inv = t_query_inventory(w, InventoryIn(location_id=a.location_id, ingredient=a.ingredient), ctx)
    sup = w.q("""SELECT si.supplier_id, si.lead_time_days, si.min_order_qty, s.status FROM supplier_ingredients si JOIN suppliers s USING(supplier_id) WHERE si.ingredient=? ORDER BY s.status='ACTIVE' DESC LIMIT 1""", a.ingredient)
    lead = sup[0]["lead_time_days"] if sup else None
    arriving = 0.0
    if lead is not None:
        horizon = (w.today + dt.timedelta(days=lead)).isoformat()
        arriving = sum(r["qty"] for r in w.q("""SELECT l.qty FROM purchase_orders p JOIN purchase_order_lines l USING(po_id) WHERE p.status='OPEN' AND l.ingredient=? AND p.expected_date<=?""", a.ingredient, horizon))
    reasons, cover, shortfall, rec, var = [], inv["days_of_cover"], False, None, None
    if "NO_COUNT" in inv["data_flags"] or "STALE_COUNT" in inv["data_flags"]:
        reasons.append("count is missing or stale; cover cannot be trusted")
    if cover is not None and lead is not None and cover < lead and arriving == 0:
        shortfall = True; reasons.append(f"cover {cover} d is below supplier lead time {lead} d and no open PO arrives in time")
        need = inv["avg_daily_usage_14d"] * (lead + 3) - (inv["on_hand_estimate"] or 0) - arriving
        rec = round(max(need, sup[0]["min_order_qty"]), 1)
    elif cover is not None and lead is not None and cover < lead and arriving > 0:
        reasons.append(f"cover {cover} d is below lead time {lead} d but an open PO ({arriving} kg) is expected within the lead time")
    # variance of the latest count vs what the previous count, receipts and usage predict
    prev = w.q("SELECT count_date, qty FROM fact_inventory_count WHERE location_id=? AND ingredient=? ORDER BY count_date DESC LIMIT 2", a.location_id, a.ingredient)
    if len(prev) == 2:
        d0, d1 = prev[1]["count_date"], prev[0]["count_date"]
        rec = w.q("SELECT COALESCE(SUM(qty),0) s FROM inventory_movements WHERE location_id=? AND ingredient=? AND move_date>? AND move_date<=?", a.location_id, a.ingredient, d0, d1)[0]["s"] if rec is None else rec
        receipts = w.q("SELECT COALESCE(SUM(qty),0) s FROM inventory_movements WHERE location_id=? AND ingredient=? AND move_date>? AND move_date<=? AND kind IN ('RECEIPT','ADJUSTMENT')", a.location_id, a.ingredient, d0, d1)[0]["s"]
        use = _usage_since(w, a.location_id, a.ingredient, d0) - _usage_since(w, a.location_id, a.ingredient, d1)
        expected = max(prev[1]["qty"] + receipts - use, 0.0)
        var = round(prev[0]["qty"] / expected, 2) if expected > 0.5 else None
        if var is not None and (var > 2.0 or var < 0.4): reasons.append(f"latest count is {var}x the expected quantity; recount before acting")
    if not isinstance(rec, (int, float)) or not shortfall: rec = rec if shortfall else None
    return dict(lead_time_days=lead, supplier_id=sup[0]["supplier_id"] if sup else None, days_of_cover=cover, open_po_qty_arriving_in_time=round(arriving, 2), shortfall_before_lead_time=shortfall,
                count_variance_ratio=var, recommended_qty_kg=rec, reasons=reasons)


def t_get_quality_finding(w, a: FindingIn, ctx):
    r = w.q("SELECT rowid finding_id, rule, tbl 'table', key, severity, detail FROM dq_finding WHERE rowid=?", a.finding_id)
    if not r: raise NotFound(f"finding {a.finding_id}")
    return r[0]


def t_list_quality_findings(w, a: FindingsListIn, ctx):
    sql = "SELECT rowid finding_id, rule, tbl 'table', key, severity, detail FROM dq_finding" + (" WHERE rule=?" if a.rule else "") + " ORDER BY rowid LIMIT ?"
    return dict(findings=w.q(sql, *( [a.rule] if a.rule else []), a.limit))


def t_get_lineage(w, a: LineageIn, ctx):
    q = w.q("SELECT reason, cascade FROM quarantine WHERE tbl=? AND key=?", a.table, a.key)
    f = [r["rule"] for r in w.q("SELECT rule FROM dq_finding WHERE tbl=? AND key=?", a.table, a.key)]
    affected, rev = [], 0
    if a.table == "orders":
        affected = [f'{r["order_id"]}:{r["line_no"]}' for r in w.q("SELECT order_id,line_no FROM fact_order_line WHERE order_id=?", a.key)]
        affected += [r["key"] for r in w.q("SELECT key FROM quarantine WHERE tbl='order_lines' AND key LIKE ?", a.key + ":%")]
        row = w.q("SELECT total_cents FROM fact_order WHERE order_id=?", a.key)
        in_model = bool(row); rev = 0 if in_model else 0
    else:
        in_model = bool(w.q({"order_lines": "SELECT 1 FROM fact_order_line WHERE order_id||':'||line_no=?", "inventory_counts": "SELECT 1 FROM fact_inventory_count WHERE location_id||':'||count_date||':'||ingredient=?"}[a.table], a.key))
    if not q and not f and not in_model: raise NotFound(f"{a.table}:{a.key}")
    return dict(table=a.table, key=a.key, quarantined=bool(q), reasons=[x["reason"] for x in q], findings=f, affected_records=sorted(set(affected))[:20], in_modeled_layer=in_model, revenue_cents_excluded=rev)


def t_get_open_purchase_orders(w, a: POIn, ctx):
    sql = "SELECT p.po_id, p.supplier_id, p.status, p.expected_date, l.ingredient, l.qty, l.unit FROM purchase_orders p JOIN purchase_order_lines l USING(po_id) WHERE p.status='OPEN'" + (" AND l.ingredient=?" if a.ingredient else "") + " ORDER BY p.expected_date"
    return dict(purchase_orders=w.q(sql, *([a.ingredient] if a.ingredient else [])))


def t_get_supplier_status(w, a: SupplierIn, ctx):
    if not a.supplier_id and not a.ingredient: raise ValueError("give supplier_id or ingredient")
    r = w.q("""SELECT s.supplier_id, s.name, s.status, si.ingredient, si.lead_time_days, si.spec_sheet_status, si.min_order_qty FROM suppliers s LEFT JOIN supplier_ingredients si USING(supplier_id)
               WHERE (? IS NULL OR s.supplier_id=?) AND (? IS NULL OR si.ingredient=?) ORDER BY s.supplier_id""", a.supplier_id, a.supplier_id, a.ingredient, a.ingredient)
    if not r: raise NotFound("no matching supplier")
    return dict(suppliers=r)


def t_get_supplier_proposal(w, a: ProposalIn, ctx):
    r = w.q("SELECT * FROM supplier_proposals WHERE proposal_id=?", a.proposal_id)
    if not r: raise NotFound(a.proposal_id)
    return r[0]


def t_search_nasha_knowledge(w, a: SearchIn, ctx):
    hits = ctx.kb.search(a.query, k=a.k, include_nonauthoritative=a.include_nonauthoritative)
    return dict(hits=[{k: h[k] for k in ("chunk_id", "document_id", "source_path", "effective_status", "verification_status", "score", "injection_suspected")} | {"excerpt": ("[withheld: possible instruction injection]" if h["injection_suspected"] else h["text"][:300])} for h in hits])


def t_get_current_policy(w, a: PolicyIn, ctx):
    r = ctx.kb.ask(a.question)
    return {k: r.get(k, [] if k.endswith("s") else "") for k in ("abstained", "answer", "reason", "citations", "injection_flagged", "non_authoritative_matches")}


def t_assess_policy_ingredient(w, a: PolicyAssessIn, ctx):
    text = f"{a.ingredient_text} {a.declared_source}"
    if dq.FORBIDDEN_RE.search(text):
        return dict(verdict="PROHIBITED", basis=["D-54 term in ingredient or declared source: " + dq.FORBIDDEN_RE.search(text).group(0)])
    hidden = [t for t in HIDDEN_TERMS if t in a.ingredient_text.lower()]
    if hidden:
        if a.spec_sheet_status == "ON_FILE" and PLANT_OR_ALLOWED_SOURCE.search(a.declared_source) and "unspecified" not in a.declared_source.lower():
            return dict(verdict="CLEARED_PENDING_HUMAN", basis=[f"hidden-derivative term(s) {hidden}", "supplier statement on file names a permitted source; a human must confirm the document"])
        return dict(verdict="REQUIRES_REVIEW", basis=[f"hidden-derivative term(s) {hidden}", f"spec sheet {a.spec_sheet_status}; declared source {a.declared_source!r} does not establish a permitted source"])
    return dict(verdict="NO_POLICY_SIGNAL", basis=["no D-54 term and no hidden-derivative term"])


def _draft(w, ctx, kind, payload):
    did = "DR-" + uuid.uuid4().hex[:8]
    w.con.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?)", (did, ctx.run_id, kind, json.dumps(payload), "DRAFT_NOT_SUBMITTED", w.today.isoformat())); w.con.commit()
    return did


def t_draft_purchase_recommendation(w, a: DraftPurchaseIn, ctx):
    s = w.q("""SELECT s.status, si.min_order_qty FROM suppliers s JOIN supplier_ingredients si USING(supplier_id) WHERE s.supplier_id=? AND si.ingredient=?""", a.supplier_id, a.ingredient)
    if not s: raise ValueError(f"supplier {a.supplier_id} does not supply {a.ingredient}")
    if s[0]["status"] != "ACTIVE": raise ValueError(f"supplier {a.supplier_id} is {s[0]['status']}")
    if a.qty_kg < s[0]["min_order_qty"]: raise ValueError(f"quantity below supplier minimum {s[0]['min_order_qty']} kg")
    return dict(draft_id=_draft(w, ctx, "PURCHASE_RECOMMENDATION", a.model_dump()), status="DRAFT_NOT_SUBMITTED", notice="DRAFT RECOMMENDATION ONLY. This is not a purchase order; nothing was sent to any supplier.")


def t_draft_review_ticket(w, a: TicketIn, ctx):
    return dict(draft_id=_draft(w, ctx, a.kind, a.model_dump()), status="DRAFT_NOT_SUBMITTED", notice="DRAFT review ticket. Nothing was sent to anyone.")


def t_adjust_inventory_record(w, a: AdjustIn, ctx):
    cur = w.con.execute("INSERT INTO inventory_movements(location_id,ingredient,move_date,kind,qty) VALUES(?,?,?,?,?)", (a.location_id, a.ingredient, w.today.isoformat(), "ADJUSTMENT", a.qty_delta)); w.con.commit()
    return dict(movement_id=cur.lastrowid, applied=True)


def t_flag_record_for_review(w, a: FlagIn, ctx):
    cur = w.con.execute("INSERT INTO review_queue(run_id,kind,payload,status,created) VALUES(?,?,?,?,?)", (ctx.run_id, "RECORD_REVIEW", json.dumps(a.model_dump()), "OPEN", w.today.isoformat())); w.con.commit()
    return dict(review_item_id=cur.lastrowid, applied=True)


def t_release_draft(w, a: ReleaseIn, ctx):
    r = w.q("SELECT status FROM drafts WHERE draft_id=?", a.draft_id)
    if not r: raise NotFound(a.draft_id)
    if r[0]["status"] != "DRAFT_NOT_SUBMITTED": raise ValueError(f"draft is {r[0]['status']}")
    w.con.execute("UPDATE drafts SET status='APPROVED_FOR_HUMAN_PROCUREMENT_REVIEW' WHERE draft_id=?", (a.draft_id,)); w.con.commit()
    return dict(draft_id=a.draft_id, status="APPROVED_FOR_HUMAN_PROCUREMENT_REVIEW", notice="Approved for a human buyer to review. This is NOT a purchase order and nothing was sent to a supplier.")


def t_external(w, a, ctx): raise AssertionError("external actions are never executed")


TOOLS: dict[str, ToolSpec] = {}
def _reg(name, perm, desc, i, o, fn, exposed=True): TOOLS[name] = ToolSpec(name, perm, desc, i, o, fn, exposed)

_reg("query_inventory", READ, "Latest valid inventory count, receipts and estimated usage since the count, 14-day average usage, days of cover and data-quality flags for one ingredient at one location.", InventoryIn, InventoryOut, t_query_inventory)
_reg("assess_inventory_risk", ANALYZE, "Compare days of cover with supplier lead time and open purchase orders, check the latest count against the previous count, and compute a draftable reorder quantity.", RiskIn, RiskOut, t_assess_inventory_risk)
_reg("get_quality_finding", READ, "One data-quality finding by id.", FindingIn, FindingOut, t_get_quality_finding)
_reg("list_quality_findings", READ, "List data-quality findings, optionally by rule.", FindingsListIn, FindingsListOut, t_list_quality_findings)
_reg("get_lineage", READ, "Quarantine status, findings and affected records for one record key.", LineageIn, LineageOut, t_get_lineage)
_reg("get_open_purchase_orders", READ, "Open purchase orders, optionally for one ingredient.", POIn, POOut, t_get_open_purchase_orders)
_reg("get_supplier_status", READ, "Supplier status, lead time and spec-sheet status by supplier or ingredient.", SupplierIn, SupplierOut, t_get_supplier_status)
_reg("get_supplier_proposal", READ, "A supplier's ingredient substitution proposal.", ProposalIn, ProposalOut, t_get_supplier_proposal)
_reg("search_nasha_knowledge", READ, "Status-aware search of the NASHA documentation. Non-authoritative sources are excluded unless requested and are always labelled.", SearchIn, SearchOut, t_search_nasha_knowledge)
_reg("get_current_policy", READ, "Answer a policy question ONLY from authoritative current sources; abstains with INSUFFICIENT VERIFIED EVIDENCE otherwise.", PolicyIn, PolicyOut, t_get_current_policy)
_reg("assess_policy_ingredient", ANALYZE, "Screen an ingredient proposal against the D-54 no-beef/no-pork rules and the hidden-derivative checklist. Never approves without a human.", PolicyAssessIn, PolicyAssessOut, t_assess_policy_ingredient)
_reg("draft_purchase_recommendation", DRAFT, "Create a DRAFT purchase recommendation (not a purchase order). Requires evidence ids and an ACTIVE supplier of the ingredient.", DraftPurchaseIn, DraftOut, t_draft_purchase_recommendation)
_reg("draft_review_ticket", DRAFT, "Create a DRAFT review ticket for a human. Sends nothing.", TicketIn, DraftOut, t_draft_review_ticket)
_reg("adjust_inventory_record", MUTATE, "Record an inventory adjustment in the simulation. Requires an approval bound to these exact arguments.", AdjustIn, AdjustOut, t_adjust_inventory_record)
_reg("flag_record_for_review", MUTATE, "Place a record in the human review queue in the simulation. Requires an approval bound to these exact arguments.", FlagIn, FlagOut, t_flag_record_for_review)
_reg("release_draft", MUTATE, "Mark an approved draft as released to human procurement review in the simulation. Still not a purchase order. Requires an approval bound to these exact arguments.", ReleaseIn, ReleaseOut, t_release_draft)
_reg("contact_supplier", EXTERNAL, "FORBIDDEN in this prototype: contact a supplier.", ExternalIn, Anything, t_external, exposed=False)
_reg("place_purchase_order", EXTERNAL, "FORBIDDEN in this prototype: place or submit a purchase order.", ExternalIn, Anything, t_external, exposed=False)


# ----------------------------------------------------------------- executor
def _err(name, perm, code, msg, t0, ctx, args=None):
    res = dict(ok=False, tool=name, permission=perm, error=dict(code=code, message=msg), data=None, ms=round((time.perf_counter() - t0) * 1000, 2))
    if ctx.trace is not None: ctx.trace.event("tool_error", tool=name, permission=perm, args=redact(args or {}), code=code, message=msg[:200])
    return res


def execute(w: World, name: str, args: dict, ctx: Optional[ToolContext] = None) -> dict:
    """Validate -> authorise -> (fault hooks) -> run with timeout -> validate output. Always returns a structured result; never raises."""
    ctx = ctx or ToolContext(); t0 = time.perf_counter()
    spec = TOOLS.get(name)
    if spec is None: return _err(name, "UNKNOWN", "UNKNOWN_TOOL", f"no tool named {name!r}", t0, ctx, args)
    if spec.permission == EXTERNAL: return _err(name, spec.permission, "FORBIDDEN_EXTERNAL_ACTION", "external actions are forbidden in this prototype", t0, ctx, args)
    try:
        parsed = spec.input_model.model_validate(args)
    except ValidationError as e:
        return _err(name, spec.permission, "INVALID_ARGUMENTS", "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())[:300], t0, ctx, args)
    clean = parsed.model_dump()
    if spec.permission == MUTATE:
        ap = ctx.approval
        if not ap or ap.get("run_id") != ctx.run_id or ap.get("tool") != name or ap.get("args_hash") != args_hash(name, clean):
            return _err(name, spec.permission, "APPROVAL_REQUIRED", "a human approval bound to this run, tool and exact arguments is required", t0, ctx, clean)
    fault = w.faults.get(name)
    def call():
        if fault == "timeout" or fault == "slow": time.sleep(0.3 if fault == "slow" else 5)
        if fault == "error": raise RuntimeError("injected upstream failure")
        if fault == "malformed": return {"unexpected": "shape"}
        with w.lock: return spec.fn(w, parsed, ctx)
    ex = cf.ThreadPoolExecutor(max_workers=1)
    try:
        fut = ex.submit(call); raw = fut.result(timeout=ctx.timeout_s if fault != "slow" else 0.05)
    except cf.TimeoutError:
        ex.shutdown(wait=False, cancel_futures=True)
        return _err(name, spec.permission, "TIMEOUT", f"tool exceeded {ctx.timeout_s}s", t0, ctx, clean)
    except NotFound as e:
        return _err(name, spec.permission, "NOT_FOUND", str(e), t0, ctx, clean)
    except (ValueError, AssertionError) as e:
        return _err(name, spec.permission, "REJECTED", str(e), t0, ctx, clean)
    except Exception as e:
        return _err(name, spec.permission, "UPSTREAM_FAILURE", f"{type(e).__name__}: {e}", t0, ctx, clean)
    finally:
        ex.shutdown(wait=False)
    try:
        data = spec.output_model.model_validate(raw).model_dump()
    except ValidationError:
        return _err(name, spec.permission, "MALFORMED_RESULT", "tool result did not match its output schema", t0, ctx, clean)
    res = dict(ok=True, tool=name, permission=spec.permission, error=None, data=data, ms=round((time.perf_counter() - t0) * 1000, 2))
    if ctx.trace is not None: ctx.trace.event("tool_call", tool=name, permission=spec.permission, args=redact(clean), result_summary=_summ(data), ms=res["ms"])
    return res


def _summ(d):
    s = json.dumps(d, default=str)
    return s if len(s) < 400 else s[:400] + "...[truncated]"


def tool_catalog(exposed_only=True):
    return [dict(name=t.name, permission=t.permission, description=t.description, input_schema=t.input_model.model_json_schema()) for t in TOOLS.values() if t.exposed or not exposed_only]
