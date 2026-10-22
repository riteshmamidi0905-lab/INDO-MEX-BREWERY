#!/usr/bin/env python3
"""Write requirements.lock: the INSTALLED versions of every direct dependency named in requirements*.txt (names only; no transitive closure), with the
python version. A reproducibility record of what the tests were last validated against, not a full resolver lock file."""
import importlib.metadata as md
import platform
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
names = set()
for f in sorted(root.glob("requirements*.txt")):
    for line in f.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-r") or line.startswith("-"):
            continue
        m = re.match(r"([A-Za-z0-9_.\-]+)", line)
        if m:
            names.add(m.group(1).lower().replace("_", "-"))
out = [f"# python {platform.python_version()} on {platform.system()} — installed versions of direct dependencies when last validated (tools/make_lock.py)"]
missing = []
for n in sorted(names):
    try:
        out.append(f"{n}=={md.version(n)}")
    except md.PackageNotFoundError:
        missing.append(n)
if missing:
    out.append("# not installed here: " + ", ".join(missing))
(root / "requirements.lock").write_text("\n".join(out) + "\n")
print(len(out) - 1, "pins;", "missing:", missing or "none")
