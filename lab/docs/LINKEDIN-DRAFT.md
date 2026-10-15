# LinkedIn draft (NOT PUBLISHED; for the founder's review. Every number is in the claims ledger or a committed result file.)

**I finally put an LLM into my agent. It lost.**

I built a simulated business (synthetic data, no customers) with an operations agent that investigates exceptions like low inventory or a supplier proposal that touches a dietary rule. It uses typed tools and a status-aware knowledge base, and it stops for a signed human approval before anything consequential.

Then I built two planners behind one interface, a deterministic one and a local open-weight LLM (Qwen2.5, 1.5B and 7B, free CPU runners, no paid API), and ran both under identical permissions, scenarios and checks. Not to prove the LLM was good. To find out.

What I measured:
- The deterministic planner passed 259 of 259 of my scenarios. The 1.5B model passed 5 of 140; the 7B model 10 of a 35-scenario sample, at about 2.5 minutes per scenario on CPU. The model won on none.
- Safety didn't depend on the model: about 1,000 real model calls, 0 executed external actions. The model proposes; deterministic code validates, authorizes and logs; a human approves.
- The small model failed in the dangerous direction: in 1 of 5 scenarios it said "no action needed" when action was needed. A deterministic evidence check removed every one of those, at the price of escalating almost everything. A guardrail is a safety device, not a capability.

What failed in my own system: the check that a model's proposed action targets a real record built its "evidence" from the whole run, including the arguments the model itself had passed. A key the model invented grounded itself. An adversarial test found it. The fix is a rule about what may count as evidence, plus a regression test.

What the follow-up showed: when I added per-scenario traces, the "forbidden attempts" I had been counting turned out to be one misspelled tool name, not attempts at anything forbidden. I corrected the record instead of the number.

And retrieval: a small neural encoder and pgvector worked, and BM25 still beat them on identifier-heavy company documents. On a second question set I built differently, the lead held mostly where questions shared the corpus's exact words; on paraphrases the gap closed and a hybrid won.

What it isn't: evidence about LLMs in general, or results in a real business. One author wrote the system, scenarios and checks, which flatters the deterministic planner. I only tried small free models. NASHA is an independent personal project, not my job.

The lesson I'm keeping: use the simplest system that satisfies the reliability requirement, and measure before you assume the model is needed.

Write-up, numbers and code: github.com/riteshmamidi0905-lab/INDO-MEX-BREWERY (lab/docs/PLANNER-EXPERIMENT.md) and the case study on my portfolio.
