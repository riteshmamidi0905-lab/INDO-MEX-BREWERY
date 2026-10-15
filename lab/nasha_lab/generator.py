"""Deterministic synthetic NASHA operations data with INJECTED, LABELLED defects.

SYNTHETIC DATA / SIMULATED OPERATION. NASHA has no restaurant, customers, sales or brewery batches.
Prices are placeholder inputs, not NASHA pricing. The 'scenario calendar' is not real time.
Every injected defect is recorded in a ground-truth list so the data-quality checks can be scored.
"""
import datetime as dt
import random

AS_OF = dt.datetime(2026, 5, 1, 0, 0, 0)          # scenario as-of: timestamps after this are 'future'
START = dt.date(2026, 3, 2)
DAYS = 56
LOCATIONS = [  # three SCENARIO sites, not real or planned locations
    ("L01", "Scenario Site A (synthetic)", 1.0),
    ("L02", "Scenario Site B (synthetic)", 0.7),
    ("L03", "Scenario Site C (synthetic)", 0.5),
]
# item_id, name, category, price_cents (PLACEHOLDER), ingredients
MENU = [
    ("M01", "Chicken 65 Totopos", "food", 1400, "chicken thigh;curry leaf;corn masa;crema;chile"),
    ("M02", "Paneer Tikka Taco", "food", 1300, "paneer;corn masa;onion;cilantro"),
    ("M03", "Goat Birria", "food", 1600, "goat;chile;corn masa;onion"),
    ("M04", "Gobi Taco", "food", 1200, "cauliflower;corn masa;chutney"),
    ("M05", "Butter Chicken Quesadilla", "food", 1500, "chicken thigh;poblano;cheese;corn masa"),
    ("B01", "Signature Hefe", "beer", 800, "water;malt;hops;yeast"),
    ("B02", "Lager", "beer", 700, "water;malt;hops;yeast"),
    ("B03", "Amber", "beer", 800, "water;malt;hops;yeast"),
    ("N01", "Lime zero-proof", "na", 500, "lime;water;sugar"),
    ("N02", "Tamarind zero-proof", "na", 550, "tamarind;water;sugar"),
]
# MENU VERSIONS. v1 is the Block 3 (frozen, historical) menu master and stays the DEFAULT so every frozen benchmark reproduces byte for byte.
# v2 is the CURRENT founder direction (decision D-84): item M04 is MANGO HABANERO GOBI, an appetizer / shareable, NOT a taco, no tortilla.
# Prices are placeholder inputs in both versions. Recipes are placeholder planning inputs (world.RECIPES / world.RECIPES_V2).
MENU_V2 = [(m[0], "Mango Habanero Gobi", "food", 1200, "cauliflower;mango;habanero") if m[0] == "M04" else m for m in MENU]
MENU_COURSE_V2 = {"M04": "appetizer / shareable"}
MENUS = {"v1": MENU, "v2": MENU_V2}
CURRENT_MENU_VERSION = "v2"
INGREDIENT_UNIT = {  # expected stock unit per ingredient
    "chicken thigh": "kg", "paneer": "kg", "goat": "kg", "cauliflower": "kg",
    "corn masa": "kg", "malt": "kg", "hops": "kg", "cheese": "kg",
}
DEFECT_TYPES = [
    "duplicate_order", "near_duplicate_order", "near_duplicate_shifted", "missing_location",
    "future_timestamp", "malformed_timestamp", "order_total_mismatch", "orphan_item",
    "nonpositive_qty", "price_drift", "forbidden_protein", "unit_mismatch",
]
FORBIDDEN_INJECT = ["pork lard", "beef stock", "bacon bits"]


def _ts(d, rng, weekend):
    hour = rng.choices(range(11, 23), weights=[3, 5, 4, 2, 2, 3, 5, 7, 8, 8 if weekend else 6, 5, 2])[0]
    return dt.datetime(d.year, d.month, d.day, hour, rng.randint(0, 59), rng.randint(0, 59))


