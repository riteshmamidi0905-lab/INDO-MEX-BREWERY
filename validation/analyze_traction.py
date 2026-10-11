#!/usr/bin/env python3
"""Analyse validation/traction-event-log.csv. Only rows with data_source == 'real' feed the metrics; 'dry_run' rows are counted separately.
Usage: python3 validation/analyze_traction.py [csv]   |   --selftest (synthetic rows in a temp dir; never writes to the repo and is never evidence)"""
import csv, os, sys, tempfile, random, statistics as st
HERE=os.path.dirname(os.path.abspath(__file__)); DEF=os.path.join(HERE,"traction-event-log.csv")
def f(x):
    try: return float(str(x).strip())
    except Exception: return None
def s(rows,k): v=[f(r[k]) for r in rows if f(r[k]) is not None]; return sum(v) if v else None
def run(path):
    rows=list(csv.DictReader(open(path))); rows=[r for r in rows if any((v or '').strip() for v in r.values())]
    real=[r for r in rows if (r.get("data_source","").strip().lower()=="real")]; dry=[r for r in rows if r.get("data_source","").strip().lower()=="dry_run"]
    other=len(rows)-len(real)-len(dry)
    print(f"sessions: real={len(real)} dry_run={len(dry)} unlabelled/other={other}")
    if other: print("WARNING: rows without data_source real/dry_run are ignored; fix them")
    if not real: print("No real sessions yet: no metrics to report."); return
    if len(real)<5: print("NOTE: fewer than 5 real sessions; treat every metric as anecdotal")
    cust=s(real,"customers_served"); orders=s(real,"orders"); rev=s(real,"net_revenue_usd"); units=s(real,"units_sold"); veg=s(real,"vegetarian_units"); cogs=s(real,"cogs_total_usd"); lab=s(real,"labor_hours")
    print("customers",cust,"| orders",orders,"| revenue",rev)
    if orders and rev is not None: print("average order value",round(rev/orders,2))
    if orders and units is not None: print("items per order",round(units/orders,2))
    if units and veg is not None: print("vegetarian mix (units)",f"{100*veg/units:.0f}%")
    if rev and cogs is not None: print("gross margin",f"{100*(rev-cogs)/rev:.0f}%")
    if orders and lab is not None: print("labour hours per order",round(lab/orders,3))
    t=[f(r["median_ticket_time_min"]) for r in real if f(r["median_ticket_time_min"]) is not None]
    if t: print("median of session median ticket times (min)",round(st.median(t),1))
    so=sum(1 for r in real if (r["items_sold_out"] or "").strip()); print("sessions with a sell-out",f"{so}/{len(real)}")
    p,pa,d=s(real,"recommend_promoters"),s(real,"recommend_passives"),s(real,"recommend_detractors")
    if None not in (p,pa,d) and (p+pa+d)>0: n=p+pa+d; print(f"NPS = {100*(p-d)/n:.0f} (n={int(n)}; noisy if small)")
    print("email signups",s(real,"email_signups"),"| QR scans",s(real,"qr_scans"),"| flagship interest",s(real,"flagship_interest_count"))
def selftest():
    random.seed(2); d=tempfile.mkdtemp(); p=os.path.join(d,"t.csv"); hdr=open(DEF).readline().strip().split(",")
    fh=open(p,"w",newline=""); w=csv.DictWriter(fh,fieldnames=hdr); w.writeheader()
    for i in range(6):
        r={k:"" for k in hdr}; r.update(session_id=i,customers_served=random.randint(20,50),orders=random.randint(15,40),net_revenue_usd=random.randint(300,700),units_sold=random.randint(30,80),vegetarian_units=random.randint(10,30),cogs_total_usd=random.randint(100,250),labor_hours=random.randint(6,12),median_ticket_time_min=random.randint(4,9),email_signups=random.randint(2,15),recommend_promoters=5,recommend_passives=3,recommend_detractors=1,data_source="real" if i else "dry_run"); w.writerow(r)
    fh.close(); print("[SELFTEST on SYNTHETIC data in",d,"- not evidence]"); run(p)
if __name__=="__main__":
    selftest() if "--selftest" in sys.argv else run(sys.argv[1] if len(sys.argv)>1 else DEF)
