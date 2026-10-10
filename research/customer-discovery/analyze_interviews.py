#!/usr/bin/env python3
"""Analyse customer-discovery responses. Reads research/customer-discovery/responses.csv (real data only).
Usage: python3 research/customer-discovery/analyze_interviews.py [responses.csv]     |   --selftest (uses synthetic rows in a temp dir; never writes to the repo)
Prints counts, medians, segment splits and the decision-rule checks from INTERVIEW-GUIDE.md section 5. Does not invent anything: empty cells are skipped."""
import csv, sys, os, statistics as st, tempfile, random
from collections import Counter, defaultdict
DEF=os.path.join(os.path.dirname(os.path.abspath(__file__)),"responses.csv")
def num(x):
    try: return float(str(x).replace("$","").strip())
    except Exception: return None
def med(v): v=[x for x in v if x is not None]; return round(st.median(v),2) if v else None
def pct(c,n): return f"{100*c/n:.0f}%" if n else "n/a"
def analyse(path):
    rows=list(csv.DictReader(open(path)))
    rows=[r for r in rows if any((v or '').strip() for k,v in r.items() if k!='id')]
    n=len(rows); print(f"n = {n} interviews (target 30)")
    if n==0: print("No responses yet."); return
    if n<30: print(f"WARNING: n<30; findings are exploratory only")
    seg=Counter(r["segment"] for r in rows if r["segment"]); print("segments:",dict(seg))
    def dist(col,label=None):
        c=Counter((r[col] or '').strip().lower() for r in rows if (r[col] or '').strip()); t=sum(c.values())
        print(f"{label or col}: "+", ".join(f"{k}={v} ({pct(v,t)})" for k,v in c.most_common()) if t else f"{label or col}: no data"); return c,t
    c1,t1=dist("concept_comprehension"); c2,t2=dist("first_reaction"); c3,t3=dist("no_beef_pork_reaction"); c4,t4=dist("goat_comfort"); c5,t5=dist("lamb_comfort"); c6,t6=dist("veg_full_meal")
    print("importance medians (1-5):",{k:med([num(r[k]) for r in rows]) for k in ["pairing_importance_1to5","imp_see_brewery_1to5","imp_shade_1to5","imp_kids_1to5","imp_music_1to5","imp_games_1to5","imp_shop_1to5"]})
    print("expected price medians ($):",{k:med([num(r[k]) for r in rows]) for k in ["exp_price_pint","exp_price_taco","exp_price_snack","exp_price_main","exp_price_kids"]})
    print("acceptable-range medians ($): pint",{k:med([num(r["pint_"+k]) for r in rows]) for k in ["too_cheap","bargain","getting_expensive","too_expensive"]},"main",{k:med([num(r["main_"+k]) for r in rows]) for k in ["too_cheap","bargain","getting_expensive","too_expensive"]})
    b=Counter(); 
    for r in rows:
        for k in ("barrier_1","barrier_2","barrier_3"):
            v=(r[k] or '').strip().lower()
            if v: b[v]+=1
    print("barriers (all mentions):",b.most_common(10))
    fm=[num(r["first_month_1to5"]) for r in rows]; mv=Counter((r["monthly_visits_after"] or '').strip() for r in rows if (r["monthly_visits_after"] or '').strip())
    print("first-month likelihood median:",med(fm),"| monthly visits after:",dict(mv))
    hi=[r for r in rows if (num(r["first_month_1to5"]) or 0)>=4]; lo=[r for r in hi if (r["monthly_visits_after"] or '').strip() in ("0","1")]
    print(f"high first-month interest but <=1 monthly visit: {len(lo)} of {len(hi)}")
    print("substitutes named:",Counter((r["substitute_named"] or '').strip().lower() for r in rows if (r["substitute_named"] or '').strip()).most_common(8))
    by=defaultdict(list)
    for r in rows: by[r["segment"]].append(r)
    print("first-reaction by segment:",{s:dict(Counter((r["first_reaction"] or '').strip().lower() for r in v if r["first_reaction"])) for s,v in by.items()})
    print("\nDECISION-RULE CHECKS (INTERVIEW-GUIDE section 5):")
    def flag(label,cond,txt): print(("  FLAG  " if cond else "  ok    ")+label+("  -> "+txt if cond else ""))
    wrong=c1.get("wrong",0)+c1.get("partly",0)+c2.get("confused",0)
    flag("concept comprehension not accurate/confused > 30%",t1>0 and (c1.get("wrong",0)+c2.get("confused",0))/max(n,1)>0.30,"rewrite the concept explanation")
    flag("'no beef/pork' lowers interest > 25%",t3>0 and c3.get("less",0)/t3>0.25,"examine segments, messaging, menu appeal")
    flag("goat/lamb 'never would' > 40%",t4>0 and (c4.get("never would",0)/t4>0.40 or (t5>0 and c5.get("never would",0)/t5>0.40)),"raise chicken/veg/fish share; revisit prominence")
    top=b.most_common(1)
    flag("top barrier named by >= 8",bool(top) and top[0][1]>=8,"treat as design requirement or kill criterion: "+(top[0][0] if top else ""))
    flag("high interest but low repeat",len(hi)>0 and len(lo)/len(hi)>0.5,"curiosity, not repeat demand")
    vs=[r for r in rows if "veg" in (r["segment"] or "").lower()]; vy=sum(1 for r in vs if (r["veg_full_meal"] or '').strip().lower()=="yes")
    flag("vegetarian full-meal 'yes' < half",len(vs)>0 and vy/len(vs)<0.5,"strengthen the vegetarian pillar")
    print("\nReport n honestly; 30 interviews find problems, they do not give precision.")
def selftest():
    random.seed(1); d=tempfile.mkdtemp(); p=os.path.join(d,"responses.csv")
    hdr=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"responses-schema.csv")).read().strip().split(",")
    fh=open(p,"w",newline=""); w=csv.DictWriter(fh,fieldnames=hdr); w.writeheader()
    for i in range(12):
        r={k:"" for k in hdr}; r.update(id=i+1,segment=random.choice(["craft","parent","vegetarian"]),concept_comprehension=random.choice(["accurate","partly","wrong"]),first_reaction=random.choice(["positive","neutral","confused"]),no_beef_pork_reaction=random.choice(["more","none","less"]),goat_comfort=random.choice(["would order","never would"]),first_month_1to5=random.randint(1,5),monthly_visits_after=random.choice(["0","1","2"]),barrier_1=random.choice(["heat","price","parking"]),exp_price_pint=random.choice(["7","8","9"]),veg_full_meal=random.choice(["yes","no"]))
        w.writerow(r)
    fh.close()
    print("[SELFTEST on synthetic data in",d,"- not real results]"); analyse(p)
if __name__=="__main__":
    if "--selftest" in sys.argv: selftest()
    else: analyse(sys.argv[1] if len(sys.argv)>1 else DEF)
