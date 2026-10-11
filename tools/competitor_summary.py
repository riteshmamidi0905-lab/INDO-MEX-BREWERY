#!/usr/bin/env python3
"""Summarise ops/data/austin-yelp-observed.csv by group (Sprint 15). OBSERVED values only; nothing is inferred about revenue or share.
It is a SAMPLE of connector results (<=8 per query), not an Austin census, and Yelp ratings are user aggregates. python3 tools/competitor_summary.py"""
import csv, statistics as st, collections
rows = list(csv.DictReader(open("ops/data/austin-yelp-observed.csv", encoding="utf-8")))
def group(r):
    c = set(r["yelp_category_aliases"].split("|"))
    if c & {"indpak", "himalayan"}: return "Indian"
    if c & {"brewpubs"}: return "Brewpub"
    if c & {"breweries"}: return "Brewery"
    if c & {"beergardens"}: return "Beer garden"
    if c & {"mexican", "tacos", "newmexican", "tex-mex"}: return "Mexican"
    return "Other / fusion-ish"
G = collections.defaultdict(list)
for r in rows: G[group(r)].append(r)
print(f"{len(rows)} listings (sample)")
for g, rs in sorted(G.items()):
    rt = [float(x["rating_observed"]) for x in rs]; rc = [int(x["review_count_observed"]) for x in rs]; pr = collections.Counter(x["price_tier"] or "n/a" for x in rs)
    print(f"{g:18} n={len(rs):2} rating median {st.median(rt):.2f} (range {min(rt):.2f}-{max(rt):.2f}) | review count median {int(st.median(rc))} | price {dict(pr)}")
food = [r for r in rows if {"foodtrucks"} & set(r["yelp_category_aliases"].split("|"))]
print("food-truck-tagged listings:", [r["name"] for r in food])
print("listings tagged both a brewery/brewpub/beergarden category and a food/cuisine category:", sum(1 for r in rows if (set(r["yelp_category_aliases"].split("|")) & {"breweries","brewpubs","beergardens"}) and (set(r["yelp_category_aliases"].split("|")) & {"tacos","foodtrucks","sandwiches","burgers","tradamerican"})))
