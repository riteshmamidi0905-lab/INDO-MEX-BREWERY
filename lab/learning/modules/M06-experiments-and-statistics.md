# Module M06: experiments and statistics (`warehouse/experiments.py`, `analytics.py`)

Status for you: NOT ASSESSED.

**A. Architecture.** Deterministic assignment by hashing member and experiment ids; two-proportion test with a Wald interval; Welch t-test for means; sample-ratio-mismatch check; sample-size calculation; a five-experiment synthetic portfolio with known injected effects (win, inconclusive, null, harmful, broken split); promotion analysis inside windows; cohort retention, RFM tertiles and a right-censored funnel.
**Concepts.** Randomization, power, minimum detectable effect, confidence intervals vs p-values, multiple comparisons, SRM, novelty effects, right-censoring, survivorship, "no behavioural response is modelled" as a limit of the simulation.
**B. Independent exercise.** Implement a two-proportion z-test and confidence interval without a statistics library; compare with `experiments.two_proportion` on the portfolio inputs.
**C. Debugging challenge.** Experiment E5 shows a significant +3 points. Explain why you must not ship it, using only the SRM check. Then explain what you would do next.
**D. Interview questions.** E2's interval spans zero: what do you tell the product manager, and how large a test would you run? Why can a "no lift" promotion still be a good decision (or not)?
**E. Tradeoffs.** Fixed-horizon vs sequential tests; stopping rules; one metric vs a guardrail set; observational promotion analysis vs a randomized holdout.
**F. Evidence.** Date / task / link.
