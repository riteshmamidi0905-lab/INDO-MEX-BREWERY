"""Product analytics over the warehouse: loyalty funnel, cohort retention, RFM segmentation, purchase frequency, concept-SKU adoption and
promotion analysis. SYNTHETIC. Every function reads the warehouse only (never the source CSVs) and refuses to run unless the pipeline's
last status is 'published'."""
import numpy as np
import pandas as pd


class NotPublished(RuntimeError):
    pass


def _require_published(con):
    r = con.execute("SELECT status FROM warehouse_status").fetchone() if con.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_status'").fetchone() else None
    if not r or r[0] != "published":
        raise NotPublished("warehouse is not published: quality gates have not passed")


def loyalty_funnel(con):
    """Members -> placed a first order -> first order within 30 days of joining -> a second order within 60 days of the first."""
    _require_published(con)
    df = pd.read_sql_query("""WITH o AS (SELECT f.member_key, d.date AS dte, ROW_NUMBER() OVER (PARTITION BY f.member_key ORDER BY f.order_id) AS rn FROM fact_order f JOIN dim_date d ON d.date_key=f.date_key WHERE f.member_key IS NOT NULL),
        a AS (SELECT member_key, max(CASE WHEN rn=1 THEN dte END) first_d, max(CASE WHEN rn=2 THEN dte END) second_d FROM o GROUP BY 1)
        SELECT m.member_key, m.join_date, m.cohort_month, a.first_d, a.second_d FROM dim_member m LEFT JOIN a ON a.member_key = m.member_key""", con)
    j, f, s = (pd.to_datetime(df[c]) for c in ("join_date", "first_d", "second_d"))
    last = pd.to_datetime(con.execute("SELECT max(date) FROM dim_date").fetchone()[0])
    eligible = df[(j + pd.Timedelta(days=30) <= last)]                          # only members old enough to have had 30 days
    ej, ef = j.loc[eligible.index], f.loc[eligible.index]
    first30 = ((ef - ej).dt.days <= 30) & ef.notna()
    elig2 = eligible[first30.reindex(eligible.index).fillna(False)]
    second60 = ((s.loc[elig2.index] - f.loc[elig2.index]).dt.days <= 60) & s.loc[elig2.index].notna()
    elig2b = elig2[(f.loc[elig2.index] + pd.Timedelta(days=60) <= last)]
    sec_ok = ((s.loc[elig2b.index] - f.loc[elig2b.index]).dt.days <= 60) & s.loc[elig2b.index].notna()
    return {"members": int(len(df)), "ever_ordered": int(f.notna().sum()), "members_with_30_days_of_history": int(len(eligible)),
            "first_order_within_30d": int(first30.sum()), "first_order_within_30d_rate": round(float(first30.mean()), 4),
            "second_order_within_60d_of_first (eligible only)": int(sec_ok.sum()), "second_order_rate": round(float(sec_ok.mean()), 4) if len(sec_ok) else None,
            "note": "Only members with enough elapsed time are counted in each stage (right-censoring handled by eligibility)."}


def cohort_matrix(con):
    _require_published(con)
    df = pd.read_sql_query("SELECT cohort_month, month, cohort_size, active_members, retention FROM mart_loyalty_cohort", con)
    df["age"] = (pd.to_datetime(df.month + "-01").dt.year - pd.to_datetime(df.cohort_month + "-01").dt.year) * 12 + (pd.to_datetime(df.month + "-01").dt.month - pd.to_datetime(df.cohort_month + "-01").dt.month)
    return df.pivot(index="cohort_month", columns="age", values="retention")


