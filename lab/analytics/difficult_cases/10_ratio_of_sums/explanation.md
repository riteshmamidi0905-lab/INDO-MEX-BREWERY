# Case 10: Overall on-time delivery rate: explanation (NOT candidate-facing)

Skills: ratio of sums, Simpson-style weighting, NULL semantics

Known outcomes: S1 8 on time of 9 known, S2 1 of 2, S3 0 of 1. Pooled: 9 / 12 = 0.75 over 12 known deliveries. The trap averages the three per-supplier rates (0.889, 0.5, 0.0) with equal weight, giving 0.463, and its COUNT(*) counts suppliers (3), not deliveries. A second variant, SUM(on_time) / COUNT(*), treats the 3 unknown outcomes as late (9/15 = 0.6). Rule: aggregate ratios as a ratio of sums over the correct denominator, never average averages across unequal groups, and decide explicitly what NULL means.
