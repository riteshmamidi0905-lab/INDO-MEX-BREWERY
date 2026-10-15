"""Data-quality rules. Independent of the generator: they see only the staged data, never the truth labels."""
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .generator import AS_OF, INGREDIENT_UNIT

# D-54 domain rule. Must stay a superset of tools/diet_audit.py TERMS (enforced by tests/test_platform.py).
FORBIDDEN_TOKENS = ("beef", "pork", "bacon", "lard", "carnitas", "carne asada", "gelatin", "brisket", "chorizo", "barbacoa", "sausage", "ham", "tallow", "veal")
FORBIDDEN_RE = re.compile(r"\b(" + "|".join(FORBIDDEN_TOKENS) + r")\b", re.I)
PRICE_TOLERANCE = 0.25   # happy-hour discounts (10%) are legitimate; beyond 25% is flagged
ERROR, WARN, BLOCKER = "ERROR", "WARN", "BLOCKER"

ALL_RULES = [
    "malformed_timestamp", "missing_location", "future_timestamp", "duplicate_order",
    "near_duplicate_order", "order_total_mismatch", "orphan_item", "nonpositive_qty",
    "price_drift", "forbidden_protein", "unit_mismatch",
]


@dataclass(frozen=True)
class Finding:
    rule: str
    table: str
    key: str
    severity: str
    detail: str = ""


def run_rules(st, enabled=None):
    """st: staged data (typed). Returns list[Finding]."""
    on = set(ALL_RULES if enabled is None else enabled)
    out = []
    add = lambda r, t, k, s, d="": out.append(Finding(r, t, k, s, d)) if r in on else None
    menu = {m["item_id"]: m for m in st["menu_items"]}
    locs = set(st["locations"])

    for m in st["menu_items"]:
        bad = [i for i in m["ingredients"] if FORBIDDEN_RE.search(i)]
        if bad:
            add("forbidden_protein", "menu_items", m["item_id"], BLOCKER, ",".join(bad))

    lines_by = defaultdict(list)
    for l in st["order_lines"]:
        lines_by[l["order_id"]].append(l)
        if l["item_id"] not in menu:
            add("orphan_item", "order_lines", f'{l["order_id"]}:{l["line_no"]}', ERROR, l["item_id"])
            continue
        if l["qty"] <= 0:
            add("nonpositive_qty", "order_lines", f'{l["order_id"]}:{l["line_no"]}', ERROR, str(l["qty"]))
        base = menu[l["item_id"]]["price_cents"]
        if base and abs(l["unit_price_cents"] - base) / base > PRICE_TOLERANCE:
            add("price_drift", "order_lines", f'{l["order_id"]}:{l["line_no"]}', WARN, f'{l["unit_price_cents"]} vs {base}')

    seen, sig_seen = set(), {}
    for o in sorted(st["orders"], key=lambda r: r["order_id"]):
        oid = o["order_id"]
        if oid in seen:
            add("duplicate_order", "orders", oid, ERROR)
            continue
        seen.add(oid)
        if o["location_id"] not in locs:
            add("missing_location", "orders", oid, ERROR, repr(o["location_id"]))
        if o["ts"] > AS_OF:
            add("future_timestamp", "orders", oid, ERROR, o["ts"].isoformat())
        ls = lines_by.get(oid, [])
        if ls and sum(l["qty"] * l["unit_price_cents"] for l in ls) != o["total_cents"]:
            add("order_total_mismatch", "orders", oid, ERROR, f'{o["total_cents"]}')
        sig = (o["location_id"], o["ts"], tuple(sorted((l["item_id"], l["qty"], l["unit_price_cents"]) for l in ls)))
        if ls and sig in sig_seen:
            add("near_duplicate_order", "orders", oid, ERROR, f"same as {sig_seen[sig]}")
        else:
            sig_seen.setdefault(sig, oid)

    for r in st["inventory_counts"]:
        exp = INGREDIENT_UNIT.get(r["ingredient"])
        if exp and r["unit"] != exp:
            add("unit_mismatch", "inventory_counts", f'{r["location_id"]}:{r["count_date"]}:{r["ingredient"]}', ERROR, r["unit"])
    return out
