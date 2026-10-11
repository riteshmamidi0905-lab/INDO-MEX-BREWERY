#!/usr/bin/env bash
# NASHA project security & licence check (Sprint 14). Read-only. Usage: bash tools/security_check.sh
set -u; fail=0
echo "== secret patterns in tracked files =="
if git grep -InE '(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{32,}|hf_[A-Za-z0-9]{30,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,})' -- . ':!tools/security_check.sh'; then echo "POSSIBLE SECRET FOUND"; fail=1; else echo "none"; fi
echo "== bandit (python, medium+) =="; python3 -m bandit -q -r tools website/build.py website/images.py website/art.py -ll 2>&1 | tail -4
echo "== pip-audit (project-used packages) =="; python3 -m pip_audit -r <(printf 'pillow\nnumpy\npandas\nscipy\nrequests\nlxml\njinja2\nopenpyxl\n') 2>&1 | tail -3
echo "== npm audit (website/qa) =="; (cd website/qa && npm audit --omit=dev 2>&1 | tail -2)
echo "== licences (python, summary) =="; pip-licenses --format=csv 2>/dev/null | python3 -c "import csv,sys,collections;print(collections.Counter(r['License'] for r in csv.DictReader(sys.stdin)).most_common(8))"
echo "== licences (node, summary) =="; (cd website/qa && npx --no-install license-checker-rseidelsohn --summary 2>&1 | tail -8)
exit $fail
