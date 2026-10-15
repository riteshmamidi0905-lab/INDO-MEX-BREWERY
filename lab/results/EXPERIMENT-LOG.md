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

## Real-model runs (free GitHub-hosted CPU runners, Ollama; results recovered from job logs because artifact/log downloads are blocked in the authoring sandbox)
1. **Run 1** (38777027649, commit f0ebad3): qwen2.5:1.5b-instruct, 138 scenarios (`--per-family 2`). Raw 9/138, guardrail 8/138. 1h12m.
2. **Run 2** (38784135017, commit 3a48adc, final planner code): same model, 140 scenarios. Raw 5/140, guardrail 8/140; 30/140 wrong silent `NO_ACTION` (raw) -> 0 (guardrail); 0 external actions. 1h03m.
3. **Run 3** (38787190128, commit 54d7da9): qwen2.5:7b-instruct, held-out B + adversarial, `--per-family 1` = 35 scenarios. Raw 10/35, guardrail 11/35; p50 151.5 s. Chosen after seeing runs 1-2 (a scale probe); no prompt, scenario or code change was made in response to any model result between runs 1-3 except the workflow's `--splits` argument.
4. **Retrieval-eval CI run** (38786430242, commit cd6078d): MiniLM, hybrids, pgvector on both embedding sets (`results/rag2_retrieval_ci.{md,json}`).
5. **CI failure investigated:** lab-ci 38784135176 (commit 3a48adc) failed at *Retrieval evaluation v2 reproduces* because the HNSW approximate index builds a different graph per build (per-category MRR moved by up to 0.5 on categories with 3-8 questions). Classification: TEST/WORKFLOW defect (comparison too strict for an approximate index), not a code defect. Fixed in 3f7d9d2 (aggregate-only tolerance 0.06 for HNSW; exact retrievers still compared exactly); lab-ci green on every commit since.
6. **Mutation run state:** `results/mutation.json` is the final 22/22 run; `mutation_first_run.json` is the 19/22 first run. The mutation harness restores source files after every mutant; the worktree was verified clean (`git status`, `git diff`) before and after recovery.
