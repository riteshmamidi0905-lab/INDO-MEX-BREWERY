# NASHA Enterprise AI Lab — Operations Data Platform (block 1)

**SYNTHETIC DATA / SIMULATED OPERATION / OFFLINE EVALUATION / NOT PRODUCTION DEPLOYED.** NASHA has no restaurant, customers, sales, staff or brewery batches. Nothing here is a business result. Menu prices are placeholder inputs. The "scenario sites" are not real or planned locations. Same-author caveat: one author wrote the generator, the rules and the scoring; no independent review.

## What it is
A deterministic synthetic NASHA operations dataset **with labelled, injected defects**, and a layered pipeline that must find them:

`raw CSV -> staging (typing, rejects) -> validated (11 data-quality rules, quarantine, severities) -> modeled (SQLite star schema) -> analytics views`, with a lineage table, a row-conservation invariant, and a publish gate that fails on a D-54 violation (beef/pork/derivatives in a menu record).

```bash
cd lab && python -m pip install pytest && python -m pytest -q tests      # 30 tests
python -m nasha_lab.run --seed 1 --out lab_out                          # one run; exit 3 when the publish gate fails
python -m nasha_lab.evaluate v1 | diff - results/eval_v1.json           # evaluation must reproduce byte for byte
```

## Evidence (all re-runnable; numbers are from this repository's committed results)
| Claim | Evidence |
|---|---|
| 30 tests pass | `tests/test_platform.py`; also run in `.github/workflows/lab-ci.yml` and `tools/validate_all.sh` |
| 10 of 11 detectable defect types found with precision 1.0 and recall 1.0 over 5 seeds x 8 injections | `results/eval_v1.json` |
| 0 findings on the clean dataset (no false positives over 5 seeds) | `results/eval_v1.json` -> `clean_dataset_findings` |
| Fail-then-fix: `near_duplicate_order` recall 0.0 in baseline v0, 1.0 after adding the rule | `results/eval_v0_baseline.json` vs `eval_v1.json` |
| Honest remaining gap: a copy shifted by 1 second is NOT detected (recall 0.0) | `test_known_limitation_...`, `docs/EVALUATION.md` |
| A real bug found by the lineage report and fixed with a regression test: dedup quarantined both copies of a duplicated order | `test_regression_dedup_keeps_the_original_order` |
| Tests can fail: 2 of 2 manual mutants (tolerance 0.25 -> 0.05; inverted total check) are caught | `docs/EVALUATION.md` |

Read next: [ARCHITECTURE](docs/ARCHITECTURE.md) · [EVALUATION](docs/EVALUATION.md) · [AUDIT, registry and roadmap](docs/AUDIT.md)
