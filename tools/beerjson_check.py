#!/usr/bin/env python3
"""Validate a BeerJSON file against the vendored official schema (Sprint 15). Structure check only: a valid file is NOT a production recipe, NOT a
brewer-approved formulation, and NASHA has no recipe (beers are working names). Intended for the eventual qualified-brewer handoff.
  python3 tools/beerjson_check.py file.json
  python3 tools/beerjson_check.py selftest"""
import json, os, sys, glob
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "beerjson")
def validator():
    reg = Registry()
    for p in glob.glob(f"{D}/*.json"):
        s = json.load(open(p)); reg = reg.with_resource(s.get("$id", "file://" + p), Resource.from_contents(s))
        reg = reg.with_resource("https://raw.githubusercontent.com/beerjson/beerjson/main/json/" + os.path.basename(p), Resource.from_contents(s))
    return Draft202012Validator(json.load(open(f"{D}/beer.json")), registry=reg)
def check(doc): return sorted(f"{'/'.join(map(str, e.path))}: {e.message[:140]}" for e in validator().iter_errors(doc))
def selftest():
    good = {"beerjson": {"version": 2.06, "recipes": [{"name": "TEST ONLY", "type": "all grain", "author": "selftest", "batch_size": {"value": 20, "unit": "l"}, "efficiency": {"brewhouse": {"value": 70, "unit": "%"}}, "ingredients": {"fermentable_additions": [{"name": "t", "type": "grain", "amount": {"value": 4, "unit": "kg"}, "yield": {"fine_grind": {"value": 80, "unit": "%"}}, "color": {"value": 2, "unit": "SRM"}}]}}]}}
    e = check(good); assert not e, e
    bad = json.loads(json.dumps(good)); bad["beerjson"]["recipes"][0]["batch_size"]["unit"] = "furlongs"; assert check(bad), "bad unit must fail"
    print("selftest ok: schema loads, valid doc passes, bad unit rejected")
if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]: selftest()
    elif len(sys.argv) == 2: e = check(json.load(open(sys.argv[1]))); print("VALID (structure only; not a recipe approval)" if not e else "\n".join(e)); sys.exit(1 if e else 0)
    else: print(__doc__)
