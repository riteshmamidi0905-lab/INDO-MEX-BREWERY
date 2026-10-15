"""Paired comparison of two planner result files over the SAME scenarios: contingency table, exact two-sided sign test (McNemar's exact), per-family wins.
  python -m nasha_lab.compare_planners A.json B.json"""
import json
import sys
from math import comb


def sign_test(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); p = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def compare(a, b, key="pass"):
    ra = {r["id"]: r for r in a["rows"]}; rb = {r["id"]: r for r in b["rows"]}
    ids = sorted(set(ra) & set(rb)); both = only_a = only_b = neither = 0; fam = {}
    for i in ids:
        x, y = bool(ra[i][key]), bool(rb[i][key]); f = ra[i]["family"]; fam.setdefault(f, [0, 0])
        if x and y: both += 1
        elif x: only_a += 1; fam[f][0] += 1
        elif y: only_b += 1; fam[f][1] += 1
        else: neither += 1
    return dict(n=len(ids), both_pass=both, only_first=only_a, only_second=only_b, both_fail=neither, p_value_exact_sign_test=round(sign_test(only_a, only_b), 4),
                families_where_first_wins={f: v[0] for f, v in fam.items() if v[0]}, families_where_second_wins={f: v[1] for f, v in fam.items() if v[1]})


if __name__ == "__main__":
    a, b = (json.load(open(p)) for p in sys.argv[1:3]); print(json.dumps(compare(a, b), indent=1))
