"""NASHA Ops AI over the warehouse: a deterministic, read-only tool layer with an authorization gate, an audit log and an evaluation set.

SYNTHETIC data only. This is an in-repo policy gate in the *style* of THE WEIR (default deny, explicit grants, every decision logged); it is NOT
the separate THE WEIR gateway, and no claim is made that it integrates with it. Nothing here writes to the warehouse: the warehouse is opened
read-only and the audit log lives in its own database file.

Flow for every call:  published? -> known tool? -> role grants tool? -> arguments valid? -> site scope ok? -> run a fixed parameterised query -> audit.
The model (or router) never supplies SQL; it names a tool and arguments, and the tool owns the query text.
"""
import json
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

from . import db as wdb

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
LOC = re.compile(r"^L\d{2}$")
RANK_METRICS = {"net_cents", "orders", "labor_pct_of_sales", "sales_per_labor_hour_cents", "waste_pct_of_cogs", "gross_margin_cents", "avg_ticket_cents"}


class Denied(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


@dataclass(frozen=True)
class Principal:
    user: str
    role: str                     # exec | finance | analyst | site_manager
    site: Optional[str] = None    # required for site_manager


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    roles: frozenset
    site_scoped: bool             # site_manager may only use it for their own location_id
    run: Callable[[sqlite3.Connection, dict], tuple]   # -> (rows, source_table)


def _month(a, k="month"):
    v = a.get(k)
    if not isinstance(v, str) or not MONTH.match(v):
        raise Denied("bad_argument", f"{k} must be YYYY-MM")
    return v


def _loc(a, required=True):
    v = a.get("location_id")
    if v is None and not required:
        return None
    if not isinstance(v, str) or not LOC.match(v):
        raise Denied("bad_argument", "location_id must look like L01")
    return v


def _limit(a, default=5):
    v = a.get("limit", default)
    if not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 25:
        raise Denied("bad_argument", "limit must be an integer 1..25")
    return v


def _rows(con, sql, p=()):
    cur = con.execute(sql, p)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _t_company_month(con, a):
    m = _month(a)
    return _rows(con, "SELECT * FROM mart_company_month WHERE month=?", (m,)), "mart_company_month"


def _t_location_month(con, a):
    m, l = _month(a), _loc(a)
    return _rows(con, "SELECT * FROM mart_location_month WHERE month=? AND location_id=?", (m, l)), "mart_location_month"


def _t_rank_locations(con, a):
    m, lim = _month(a), _limit(a)
    metric = a.get("metric")
    if metric not in RANK_METRICS:
        raise Denied("bad_argument", f"metric must be one of {sorted(RANK_METRICS)}")
    order = "ASC" if a.get("order") == "asc" else "DESC"
    # metric and order come from fixed allow-lists above, never from the caller's text
    return _rows(con, f"SELECT location_id, format, {metric} AS value FROM mart_location_month WHERE month=? AND {metric} IS NOT NULL ORDER BY {metric} {order}, location_id LIMIT ?", (m, lim)), "mart_location_month"


def _t_top_products(con, a):
    m, lim = _month(a), _limit(a)
    cat = a.get("category")
    if cat is not None and cat not in {r[0] for r in con.execute("SELECT DISTINCT category FROM dim_product")}:
        raise Denied("bad_argument", "unknown category")
    if cat:
        return _rows(con, "SELECT item_id, name, category, units, net_cents, margin_pct FROM mart_product_month WHERE month=? AND category=? ORDER BY net_cents DESC, item_id LIMIT ?", (m, cat, lim)), "mart_product_month"
    return _rows(con, "SELECT item_id, name, category, units, net_cents, margin_pct FROM mart_product_month WHERE month=? ORDER BY net_cents DESC, item_id LIMIT ?", (m, lim)), "mart_product_month"


def _t_waste(con, a):
    m, l, lim = _month(a), _loc(a, required=False), _limit(a)
    if l:
        return _rows(con, "SELECT ingredient, waste_kg, waste_cost_cents, events FROM mart_inventory_waste WHERE month=? AND location_id=? ORDER BY waste_cost_cents DESC, ingredient LIMIT ?", (m, l, lim)), "mart_inventory_waste"
    return _rows(con, "SELECT ingredient, sum(waste_kg) waste_kg, sum(waste_cost_cents) waste_cost_cents, sum(events) events FROM mart_inventory_waste WHERE month=? GROUP BY ingredient ORDER BY 3 DESC, ingredient LIMIT ?", (m, lim)), "mart_inventory_waste"


def _t_daily(con, a):
    m, l = _month(a), _loc(a)
    return _rows(con, "SELECT date, orders, net_cents, labor_cost_cents, labor_pct_of_sales, waste_cost_cents FROM mart_daily_location WHERE month=? AND location_id=? ORDER BY date", (m, l)), "mart_daily_location"


def _t_months(con, a):
    return _rows(con, "SELECT month FROM mart_company_month ORDER BY month"), "mart_company_month"


ALL = frozenset({"exec", "finance", "analyst", "site_manager"})
CORP = frozenset({"exec", "finance", "analyst"})
TOOLS = {t.name: t for t in (
    Tool("list_months", "Months available in the warehouse.", ALL, False, _t_months),
    Tool("company_month", "Company KPIs for one month.", CORP, False, _t_company_month),
    Tool("location_month", "One location's KPIs for one month.", ALL, True, _t_location_month),
    Tool("rank_locations", "Rank locations by an allow-listed metric (cross-site).", CORP, False, _t_rank_locations),
    Tool("top_products", "Top products by net sales (company-wide).", CORP, False, _t_top_products),
    Tool("waste", "Waste by ingredient, company-wide or for a location.", ALL, True, _t_waste),
    Tool("daily_series", "Daily orders, sales and labor for a location-month.", ALL, True, _t_daily),
)}


# ------------------------------------------------------------------ scenario (D-87) tools: recipes, menu economics, inventory, procurement (SYNTHETIC; read-only)
ING = re.compile(r"^i-[a-z0-9-]{2,40}$")


def _need_scn(con):
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='scn_menu_item'").fetchone():
        raise Denied("scenario_not_built", "the pricing/recipe scenario has not been built into this warehouse")


def _t_price_config(con, a):
    _need_scn(con)
    return _rows(con, "SELECT config_id, price_key, kind, price_cents, status FROM scn_pricing WHERE config_id NOT LIKE '%v1%' ORDER BY price_key"), "scn_pricing"


def _t_menu_economics(con, a):
    _need_scn(con)
    cat = a.get("menu_category")
    if cat is not None and cat not in ("appetizer", "main"):
        raise Denied("bad_argument", "menu_category must be appetizer or main")
    sql = ("SELECT menu_item_id, name, menu_category, price_cents, round(unit_food_cost_cents, 2) AS unit_food_cost_cents, round(unit_consumables_cents, 2) AS unit_consumables_cents, "
           "round(unit_food_cost_cents / price_cents, 4) AS food_cost_pct, round(price_cents - unit_food_cost_cents - unit_consumables_cents, 2) AS gross_profit_cents, menu_status "
           "FROM scn_menu_item" + (" WHERE menu_category=?" if cat else "") + " ORDER BY unit_food_cost_cents / price_cents DESC, menu_item_id")
    return _rows(con, sql, (cat,) if cat else ()), "scn_menu_item"


def _t_menu_profitability(con, a):
    _need_scn(con)
    m, lim = _month(a), _limit(a)
    return _rows(con, "SELECT menu_item_id, sum(units) units, sum(restated_net_cents) restated_net_cents, sum(food_and_consumables_cents) food_and_consumables_cents, sum(gross_profit_cents) gross_profit_cents "
                      "FROM scn_menu_profitability_month WHERE month=? GROUP BY menu_item_id ORDER BY 5 DESC, 1 LIMIT ?", (m, lim)), "scn_menu_profitability_month"


def _t_ingredient_usage(con, a):
    _need_scn(con)
    l, lim = _loc(a), _limit(a)
    w = a.get("week")
    if not isinstance(w, int) or isinstance(w, bool) or not 0 <= w <= 2000:
        raise Denied("bad_argument", "week must be an integer 0..2000")
    return _rows(con, "SELECT ingredient_id, round(theoretical_qty, 4) theoretical_qty, round(measured_qty, 4) measured_qty, variance_pct FROM scn_variance_week WHERE location_id=? AND week=? ORDER BY theoretical_qty DESC, ingredient_id LIMIT ?", (l, w, lim)), "scn_variance_week"


def _t_variance_flags(con, a):
    _need_scn(con)
    l, lim = _loc(a, required=False), _limit(a, 10)
    sql = "SELECT location_id, week, ingredient_id, variance_pct, baseline_pct, excess_pct, pattern, severity FROM scn_variance_flag" + (" WHERE location_id=?" if l else "") + " ORDER BY excess_pct DESC, location_id, week, ingredient_id LIMIT ?"
    return _rows(con, sql, ((l,) if l else ()) + (lim,)), "scn_variance_flag"


def _t_reorder(con, a):
    _need_scn(con)
    l, lim = _loc(a, required=False), _limit(a, 10)
    sql = ("SELECT reco_id, location_id, ingredient_id, round(need_qty, 4) need_qty, round(on_hand_qty, 4) on_hand_qty, order_qty, unit, supplier_id, est_cost_usd, price_class, status FROM scn_procurement_reco"
           + (" WHERE location_id=?" if l else "") + " ORDER BY est_cost_usd DESC, reco_id LIMIT ?")
    return _rows(con, sql, ((l,) if l else ()) + (lim,)), "scn_procurement_reco"


def _t_supplier_compare(con, a):
    _need_scn(con)
    ing = a.get("ingredient_id")
    if not isinstance(ing, str) or not ING.match(ing):
        raise Denied("bad_argument", "ingredient_id must look like i-chicken-thigh")
    return _rows(con, "SELECT supplier_id, quote_id, unit_price, pack_qty, lead_days, price_class FROM scn_supplier_quote WHERE ingredient_id=? ORDER BY unit_price, supplier_id", (ing,)), "scn_supplier_quote"


def _t_recipe_bom(con, a):
    _need_scn(con)
    r = a.get("recipe_id")
    if not isinstance(r, str) or not re.match(r"^[a-z0-9-]{3,60}$", r):
        raise Denied("bad_argument", "recipe_id must look like chicken-65-totopos")
    return _rows(con, "SELECT recipe_id, recipe_version, ingredient_id, round(ap_qty_per_portion, 5) ap_qty_per_portion, unit FROM scn_recipe_bom WHERE recipe_id=? ORDER BY ap_qty_per_portion DESC, ingredient_id", (r,)), "scn_recipe_bom"


SCN_CORP = frozenset({"exec", "finance", "analyst"})
TOOLS.update({t.name: t for t in (
    Tool("price_config", "Approved CONCEPT menu prices and pending serving-volume decisions.", ALL, False, _t_price_config),
    Tool("menu_economics", "Per-dish price, planning food cost, food-cost % and gross profit (planning assumptions).", SCN_CORP, False, _t_menu_economics),
    Tool("menu_profitability", "Simulated menu profitability for a month at approved concept prices (restated; synthetic).", SCN_CORP, False, _t_menu_profitability),
    Tool("ingredient_usage", "Theoretical vs measured ingredient usage for a site-week.", ALL, True, _t_ingredient_usage),
    Tool("variance_flags", "Waste/variance flags for unexplained excess usage.", ALL, True, _t_variance_flags),
    Tool("reorder_recommendations", "PROPOSED reorder recommendations (not orders; need human approval).", ALL, True, _t_reorder),
    Tool("supplier_comparison", "Compare SYNTHETIC supplier quotes for an ingredient.", SCN_CORP, False, _t_supplier_compare),
    Tool("recipe_bom", "Bill of materials (as-purchased units per portion) for a dish.", SCN_CORP, False, _t_recipe_bom),
)})
SITE_DEFAULT_TOOLS = {"waste", "variance_flags", "reorder_recommendations"}


AUDIT = """CREATE TABLE IF NOT EXISTS ops_ai_audit (call_id TEXT PRIMARY KEY, ts TEXT, user TEXT, role TEXT, site TEXT, tool TEXT, args TEXT, decision TEXT, code TEXT, rows INTEGER, ms REAL, warehouse_run TEXT, source TEXT)"""


class OpsAI:
    def __init__(self, warehouse_path, audit_path):
        self.wh = sqlite3.connect(f"file:{warehouse_path}?mode=ro", uri=True, timeout=30)
        self.audit = sqlite3.connect(str(audit_path))
        self.audit.execute(AUDIT)

    def close(self):
        self.wh.close()
        self.audit.close()

    # --------------------------------------------------------------- gate
    def _published_run(self):
        try:
            r = self.wh.execute("SELECT status, run_id FROM warehouse_status").fetchone()
        except sqlite3.Error:
            r = None
        if not r or r[0] != "published":
            raise Denied("not_published", "warehouse is not published: quality gates have not passed")
        return r[1]

    def call(self, who: Principal, tool: str, args: Optional[dict] = None) -> dict:
        args = dict(args or {})
        cid, t0 = uuid.uuid4().hex[:12], time.perf_counter()
        decision, code, rows, source, run = "allow", "ok", [], "", ""
        try:
            run = self._published_run()
            t = TOOLS.get(tool)
            if t is None:
                raise Denied("unknown_tool", f"no such tool: {tool}")
            if who.role not in t.roles:
                raise Denied("role_denied", f"role {who.role} may not use {tool}")
            if who.role == "site_manager":
                if not who.site or not LOC.match(who.site):
                    raise Denied("no_site", "site_manager principal has no valid site")
                if t.site_scoped:
                    loc = args.get("location_id")
                    if loc is None and tool in SITE_DEFAULT_TOOLS:
                        args["location_id"] = who.site   # default to their own site, never company-wide
                    elif loc != who.site:
                        raise Denied("site_scope", f"{who.user} is scoped to {who.site}")
            rows, source = t.run(self.wh, args)
        except Denied as d:
            decision, code = "deny", d.code
            err = str(d)
        finally:
            ms = (time.perf_counter() - t0) * 1000
            self.audit.execute("INSERT INTO ops_ai_audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (cid, wdb.now(), who.user, who.role, who.site, tool, json.dumps(args, sort_keys=True, default=str), decision, code, len(rows), round(ms, 2), run, source))
            self.audit.commit()
        if decision == "deny":
            return {"call_id": cid, "ok": False, "code": code, "error": err}
        return {"call_id": cid, "ok": True, "rows": rows, "provenance": {"source": source, "warehouse_run": run, "synthetic": True}}

    # ------------------------------------------------------------ routing
    def ask(self, who: Principal, question: str) -> dict:
        """Deterministic intent router (no model). Unrecognised or unsafe questions abstain rather than guess."""
        q = question.lower()
        mm = re.search(r"\b(\d{4}-\d{2})\b", q)
        ll = re.search(r"\b(l\d{2})\b", question, re.I)
        month = mm.group(1) if mm else None
        loc = ll.group(1).upper() if ll else None
        if re.search(r"\b(drop|delete|update|insert|ignore previous|system prompt)\b", q):
            return {"ok": False, "code": "abstain", "error": "request is not a read-only business question"}
        if re.search(r"\b(reorder|procure|purchase order)", q) and not re.search(r"\b(place|send|submit|approve|execute)\b", q):
            return self.call(who, "reorder_recommendations", {**({"location_id": loc} if loc else {})})
        if "variance" in q or "over-portion" in q or "unexplained usage" in q:
            return self.call(who, "variance_flags", {**({"location_id": loc} if loc else {})})
        if re.search(r"food cost|menu margin|dish margin|gross profit per dish", q):
            return self.call(who, "menu_economics", {})
        if month is None:
            return {"ok": False, "code": "abstain", "error": "name a month as YYYY-MM"}
        if "waste" in q:
            return self.call(who, "waste", {"month": month, **({"location_id": loc} if loc else {})})
        if "top" in q and ("product" in q or "item" in q or "seller" in q):
            return self.call(who, "top_products", {"month": month})
        m = next((k for k, w in (("labor_pct_of_sales", "labor"), ("net_cents", "sales"), ("net_cents", "revenue"), ("orders", "orders")) if w in q), None)
        if ("highest" in q or "lowest" in q or "rank" in q) and m:
            return self.call(who, "rank_locations", {"month": month, "metric": m, "order": "asc" if "lowest" in q else "desc"})
        if loc:
            return self.call(who, "location_month", {"month": month, "location_id": loc})
        if "company" in q or "total" in q:
            return self.call(who, "company_month", {"month": month})
        return {"ok": False, "code": "abstain", "error": "question not recognised"}

    # ------------------------------------------------------ observability
    def metrics(self):
        a = self.audit
        n, den = a.execute("SELECT count(*), sum(decision='deny') FROM ops_ai_audit").fetchone()
        lat = sorted(r[0] for r in a.execute("SELECT ms FROM ops_ai_audit WHERE decision='allow'"))
        pct = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))] if lat else None
        by = dict(a.execute("SELECT code, count(*) FROM ops_ai_audit GROUP BY code").fetchall())
        return {"calls": n, "denied": den or 0, "by_code": by, "latency_ms_p50": pct(0.5), "latency_ms_p95": pct(0.95)}
