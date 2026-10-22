import argparse
import json
import sys

from . import monitor, pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nasha_lab.warehouse", description="Synthetic enterprise warehouse pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--source", required=True); r.add_argument("--db", required=True); r.add_argument("--through"); r.add_argument("--full", action="store_true")
    m = sub.add_parser("monitor"); m.add_argument("--db", required=True)
    l = sub.add_parser("lineage"); l.add_argument("--db", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        out = pipeline.run(a.source, a.db, through=a.through, force_full=a.full)
        print(json.dumps(out, indent=1, default=str))
        return 0 if out["status"] == "published" else 1
    if a.cmd == "monitor":
        print(json.dumps(monitor.report(a.db), indent=1, default=str))
        return 0
    print(monitor.lineage_markdown(a.db))
    return 0


if __name__ == "__main__":
    sys.exit(main())
