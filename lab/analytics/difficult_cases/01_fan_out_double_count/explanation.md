# Case 01: Revenue per site from orders and lines: explanation (NOT candidate-facing)

Skills: grain, fan-out, semi-join

The header total is repeated once per line after the join, and COUNT(*) counts lines. Site A: 3 orders, 230 USD; the trap returns 6 and 510 (100x3 + 50x1 + 80x2). Order O5 has no lines and must not count. Fix: a semi-join (EXISTS), or aggregate lines to order grain before joining. Rule: before every join write down the grain of both sides; a 1-to-many join changes the grain of any measure on the 'one' side.
