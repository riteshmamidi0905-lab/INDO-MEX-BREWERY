"""SYNTHETIC supplier quotes for supplier-cost comparison and procurement recommendations.

There are NO real supplier quotes for NASHA. Every quote below is generated deterministically from the planning-assumption base price by a seeded factor and is
labelled price_class = SYNTHETIC_QUOTE with a fictional supplier id. They exist to exercise comparison, pack-size and lead-time logic, not to estimate real costs.
Real dated quotes, when they exist, must use price_class SUPPLIER_QUOTE with a document reference and are never mixed into synthetic results.
"""
import hashlib
import json
import math

from . import model

PRICING = model.ROOT / "food/pricing"
QUOTE_FILE = PRICING / "supplier-quotes.synthetic.v1.json"
PRICE_CLASSES = ("PLANNING_ASSUMPTION", "SYNTHETIC_QUOTE", "PUBLIC_REFERENCE", "SUPPLIER_QUOTE")
SUPPLIERS = [   # id, name, kind. S01-S05 are the simulation's own category suppliers; FS* are synthetic broadline/specialist additions (all fictional)
    ("S01", "Synthetic Supplier 01", "poultry"), ("S02", "Synthetic Supplier 02", "goat and lamb"), ("S03", "Synthetic Supplier 03", "produce"),
    ("S04", "Synthetic Supplier 04", "dairy"), ("S05", "Synthetic Supplier 05", "dry goods"),
    ("FS01", "Synthetic Broadline Distributor A", "broadline"), ("FS02", "Synthetic Broadline Distributor B", "broadline"), ("FS03", "Synthetic Specialty Importer", "specialty")]
PRIMARY = {"protein": "S01", "produce": "S03", "aromatic": "S03", "herb": "S03", "dairy": "S04", "grain": "S05", "pantry": "S05", "spice": "S05", "oil": "S05"}
PACK = {"kg": 5.0, "l": 4.0, "each": 60.0}
SPICE_PACK = 1.0


def _factor(seed, ing, sup):
    h = hashlib.sha256(f"{seed}|{ing}|{sup}".encode()).digest()
    return 0.93 + (int.from_bytes(h[:4], "big") / 2 ** 32) * 0.17            # 0.93 .. 1.10


def primary_for(ing):
    if ing["id"] in ("i-goat-bone-in", "i-lamb-leg"):
        return "S02"
    if ing["id"] in ("i-white-fish", "i-saffron"):
        return "FS03"
    return PRIMARY[ing["category"]]


def generate(master=None, seed=87):
    master = master or model.load_master()
    out = []
    for ing in master.values():
        if ing.get("derived_from"):
            continue
        sups = [primary_for(ing), "FS01", "FS02"]
        for s in dict.fromkeys(sups):
            f = _factor(seed, ing["id"], s)
            pack = SPICE_PACK if ing["category"] == "spice" else PACK[ing["unit"]]
            out.append({"quote_id": f"Q-{s}-{ing['id'][2:]}", "supplier_id": s, "ingredient_id": ing["id"], "unit": ing["unit"], "unit_price": round(ing["price"]["base"] * f, 4),
                        "pack_qty": pack, "lead_days": 1 + int(hashlib.sha256(f"L{ing['id']}{s}".encode()).digest()[0] % 4), "min_order_usd": 0 if s.startswith("S") else 150,
                        "valid_from": "2026-10-22", "valid_to": "2026-11-21", "price_class": "SYNTHETIC_QUOTE", "source": "generated: seeded factor on planning-assumption base price; NOT a supplier document"})
    return {"version": "synthetic-quotes-v1", "seed": seed, "status": "SYNTHETIC — no real supplier quote exists", "suppliers": [{"supplier_id": a, "name": b, "kind": c, "synthetic": True} for a, b, c in SUPPLIERS],
            "quotes": out}


def load():
    return json.loads(QUOTE_FILE.read_text())


def compare(quotes, ingredient_id, need_qty, on=None):
    """Rank suppliers for a need: cost = whole packs x pack price (you cannot buy less than a pack), then lead time. Returns list best-first."""
    rows = []
    for q in quotes:
        if q["ingredient_id"] != ingredient_id:
            continue
        if on and not (q["valid_from"] <= on <= q["valid_to"]):
            continue
        packs = max(1, math.ceil(need_qty / q["pack_qty"] - 1e-9))
        buy = packs * q["pack_qty"]
        rows.append({"supplier_id": q["supplier_id"], "quote_id": q["quote_id"], "buy_qty": buy, "unit_price": q["unit_price"], "cost": round(buy * q["unit_price"], 2),
                     "effective_unit_cost": round(buy * q["unit_price"] / need_qty, 4) if need_qty else None, "lead_days": q["lead_days"], "price_class": q["price_class"]})
    return sorted(rows, key=lambda r: (r["cost"], r["lead_days"], r["supplier_id"]))


def write():
    QUOTE_FILE.write_text(json.dumps(generate(), indent=1) + "\n")


if __name__ == "__main__":
    write()
    print("written", QUOTE_FILE)
