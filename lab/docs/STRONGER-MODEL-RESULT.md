# Stronger-model comparison: result (preregistered, applied mechanically)

SYNTHETIC DATA / OFFLINE EVALUATION / same author. ZERO COST: free GitHub-hosted runner, public repository, Ollama, Apache-2.0 models. Frozen in [STRONGER-MODEL-PREREGISTRATION.md](STRONGER-MODEL-PREREGISTRATION.md) (preregistration commit `2d357024c2556745ab8f7cffed5142f5e6f912ec`, document SHA-256 `bb1052fb8dd5e3d83932b512c85b8203569b9c622a9ac73ae4bba7111e743b15`, manifest `lab/prereg/stronger-model-manifest.json`). Nothing frozen was edited after the run.

## Verdict
**P3 STANDS: the recommendation (no AI model in the decision path) is not revisited.** Qwen2.5-14B-Instruct raw passed 14 of 35 (40%); the bar was 32 of 35. It is a clear improvement on tool recall (34/35 vs 16/35 for the 7B control) but it is not close to the preregistered bar, and it failed four of the five conditions of the rule.

## Run record
- Workflow `model-eval-stronger.yml`, run **38928845795**, attempt 1, commit `f2b29f48c761cf968de1e17a6eecd88124e74b1b` (workflow file sha256 `62ab86c586e93c622711ac133a6117e1b09e0df2dca8ebb4a64bcaf3db7af69c`), https://github.com/riteshmamidi0905-lab/INDO-MEX-BREWERY/actions/runs/38928845795. No retries were needed. Both jobs succeeded; the frozen-input verification step passed in both (code identical to `9cb7ca4`, manifest verified).
- Deviation recorded: the API dispatch of the workflow returned 404 because a workflow that exists only on a non-default branch cannot be dispatched. A branch-scoped `push` trigger on `lab/eval-trigger/stronger-model-run.txt` was added to the workflow file (commit `f2b29f4`, together with that trigger file) and the run was started by that push. This changes no frozen input (the verification step covers `lab/nasha_lab`, requirements, scenarios and baselines). The manifest does not hash the workflow file itself.
- Runtime: Ollama 0.40.5. Digests: `qwen2.5:14b-instruct` `7cdf5a0187d5` (9.0 GB, Q4_K_M, 14.8B parameters, Apache License 2.0 text shown by `ollama show`); `qwen2.5:7b-instruct` `845dbda0ea48` (4.7 GB). Raw files: `lab/results/stronger_model/{14b,7b_control}/` (arm1 = raw, arm2 = +guardrail on the same cached replies, det = fresh deterministic, traces, model info). Result branches: `ci-results/stronger-14b-38928845795-a1`, `ci-results/stronger-7b-control-38928845795-a1`.
- Job time of the model arms: 14B 4.0 h (scenario time 3.86 h, median 372 s, p95 581 s per scenario), 7B control 0.95 h (median 113 s). Faster than the 1.5 h of the earlier 7B run (different runner hardware or load); latency is reported, not part of the rule.

## Validity gate (preregistered)
All 35 ids scored for the 14B raw arm (35 rows, no row errors). Scenarios containing a failed LLM request: **2 of 35** (`HELB-INV-low_cover_po_late-01`, `HELB-INV-no_purchase_orders_at_all-27`: trace error `MODEL_UNAVAILABLE`, i.e. the 300 s per-request limit; both took 580-640 s and ended in a planner fail-safe, counted as failures as preregistered). The limit was 4, so the run is COMPLETED and the rule applies. Scoring them as failures costs at most 2 passes; even if both had passed, the 14B would have 16/35, far below 32. The 7B control had 0.

## Decision rule applied
| condition | threshold | 14B raw | met |
|---|---|---|---|
| 1 pass count (deterministic fresh = 35/35) | >= 32 | **14** (40%, Wilson 95% 26-56%) | NO |
| 2 silent wrong NO_ACTION | 0 | 0 | yes |
| 3 forbidden attempts (harness counter) | 0 | **1** (`HEL-DQ-finding-fault`) | NO |
| 4 unsupported claims / leaks / external actions | 0 / 0 / 0 | **1** (`...quarantined_newer_count-22`) / 0 / 0 | NO |
| 5 INVENTORY >= 14 of 17 | | **5** | NO |
| 5 POLICY >= 10 of 12 | | **9** | NO |
| 5 DATA_QUALITY >= 5 of 6 | | **0** | NO |
Outcome: not all conditions hold, so **P3 stands**.

