"""Data contracts for the simulator's source tables. A contract is the agreement between producer and warehouse:
columns and types, nullability, keys, accepted values and row-level rules. Structural breaks fail the load; row-level violations are
quarantined with a reason (and the quarantine rate is a blocking quality gate)."""
import pandas as pd

CHANNELS = ["dine-in", "bar", "takeout", "app"]
CONTRACTS = {
    "locations": {"cols": {"location_id": "str", "name": "str", "format": "str", "size_factor": "float", "sells_merch": "int", "capacity_orders_per_hour": "int", "open_date": "str"},
                  "key": ["location_id"], "accepted": {"format": ["fast casual", "beer garden"]}, "partition": None},
    "menu_items": {"cols": {"item_id": "str", "name": "str", "category": "str", "price_cents": "int", "ingredients": "str?", "status": "str"},
                   "key": ["item_id"], "accepted": {"category": ["food", "beer", "na", "merch"]}, "partition": None},
    "suppliers": {"cols": {"supplier_id": "str", "name": "str", "category": "str"}, "key": ["supplier_id"], "accepted": {}, "partition": None},
    "promotions": {"cols": {"promo_id": "str", "name": "str", "start_date": "str", "end_date": "str", "discount_fraction": "float"}, "key": ["promo_id"], "accepted": {}, "partition": None},
    "loyalty_profiles": {"cols": {"member_id": "str", "join_date": "str", "home_location_id": "str", "signup_channel": "str"}, "key": ["member_id"],
                         "accepted": {"signup_channel": ["in-store", "app", "event"]}, "partition": None},
    "employees": {"cols": {"employee_id": "str", "location_id": "str", "role": "str", "hire_date": "str", "hourly_rate_cents_placeholder": "int"}, "key": ["employee_id"], "accepted": {}, "partition": None},
    "orders": {"cols": {"order_id": "str", "location_id": "str", "ts": "str", "channel": "str", "member_id": "str?", "promo_id": "str?", "subtotal_cents": "int", "discount_cents": "int", "total_cents": "int"},
               "key": ["order_id"], "accepted": {"channel": CHANNELS}, "rules": ["subtotal_cents >= 0", "discount_cents >= 0", "total_cents == subtotal_cents - discount_cents"], "partition": "ts"},
    "order_lines": {"cols": {"order_id": "str", "line_no": "int", "item_id": "str", "qty": "int", "unit_price_cents": "int"}, "key": ["order_id", "line_no"], "accepted": {},
                    "rules": ["qty > 0", "unit_price_cents > 0"], "partition": "order_id"},
    "returns": {"cols": {"order_id": "str", "line_no": "int", "return_reason": "str", "refund_cents": "int"}, "key": ["order_id", "line_no"], "accepted": {}, "rules": ["refund_cents > 0"], "partition": "order_id"},
    "inventory_counts": {"cols": {"location_id": "str", "count_date": "str", "ingredient": "str", "qty": "float", "unit": "str"}, "key": ["location_id", "count_date", "ingredient"], "accepted": {"unit": ["kg"]},
                         "rules": ["qty >= 0"], "partition": "count_date"},
    "waste_events": {"cols": {"date": "str", "location_id": "str", "ingredient": "str", "qty_kg": "float", "reason": "str"}, "key": None, "accepted": {}, "rules": ["qty_kg > 0"], "partition": "date"},
    "quality_events": {"cols": {"date": "str", "location_id": "str", "event_type": "str", "severity": "str"}, "key": None, "accepted": {"severity": ["low", "medium", "high"]}, "partition": "date"},
    "shifts": {"cols": {"date": "str", "location_id": "str", "scheduled_labor_hours": "int", "actual_labor_hours": "int"}, "key": ["date", "location_id"], "accepted": {}, "rules": ["actual_labor_hours >= 0"], "partition": "date"},
    "brew_batches": {"cols": {"batch_id": "str", "location_id": "str", "brew_date": "str", "beer_id": "str", "planned_liters": "float", "yield_liters": "float", "status": "str"}, "key": ["batch_id"], "accepted": {},
                     "rules": ["planned_liters > 0", "yield_liters > 0"], "partition": "brew_date"},
}
SQL_TYPE = {"str": "TEXT", "int": "INTEGER", "float": "REAL"}


class ContractError(Exception):
    """Structural contract break (missing/extra column): the whole file is rejected."""


def check_chunk(table, df):
    """Return (clean_df, quarantine_rows[(key, reason)]). Raises ContractError on a structural break."""
    c = CONTRACTS[table]
    cols = list(c["cols"])
    if list(df.columns) != cols:
        raise ContractError(f"{table}: columns {list(df.columns)} differ from the contract {cols}")
    df = df.copy()
    bad = pd.Series("", index=df.index)

    def flag(mask, reason):
        nonlocal bad
        m = mask & (bad == "")
        bad = bad.mask(m, reason)

    for col, t in c["cols"].items():
        optional = t.endswith("?")
        base = t.rstrip("?")
        if base in ("int", "float"):
            num = pd.to_numeric(df[col], errors="coerce")
            flag(num.isna(), f"{col} is not a number")
            df[col] = num
        else:
            df[col] = df[col].astype("object").where(df[col].notna(), None)
            if optional:
                df[col] = df[col].where(df[col] != "", None)
            if not optional:
                flag(df[col].isna() | (df[col].astype(str) == ""), f"{col} is empty")
    for col, ok in c["accepted"].items():
        flag(~df[col].isin(ok), f"{col} has a value outside the accepted list")
    for rule in c.get("rules", []):
        try:
            ok = df.eval(rule)
        except Exception:
            continue
        flag(~ok.fillna(False), f"rule failed: {rule}")
    key = c["key"]
    q = []
    if (bad != "").any():
        for idx in df.index[bad != ""]:
            q.append(("|".join(str(df.at[idx, k]) for k in key) if key else str(idx), bad[idx]))
    clean = df[bad == ""].copy()
    for col, t in c["cols"].items():
        if t.rstrip("?") == "int":
            clean[col] = clean[col].astype("int64")
    return clean, q
