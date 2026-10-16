# Case 07: Net revenue per month with returns booked in the return month: explanation (NOT candidate-facing)

Skills: netting, fan-out, UNION ALL of signed facts

Three traps in one. (1) The sales-driven LEFT JOIN books every return in the SALE month: the 300 USD return that happened in March is charged to January. (2) It fans out: sale 2 has two returns, so its 200 is counted twice in January (300 + 200 + 200 of sales against 300 + 50 + 30 of returns gives the trap's 320). (3) March has returns but no sales, so the month disappears (the true answer is -300). Expected: Jan 500 - 50 = 450, Feb 100 - 30 = 70, Mar -300. A signed-amount UNION ALL keeps each fact at its own grain and its own date. Always ask 'which date does the business attribute this to?'
