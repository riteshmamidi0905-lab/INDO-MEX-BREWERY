# Difficult SQL cases (ten) - candidate-facing material only

**SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.**

Each `NN_name/` folder holds only what a candidate may see: `prompt.md`, `fixture.sql` and `trap.sql` (the tempting wrong query).

The answer keys (`solution.sql`, `expected.json`, `explanation.md` for each case) are deliberately **not in this repository or its history**. They are kept privately so the cases can seed an unassisted SQL assessment.

- `KEYS-MANIFEST.sha256` lists the sha256 of every removed key file (30 entries), so the owner can show that the private copies are the ones that were removed (`cd difficult_cases && sha256sum -c` against a private directory laid out as `<dir>/NN_name/<file>`).
- Verification: the key-dependent tests run only when the environment variable `NASHA_PRIVATE_KEYS` points at the private directory (layout `<dir>/NN_name/{solution.sql,expected.json,explanation.md}`). Without it they SKIP cleanly; the public tests (files present, prompt does not leak, fixtures load, trap runs, manifest well-formed) always run.
- Without the keys, nobody but the owner can claim these cases are verified; the public repository only shows that the fixtures and trap queries are well-formed.

```bash
cd lab
python3 -m pytest -q -p no:cacheprovider tests/test_analytics_difficult_cases.py                      # keys absent: key tests skip
NASHA_PRIVATE_KEYS=/path/to/private/p4-private-keys python3 -m pytest -q -p no:cacheprovider tests/test_analytics_difficult_cases.py
```
