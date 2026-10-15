# LinkedIn draft (NOT PUBLISHED; for the founder's review)

I built an operations agent for a business that does not exist yet, so I could test it without real customers.

The scenario: goat inventory is running low, the supplier needs five days, and the supplier-status tool fails mid-investigation. My first version answered "no action needed."

It had not concluded that. Its drafting branch needed a supplier list, didn't get one, and fell through to the default. My happy-path evaluation scored 18/18 and never touched this path. A failure-injection run did.

The fix was a rule, not a prompt: short cover with an unconfirmed supplier escalates as "insufficient verified evidence," and "no action" is impossible if any check failed. Then a regression test.

Same project, same lesson: my decision register still listed an old name as active after a newer decision replaced it. A retriever that trusts the register would have presented a superseded decision as policy.

What it is: synthetic data, a deterministic planner (not an LLM), 133 tests, human approval before anything consequential, nothing that can contact a supplier. What it isn't: evidence of results in a real business. Evaluation is by me, on my own scenarios.

The lesson I'm keeping: evaluate what the agent does when its tools fail, not just when they work.

Code and write-up: github.com/riteshmamidi0905-lab/INDO-MEX-BREWERY (lab/)
