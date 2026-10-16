# Case 03: Units sold by dish name as of the sale date: explanation (NOT candidate-facing)

Skills: SCD2, range joins, half-open intervals

BETWEEN is inclusive on both ends, so a sale on the change date (2026-04-13, 5 units) matches BOTH versions and is counted twice; the old name gets 10 instead of 5, total 20 instead of 15. With half-open ranges every sale matches exactly one version. Follow-up: assert in a test that every fact row joins to exactly one dimension version (count of matches = 1).
