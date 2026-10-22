"""Verify the contrast table in brand/NASHA-IDENTITY-SYSTEM.md section 3 against the real tokens in website/src/styles.css.
Stdlib only. Exit 1 if a documented ratio differs from the computed one by more than 0.06, or a pair the doc forbids for text passes 4.5.
    python3 website/tools/check_contrast.py"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / "website/src/styles.css").read_text()
DOC = (ROOT / "brand/NASHA-IDENTITY-SYSTEM.md").read_text()


def tokens():
    root = re.search(r":root\{(.*?)\}", CSS, re.S).group(1)
    return {m.group(1): m.group(2).upper() for m in re.finditer(r"--([a-z-]+):(#[0-9a-fA-F]{6})", root)}


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main():
    t = tokens()
    sec = DOC[DOC.index("Accessible text pairs"):DOC.index("**Rules:**")]
    bad, n = [], 0
    for row in re.finditer(r"^\| (.+?) on (.+?) \| (?:\*\*)?([\d.]+)(?:\*\*)? \| (.*?) \|", sec, re.M):
        fg, bg, doc_ratio, use = row.groups()
        fg, bg = (re.sub(r"[*]|-ink`?.*$", "", x).strip() for x in (fg, bg))
        ink = "ink" in row.group(1)
        key = lambda s, i=False: (s.lower() + ("-ink" if i else "")).replace("**", "")
        f, b = t.get(key(fg.split()[0], ink)), t.get(key(bg.split()[0]))
        if not f or not b:
            continue
        n += 1
        got = ratio(f, b)
        if abs(got - float(doc_ratio)) > 0.06:
            bad.append(f"{row.group(1)} on {row.group(2)}: doc {doc_ratio} vs computed {got:.2f}")
        if re.search(r"fail|decorative", use, re.I) and got >= 4.5:
            bad.append(f"{row.group(1)} on {row.group(2)} is forbidden for text but computes {got:.2f}")
    print(f"checked {n} documented pairs against styles.css tokens; {len(bad)} problems")
    for b in bad:
        print("  -", b)
    return 1 if bad or n < 10 else 0


if __name__ == "__main__":
    sys.exit(main())
