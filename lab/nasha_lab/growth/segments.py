"""Customer segmentation (capability 1) from the SYNTHETIC order history: recency / frequency / monetary (RFM) rules over loyalty members. Segment definitions are transparent rules, not a learned model;
evidence_basis is always 'synthetic_data_derived' and confidence is a documented function of segment size. Nothing here is a statement about real customers."""
import sqlite3
from datetime import date

RULES = [  # evaluated in order; first match wins
    ("champions", "recent (<=30d), 5+ orders, top-quartile spend"), ("loyal", "5+ orders, any recency within 60d"), ("new", "1-2 orders, first order within 30d"),
    ("at_risk", "3+ orders but last order 61-120d ago"), ("lapsed", "last order more than 120d ago"), ("occasional", "everyone else")]
CONF_K = 100          # confidence = n / (n + CONF_K): a documented heuristic that grows with sample size, never reaching 1


def member_rfm(wh_path):
    """member_id -> dict(orders, spend_cents, last_order_date). Computed from fact_order joined to dim_member."""
    con = sqlite3.connect(f"file:{wh_path}?mode=ro", uri=True)
    rows = con.execute("SELECT m.member_id, count(*), sum(o.total_cents), max(d.date) FROM fact_order o JOIN dim_member m USING(member_key) JOIN dim_date d USING(date_key) GROUP BY m.member_id").fetchall()
    ref = con.execute("SELECT max(date) FROM dim_date WHERE date_key IN (SELECT date_key FROM fact_order)").fetchone()[0]
    con.close()
    return {r[0]: dict(orders=r[1], spend_cents=r[2], last=r[3]) for r in rows}, ref


def classify(m, ref_date, spend_q75):
    days = (date.fromisoformat(ref_date) - date.fromisoformat(m["last"])).days
    n = m["orders"]
    if days <= 30 and n >= 5 and m["spend_cents"] >= spend_q75:
        return "champions"
    if n >= 5 and days <= 60:
        return "loyal"
    if n <= 2 and days <= 30:
        return "new"
    if n >= 3 and 61 <= days <= 120:
        return "at_risk"
    if days > 120:
        return "lapsed"
    return "occasional"


def segment(wh_path):
    members, ref = member_rfm(wh_path)
    spends = sorted(m["spend_cents"] for m in members.values())
    q75 = spends[int(0.75 * (len(spends) - 1))] if spends else 0
    seg = {mid: classify(m, ref, q75) for mid, m in members.items()}
    out = {}
    for name, _ in RULES:
        ids = [m for m, s in seg.items() if s == name]
        n = len(ids)
        out[name] = dict(n=n, est_value_cents=sum(members[m]["spend_cents"] for m in ids), confidence=n / (n + CONF_K) if n else 0.0,
                         criteria=dict(rule=dict(RULES)[name], reference_date=ref, spend_q75_cents=q75))
    return out, seg
