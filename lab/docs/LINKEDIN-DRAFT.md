# LinkedIn draft (NOT PUBLISHED; for the founder's review. Numbers are from committed result files.)

I finally put an LLM into my agent. Then I tested whether it actually improved anything.

The setup: a simulated business (synthetic data, no customers) with an operations agent that investigates exceptions like low inventory or bad orders, using typed tools and a status-aware knowledge base, and stops for a signed human approval before anything consequential. I built two planners behind one interface, a deterministic one and a local open-weight LLM (Qwen2.5, 1.5B and 7B, free CPU runners, no paid API), and ran both under identical permissions, scenarios and metrics.

The result, honestly: the deterministic planner won. It passed 259/259 of my scenarios. The 1.5B model passed 4-7%; the 7B model passed 29% of a smaller sample and took about 2.5 minutes per scenario on CPU. The model won on no scenario.

Three things I'd keep from it:
- Safety did not depend on the model. About 1,000 real model calls, 0 external actions, 100% approval-boundary compliance. The model proposes; deterministic code validates, authorizes and logs; a human approves.
- The small model failed in the dangerous way: in 1 of 5 scenarios it said "no action" when action was needed. A deterministic evidence check removed every one of those.
- Same pattern for retrieval. A real sentence encoder (MiniLM) and pgvector worked, and did not beat plain BM25 on identifier-heavy company documents (MRR 0.67 vs 0.91). I measured it so I didn't have to guess.

What it isn't: evidence about LLMs in general, or results in a real business. One author wrote the system, scenarios and checks, which flatters the deterministic planner, and I only tried small free models.

Mutation testing of the safety code also found my tests were weaker than I thought: two redundant defenses were masking each other. 19/22 mutants killed at first, 22/22 after fixing the tests.

Write-up, numbers and code: github.com/riteshmamidi0905-lab/INDO-MEX-BREWERY (lab/docs/PLANNER-EXPERIMENT.md)
