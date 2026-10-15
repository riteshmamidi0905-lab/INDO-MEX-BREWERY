"""CLI: python -m nasha_lab.run --seed 1 --defects 8 --out lab_out   (writes raw CSVs, a SQLite model and a text report)."""
import argparse
import os
import sys

from . import generator, pipeline


def main(argv=None):
    a = argparse.ArgumentParser(description="SYNTHETIC NASHA operations data platform run")
    a.add_argument("--seed", type=int, default=1)
    a.add_argument("--defects", type=int, default=8, help="injected defects per type; 0 = clean dataset")
    a.add_argument("--out", default="lab_out")
    n = a.parse_args(argv)
    raw, truth = generator.generate(n.seed, n.defects)
    pipeline.write_raw(raw, os.path.join(n.out, "raw"))
    db = os.path.join(n.out, "nasha_model.sqlite")
    if os.path.exists(db): os.remove(db)
    con, rep = pipeline.run(raw, db)
    print("SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED")
    for t, (r, m, q) in rep["lineage"].items():
        print(f"{t:18s} raw={r:6d} modeled={m:6d} quarantined={q:4d}")
    print("findings:", len(rep["findings"]), "| publish gate:", rep["gate"])
    return 0 if rep["gate"] == "PASSED" else 3


if __name__ == "__main__":
    sys.exit(main())