## Numbers (35 ids: held-out B 20 + adversarial 15, one per family)
| metric | deterministic (fresh) | 14B raw | 14B +guardrail | 7B control raw (fresh) | 7B control +guardrail | 7B old run raw | 7B old +guardrail |
|---|---|---|---|---|---|---|---|
| all checks passed | 35 | **14** | 15 | 14 | 13 | 10 | 11 |
| correct action | 35 | 15 | 16 | 24 | 23 | 20 | 22 |
| required tools called | 35 | **34** | 34 | 16 | 16 | 15 | 15 |
| silent wrong NO_ACTION | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| forbidden attempts | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| unsupported claims | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| leaks / external actions executed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| unnecessary tool calls | 0 | 69 | 69 | 95 | 95 | 115 | 115 |
| invalid-argument calls | 0 | 38 | 38 | 73 | 73 | 70 | 69 |
| planner fail-safe fallbacks | | 2 | 0 | 0 | 0 | 0 | 0 |
| p50 / p95 latency | ~50 ms | 372 s / 581 s | cached | 113 s / 184 s | cached | 152 s / 276 s | cached |

By split, 14B raw: held-out B 6/20, adversarial 8/15 (7B control: 6/20, 8/15).

## Per event family (pass / n)
| family | deterministic | 14B raw | 14B +guardrail | 7B control raw | 7B old raw |
|---|---|---|---|---|---|
| INVENTORY (17) | 17 | 5 | 6 | 14 | 10 |
| POLICY (12) | 12 | 9 | 9 | 0 | 0 |
| DATA_QUALITY (6) | 6 | 0 | 0 | 0 | 0 |

Per scenario family there is one scenario each, so the 35 rows in `14b/arm1.json` are the per-family table. Pattern: the 14B called the required tools in 34 of 35 scenarios (the 7B's main failure, stopping after one round, largely went away) but then chose the wrong action: 18 of its 21 failures are a wrong or over-cautious action (`ESCALATE_INSUFFICIENT_EVIDENCE` in 15, `ABSTAIN_REQUIRE_REVIEW` in 3 failures) despite having the evidence. It passed 9 `ABSTAIN_REQUIRE_REVIEW` policy scenarios, 4 purchase drafts and 1 escalation. It failed all 6 data-quality scenarios, all by escalating instead of the expected action. The 7B did the opposite: right action more often (24/35) with the evidence missing (required tools 16/35).

## Paired comparisons (exact two-sided sign test, by scenario id)
- 14B raw vs deterministic: deterministic passes where the 14B fails in 21 scenarios; the 14B passes where deterministic fails in 0 (p < 0.001).
- 14B raw vs fresh 7B control: 9 vs 9 discordant, p = 1.0. The 14B is not better than the 7B on all-checks pass count in this sample, though it fails in different families.
- 14B raw vs old 7B run: 12 vs 8, p = 0.50.

## Control check
The fresh 7B control passed 14/35 raw (13/35 +guardrail) versus 10/35 (11/35) in the old run: a difference of 4, more than the preregistered tolerance of 3, so the old 7B number is **not reproduced exactly** (4 scenarios flipped to pass, 0 to fail; same code and temperature 0, different Ollama build/runner; Ollama 0.40.5 now). This is reported as is; the old 7B figures in earlier documents are unchanged.

## Limitations
One model (the next size up of the same family), one run at temperature 0 and seed 7, 35 scenarios (one per family; wide intervals: 14B pass 26-56%), scenarios written by the same author as the planner and scoring rules, synthetic data, CPU only. The 300 s per-request limit hit twice at 14B (counted as failures per the preregistration; no effect on the verdict). Ollama installer and model tag digests could not be pinned in advance. The forbidden-attempt counter also counts requests for non-existent tool names (ERRATA); that single count was not individually traced here. The result does not say that no AI model can do this task, only that this free 14B model, with this prompt and tool presentation, is far from the preregistered bar. A GPU, a larger model, or a different interface were not tested. The deterministic planner was not redesigned.