def rfm_segments(con):
    """Recency/frequency/monetary tertile scores and simple named segments. Segments describe behaviour in the data; they are not predictions."""
    _require_published(con)
    last = pd.to_datetime(con.execute("SELECT max(date) FROM dim_date").fetchone()[0])
    df = pd.read_sql_query("""SELECT f.member_key, max(d.date) AS last_d, count(*) AS frequency, sum(f.total_cents) AS monetary FROM fact_order f JOIN dim_date d ON d.date_key=f.date_key
                              WHERE f.member_key IS NOT NULL GROUP BY 1""", con)
    df["recency_days"] = (last - pd.to_datetime(df.last_d)).dt.days
    df["R"] = pd.qcut(df.recency_days.rank(method="first", ascending=False), 3, labels=[1, 2, 3]).astype(int)
    df["F"] = pd.qcut(df.frequency.rank(method="first"), 3, labels=[1, 2, 3]).astype(int)
    df["M"] = pd.qcut(df.monetary.rank(method="first"), 3, labels=[1, 2, 3]).astype(int)

    def name(r):
        if r.R == 3 and r.F == 3:
            return "champions (recent, frequent)"
        if r.R == 1 and r.F >= 2:
            return "at risk (lapsed but were frequent)"
        if r.R == 1:
            return "lapsed"
        if r.F == 1:
            return "new or occasional"
        return "steady"
    df["segment"] = df.apply(name, axis=1)
    g = df.groupby("segment").agg(members=("member_key", "count"), avg_orders=("frequency", "mean"), avg_spend_cents=("monetary", "mean"), avg_recency_days=("recency_days", "mean")).round(1)
    return df, g.sort_values("members", ascending=False)


def purchase_frequency(con):
    _require_published(con)
    df = pd.read_sql_query("SELECT member_key, count(*) n FROM fact_order WHERE member_key IS NOT NULL GROUP BY 1", con)
    bins = pd.cut(df.n, [0, 1, 2, 4, 8, 16, 10**6], labels=["1", "2", "3-4", "5-8", "9-16", "17+"])
    return bins.value_counts().sort_index().rename_axis("orders_per_member").reset_index(name="members").assign(share=lambda d: (d.members / d.members.sum()).round(4))


def concept_sku_adoption(con):
    """Concept SKUs (never brewed / never made) in SYNTHETIC sales: units, orders containing them, share of orders, share of member orders."""
    _require_published(con)
    return pd.read_sql_query("""SELECT p.item_id, p.name, count(DISTINCT f.order_id) AS orders_containing, sum(f.qty) AS units, round(100.0*count(DISTINCT f.order_id)/(SELECT count(*) FROM fact_order), 2) AS pct_of_all_orders,
        round(100.0*count(DISTINCT CASE WHEN o.member_key IS NOT NULL THEN f.order_id END)/(SELECT count(*) FROM fact_order WHERE member_key IS NOT NULL), 2) AS pct_of_member_orders
        FROM fact_order_line f JOIN dim_product p ON p.product_key=f.product_key JOIN fact_order o ON o.order_id=f.order_id WHERE p.is_concept_sku=1 GROUP BY 1,2 ORDER BY units DESC""", con)


def promotion_analysis(con):
    """Within each promotion window, loyalty orders that received the promo vs loyalty orders that did not (the simulator assigns the promo at random,
    so the comparison is unconfounded by construction). The simulator models NO behavioural response to promotions, so a null lift in ticket is the
    expected, honest result; what is real is the discount cost."""
    _require_published(con)
    from .experiments import welch
    out = []
    for pid, name, s, e in con.execute("SELECT promo_id, name, start_date, end_date FROM dim_promotion ORDER BY 1").fetchall():
        df = pd.read_sql_query("""SELECT f.promo_key IS NOT NULL AS treated, f.subtotal_cents, f.discount_cents, f.total_cents FROM fact_order f JOIN dim_date d ON d.date_key=f.date_key
                                  WHERE f.member_key IS NOT NULL AND d.date BETWEEN ? AND ?""", con, params=(s, e))
        if df.treated.sum() < 30 or (~df.treated.astype(bool)).sum() < 30:
            out.append({"promo": pid, "name": name, "note": "too few orders in the window (not analysed)"})
            continue
        t, c = df[df.treated == 1], df[df.treated == 0]
        g = welch(t.subtotal_cents, c.subtotal_cents)
        out.append({"promo": pid, "name": name, "treated_orders": int(len(t)), "control_orders": int(len(c)), "gross_ticket_diff_cents": round(g["diff"], 1),
                    "ci95_cents": [round(g["ci"][0], 1), round(g["ci"][1], 1)], "p": round(g["p"], 3), "discount_given_cents": int(t.discount_cents.sum()),
                    "net_revenue_per_order_diff_cents": round(float(t.total_cents.mean() - c.total_cents.mean()), 1),
                    "verdict": "no detectable lift in basket size; the discount is pure cost" if g["p"] >= 0.05 else "basket-size difference detected"})
    return out
