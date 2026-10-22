# NASHA analytics: prospective sample-size design (synthetic experiment)

**SYNTHETIC DATA / SIMULATED OPERATION / NOT PRODUCTION DEPLOYED.** NASHA has no restaurant, customers, sales, suppliers or staff. Prices, costs and recipes are placeholders or assumptions. Nothing here is a business result.

This is a **forward-looking design exercise** for the simulated M04 placement test in [`ANALYTICS-EVALUATION.md`](ANALYTICS-EVALUATION.md). The original experiment there was **deliberately underpowered** (170 synthetic guests per arm, analytic power about 22% at the injected effect). It is kept **unchanged as historical evidence and is NOT retroactively resized**. Nothing below is a real-business outcome: NASHA has no guests, no placement test and no sales.

## Inputs (from the simulated experiment)

- Injected effect: **0.2258** M04 units per treated guest. Pre-period SD of M04 units per guest: **1.7611**. Observed pre/post correlation (for CUPED): **0.2020**.
- Two-sided test, alpha 0.05; two equal arms. Source: `results/analytics/experiment.json`; module `analytics/prospective_design.py`; results `results/analytics/prospective_design.json`.

## Required guests per arm

Closed form: n = 2 (z(1-alpha/2) + z(power))^2 sd^2 / delta^2; CUPED replaces sd^2 by sd^2 (1 - rho^2).

| Target power | Estimator | n per arm | Total | Analytic power at n | Monte Carlo power at n | MC standard error | Reaches target within MC error |
|---|---|---|---|---|---|---|---|
| 80% | unadjusted | 955 | 1,910 | 80.01% | 81.50% | 0.61% | True |
| 80% | cuped | 916 | 1,832 | 80.01% | 80.65% | 0.62% | True |
| 90% | unadjusted | 1,279 | 2,558 | 90.02% | 89.88% | 0.48% | True |
| 90% | cuped | 1,227 | 2,454 | 90.02% | 90.40% | 0.47% | True |

Headline: about **955 per arm for 80% power** and **1,279 per arm for 90% power** unadjusted; with CUPED at the observed correlation **916** and **1,227**. That is roughly 5.6 times the 170 per arm of the original run. CUPED saves only about 4% because the correlation is low.

Type I error check at the 80% sample sizes with zero true effect: unadjusted 4.75%, CUPED 5.17% (nominal 5%).

## Sensitivity to effect size and SD (per arm)

| Effect x | Effect (units/guest) | SD x | SD | 80% unadj. | 80% CUPED | 90% unadj. | 90% CUPED |
|---|---|---|---|---|---|---|---|
| 0.5 | 0.113 | 0.75 | 1.32 | 2,149 | 2,061 | 2,877 | 2,759 |
| 0.5 | 0.113 | 1.0 | 1.76 | 3,820 | 3,664 | 5,114 | 4,905 |
| 0.5 | 0.113 | 1.25 | 2.20 | 5,968 | 5,725 | 7,990 | 7,664 |
| 1.0 | 0.226 | 0.75 | 1.32 | 538 | 516 | 720 | 690 |
| 1.0 | 0.226 | 1.0 | 1.76 | 955 | 916 | 1,279 | 1,227 |
| 1.0 | 0.226 | 1.25 | 2.20 | 1,492 | 1,432 | 1,998 | 1,916 |
| 1.5 | 0.339 | 0.75 | 1.32 | 239 | 229 | 320 | 307 |
| 1.5 | 0.339 | 1.0 | 1.76 | 425 | 408 | 569 | 545 |
| 1.5 | 0.339 | 1.25 | 2.20 | 664 | 637 | 888 | 852 |
| 2.0 | 0.452 | 0.75 | 1.32 | 135 | 129 | 180 | 173 |
| 2.0 | 0.452 | 1.0 | 1.76 | 239 | 229 | 320 | 307 |
| 2.0 | 0.452 | 1.25 | 2.20 | 373 | 358 | 500 | 479 |
| 3.0 | 0.677 | 0.75 | 1.32 | 60 | 58 | 80 | 77 |
| 3.0 | 0.677 | 1.0 | 1.76 | 107 | 102 | 143 | 137 |
| 3.0 | 0.677 | 1.25 | 2.20 | 166 | 160 | 222 | 213 |

CUPED correlation sensitivity at the injected effect and SD:

| rho | n per arm, 80% | n per arm, 90% |
|---|---|---|
| 0.0 | 955 | 1,279 |
| 0.2 | 917 | 1,228 |
| 0.4 | 803 | 1,074 |
| 0.6 | 612 | 819 |

## Assumptions and limits

- Two-sided z test at alpha 0.05, two equal arms, individual guests as the unit of randomisation.
- The effect is the injected truth of the simulation (about 0.23 M04 units per treated guest); the SD is the pre-period SD of M04 units per guest, used as the variance proxy for the experiment window.
- CUPED reduces the variance by the factor (1 - rho^2), with rho the pre/post correlation observed in the one simulated run; with rho about 0.2 the saving is small.
- The Monte Carlo uses stylised bivariate-normal data with the same SD, rho and effect, not the skewed count data of the mart: it confirms the arithmetic and the estimator, not the shape of real data. Heavy tails, repeated visits and clustering would need more guests.
- Seeded and deterministic (seed 20260101, 4000 repetitions). Monte Carlo standard error of a power estimate is about 0.6 points at 80%.
- Not covered: multiple metrics (the Holm family of guardrails), sequential looks, attrition, interference between guests, novelty effects, a real baseline. NASHA has no guests; this is a method exercise.

Evidence: `lab/results/analytics/prospective_design.json`, reproducible with `cd lab && python3 -m analytics.run_all && python3 -m analytics.render_docs`.