def generate(seed=1, defects_per_type=8, types=None, menu_version="v1"):
    """Return (raw, truth). raw: dict of table -> list of dict (all values strings, as a CSV would be).
    truth: set of (defect_type, table, key). defects_per_type=0 gives the clean dataset."""
    rng = random.Random(seed)
    MENU_ = MENUS[menu_version]; menu = {m[0]: m for m in MENU_}
    orders, lines = [], []
    n = 0
    for k in range(DAYS):
        d = START + dt.timedelta(days=k)
        weekend = d.weekday() >= 4
        for loc, _name, factor in LOCATIONS:
            for _ in range(int(rng.randint(22, 38) * factor * (1.3 if weekend else 1))):
                n += 1
                oid = f"O{n:06d}"
                ts = _ts(d, rng, weekend)
                happy = 15 <= ts.hour < 17
                total = 0
                chosen = rng.sample(sorted(menu), rng.randint(1, 4))
                for ln, iid in enumerate(chosen, 1):
                    qty = rng.choices([1, 2, 3], weights=[6, 3, 1])[0]
                    price = menu[iid][3]
                    if happy and menu[iid][2] == "beer":
                        price = round(price * 0.9)       # legitimate happy-hour price, inside the drift tolerance
                    total += qty * price
                    lines.append({"order_id": oid, "line_no": str(ln), "item_id": iid, "qty": str(qty), "unit_price_cents": str(price)})
                orders.append({"order_id": oid, "location_id": loc, "ts": ts.isoformat(), "channel": rng.choice(["dine-in", "bar", "takeout"]), "total_cents": str(total)})
    inv = []
    for loc, _n, f in LOCATIONS:
        for w in range(9):
            d = START + dt.timedelta(days=7 * w)
            for ing, unit in INGREDIENT_UNIT.items():
                inv.append({"location_id": loc, "count_date": d.isoformat(), "ingredient": ing, "qty": f"{rng.uniform(2, 40) * f:.1f}", "unit": unit})
    menu_rows = [{"item_id": m[0], "name": m[1], "category": m[2], "price_cents": str(m[3]), "ingredients": m[4]} for m in MENUS[menu_version]]
    raw = {"menu_items": menu_rows, "orders": orders, "order_lines": lines, "inventory_counts": inv}
    truth = set()
    if defects_per_type:
        _inject(raw, truth, rng, defects_per_type, types or DEFECT_TYPES)
    return raw, truth


def _recompute(raw_lines_by_order, header):
    t = sum(int(l["qty"]) * int(l["unit_price_cents"]) for l in raw_lines_by_order[header["order_id"]])
    header["total_cents"] = str(t)


def _inject(raw, truth, rng, k, types):
    orders, lines = raw["orders"], raw["order_lines"]
    by_order = {}
    for l in lines:
        by_order.setdefault(l["order_id"], []).append(l)
    free = [o for o in orders]
    rng.shuffle(free)
    pop = lambda: free.pop()
    for t in types:
        for i in range(k):
            if t == "unit_mismatch":
                row = rng.choice([r for r in raw["inventory_counts"] if r["unit"] == "kg"])
                row["unit"] = "lb"
                truth.add((t, "inventory_counts", f'{row["location_id"]}:{row["count_date"]}:{row["ingredient"]}'))
            elif t == "forbidden_protein":
                if i >= len(FORBIDDEN_INJECT):
                    continue
                row = raw["menu_items"][[1, 3, 4][i % 3]] if i < 3 else None
                if row is None or "forbidden" in row.get("_mark", ""):
                    continue
                row["ingredients"] += ";" + FORBIDDEN_INJECT[i]
                row["_mark"] = "forbidden"
                truth.add((t, "menu_items", row["item_id"]))
            elif t in ("duplicate_order", "near_duplicate_order", "near_duplicate_shifted"):
                o = pop()
                if t == "duplicate_order":
                    orders.append(dict(o))
                    truth.add((t, "orders", o["order_id"]))
                else:
                    nid = f"O9{len(orders):05d}"
                    ts = dt.datetime.fromisoformat(o["ts"])
                    if t == "near_duplicate_shifted":
                        ts += dt.timedelta(seconds=1)
                    no = dict(o, order_id=nid, ts=ts.isoformat())
                    orders.append(no)
                    for l in by_order[o["order_id"]]:
                        lines.append(dict(l, order_id=nid))
                    truth.add((t, "orders", nid))
            elif t in ("orphan_item", "nonpositive_qty", "price_drift"):
                o = pop()
                l = rng.choice(by_order[o["order_id"]])
                key = f'{l["order_id"]}:{l["line_no"]}'
                if t == "orphan_item":
                    l["item_id"] = rng.choice(["M99", "X01", "B77"])
                elif t == "nonpositive_qty":
                    l["qty"] = rng.choice(["0", "-1"])
                else:
                    l["unit_price_cents"] = str(round(int(l["unit_price_cents"]) * rng.choice([1.45, 1.9, 0.5, 0.45])))
                _recompute(by_order, o)
                truth.add((t, "order_lines", key))
            else:
                o = pop()
                if t == "missing_location":
                    o["location_id"] = rng.choice(["", "L99"])
                elif t == "future_timestamp":
                    o["ts"] = (AS_OF + dt.timedelta(days=rng.randint(1, 30), seconds=rng.randint(0, 80000))).isoformat()
                elif t == "malformed_timestamp":
                    o["ts"] = rng.choice(["2026-13-45T99:99:00", "yesterday", "03/04/26 25:00"])
                elif t == "order_total_mismatch":
                    o["total_cents"] = str(int(o["total_cents"]) + rng.choice([-1, 1]) * rng.randint(50, 900))
                truth.add((t, "orders", o["order_id"]))
    for r in raw["menu_items"]:
        r.pop("_mark", None)
