# Case 08: Which month sells best per day?: explanation (NOT candidate-facing)

Skills: period normalisation, partial periods

Comparing monthly TOTALS makes March (the partial month) look worst and February (28 days) look worse than January; dividing by a fixed 31 days is wrong for February and for the partial March. Normalise by days actually observed in the window: March is the best month per day (130), not the worst. Rule: for any period comparison state the exposure (days, orders, sites open) and exclude or flag incomplete periods.
