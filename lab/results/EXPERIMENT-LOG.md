# Experiment log (Block 3): what was run, in what order, and what was changed after seeing results

SYNTHETIC; same author; read the disclosure in `docs/PLANNER-EXPERIMENT.md`.

## Planner experiment
1. **Planner interface** extracted from the Block 2 agent (`planners.py`): `DeterministicPlanner` (control, unchanged logic) and `LLMPlanner` share state, tool registry, permission layer, approval gate, trace and harness.
2. **Scenario suite** generated programmatically (`scenarios.py`), expectations set by construction from the injected condition. Splits: **dev** (families and seeds used while building), **held-out** (different families, seed 3000), **adversarial** (poison, replay, edit/decision abuse, untrusted MCP modes).
3. **First deterministic run (before any fix), 175 scenarios:** dev 67/67; **held-out 73/75; adversarial 28/33.**
   - 2 held-out failures: `count_variance` on hops. The variance check ignored any expected quantity below 0.5 kg; hops are used in grams. **Real weakness in a shared tool. Fixed** (floor scaled to usage).
   - 4 adversarial failures: “pork-free”, “no beef stock” etc. were rejected as prohibited. **Real weakness. Fixed** (negated mention = unverified supplier claim). Metamorphic property test added.
   - 1 adversarial failure: harness false positive + a real echo of attacker text inside a claim. **Fixed both** (untrusted spans are quoted and marked; the leak check ignores marked spans).
4. **Disclosure of contamination.** These fixes were made after reading held-out failures, so **held-out (seed 3000) is no longer a clean test of the deterministic planner.** A second, never-inspected draw, **held-out B (seed 7000)**, was generated and scored only after the fixes: 75/75. LLM planners were first run after all of this; no scenario was edited in response to an LLM result.
5. **Stand-in models** (scripted, not language models) were added to test the pipeline and the permission layer:
   - `rule-model` equals the deterministic planner scenario by scenario (harness parity).
   - `worst-case` made 1,820 forbidden attempts (external actions, unknown tools, unapproved mutations, invented targets, invented evidence); **none executed**.
   - `parrot` (obeys injected text) kept permissions intact but **changed 2 of 42 adversarial recommendations**; the evidence envelope (deterministic guardrail) restores 42/42.
   - `taint-copier` copied a persuasive untrusted note into a draft; the taint check refused it (safe, degraded).
6. **Defects found by the stand-ins, fixed:** (a) mutation targets were “grounded” against evidence that included the model’s *own tool arguments*; (b) an unauthenticated caller could tell which run ids exist (404 vs 401). Both fixed with regression tests.
7. **Mutation testing** of the safety code: first run **19/22** killed. Survivors: M12 (no direct test of the mutation-tool allowlist), M13 and M14 (two redundant defensive layers each masked the other). Closed with layer-isolating unit tests: **22/22**. M13/M14 were not “equivalent mutants”; each layer now has its own test.

## Retrieval and abstention
1. v1 (55 hand-written questions) kept as history. v2 adds 412 generated, structurally validated questions in 13 categories (467 total), split by *source document* (content) or *template family* (unanswerable).
2. Retrievers: BM25, LSA, hybrid, static neural (spaCy md), hybrid-static, pgvector (HNSW) over the static vectors; MiniLM measured in CI only.
3. **Abstention strategies** (8) compared; thresholds/hyper-parameters fit on dev only (5-fold CV on dev for the learned gate).
4. **Finding:** the learned gate trained on generated questions over-refused hand-written paraphrases (dev accuracy .842 -> .632 on that subset). Re-selected by CV with paraphrases weighted 3x. End-to-end held-out: false answers 29% -> 15%, false abstentions 2% -> 6%; hand-written held-out (n=17) .824 -> .941, hand-written dev .842 -> .789. **Mixed and small-n: reported as unsettled.**
5. Default retriever left as hybrid although BM25 wins on generated questions: on the 45 hand-written paraphrases hybrid is ahead (MRR .794 vs .764). n=45; within noise; recorded as a judgment call.
