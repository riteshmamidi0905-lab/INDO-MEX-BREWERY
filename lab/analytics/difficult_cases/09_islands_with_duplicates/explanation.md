# Case 09: Longest streak of consecutive trading days per site: explanation (NOT candidate-facing)

Skills: gaps and islands, DISTINCT before window, tie-breaks

The date-minus-row-number trick needs ONE row per day. With duplicate rows the row number advances faster than the date, which breaks runs in some places and, worse, glues non-consecutive days together in others: the trap reports site A with a 5-day streak (03-01, 03-02, 03-03 plus 03-06 and 03-07 share an island id by accident) when the true longest run is 3 days (03-01 to 03-03). DISTINCT the (site, day) first, then pick the best island per site with a second ROW_NUMBER that includes the tie-break. Tie-break: B has two 2-day runs; the earlier (03-01) wins.
