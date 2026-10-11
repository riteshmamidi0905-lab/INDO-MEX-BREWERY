#!/usr/bin/env python3
"""Random 3-digit plate codes for blinding the first T1 cook (constructions A/B/C and the bare-chip control).
  python3 tools/t1_randomize.py R1-it1      writes food/t1-results/keys/R1-it1.json (keep it SEALED until all scoring is finished) and prints only the codes to write on the plates
Appearance cannot be blinded (the constructions look different); flavour and texture are the only blinded signals. Uses the OS random source, no seed."""
import json, os, secrets, sys
run = sys.argv[1] if len(sys.argv) > 1 else "R1-it1"
items = ["A", "B", "C", "CONTROL"]
codes = set()
while len(codes) < len(items): codes.add(str(100 + secrets.randbelow(900)))
codes = list(codes); secrets.SystemRandom().shuffle(codes)
key = dict(zip(items, codes))
os.makedirs("food/t1-results/keys", exist_ok=True)
path = f"food/t1-results/keys/{run}.json"
if os.path.exists(path): sys.exit(f"{path} exists: never overwrite a key")
json.dump({"run": run, "key": key, "note": "SEALED until scoring ends"}, open(path, "w"), indent=1)
print(f"Run {run}: write these codes on the plates (the key is in {path}; do not open it before scoring):")
print("  codes:", ", ".join(sorted(codes)), "  (the cook plates from the key; tasters see codes only)")
