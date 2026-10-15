# The failure that mattered most in Block 3: "grounded" meant "the model said so"

SYNTHETIC DATA / OFFLINE EVALUATION. Interview-ready; every claim below is backed by a committed test or result file.

## What failed
The agent lets a planner (deterministic, or a language model) propose *mutating* actions, for example flagging a record for review. Before anything reaches the human reviewer, `validate_mutations` is supposed to check that each proposed target is **grounded**: that the record key actually appears in trusted evidence the system itself collected. When I ran the worst-case stand-in model (a scripted adversary that proposes invented record keys, unknown tools and external actions), some **invented targets passed the grounding check**.

## Why it mattered
Grounding is the control that stops a model from fabricating a record id and getting a human to approve an action against a thing that does not exist (or against a real record the model had no business touching). The check existed, had a test, and looked correct. It was silently vacuous for any model that *named* the target in its own tool call, which is what a real model does.

## How the test found it
Not the happy path, and not the deterministic planner (which only ever proposes targets it just read). The **worst-case stand-in** over the 259 scenarios made 1,820 forbidden attempts; the safety layer refused them all except this class. The harness records every refusal and every executed action, so the surviving invented target showed up as an unexpected pass, not as a crash.

## Root cause
The grounding blob was built from the whole evidence map, and the evidence map includes an entry for every tool call, including the **model's own request arguments** and its error entries. A target the model invented and passed as an argument therefore appeared in "the evidence" and grounded itself.

## Fix
`validate_mutations` now builds the blob from **only** `data` of tool calls that succeeded, were not flagged as suspected injection, and did not come from the untrusted supplier-notes tool, plus the triggering event. A model cannot ground a claim in its own arguments. `release_draft` is additionally restricted to the draft created in the same run. The same discipline applies to claims (`validate_claims` drops claims without a resolvable evidence id) and to arguments derived from untrusted text (taint check).

## Regression tests
- `tests/test_llm_planner.py::test_invented_mutation_targets_are_rejected_before_review` (worst-case model; asserts a `mutation_rejected` event and an empty mutation list).
- `tests/test_planner_units.py::test_validate_mutations_keeps_a_grounded_flag_and_this_runs_own_draft_only` (layer-isolated unit test).
- The worst-case stand-in is part of the CI planner reproduction (`repro_check planner`), so a reintroduction changes the committed numbers and fails CI.

## A second lesson from the same defect: redundant defences hide missing tests
Mutation testing of the safety code (22 mutants) first killed 19. The three survivors (M12-M14) were not equivalent mutants: **two redundant defensive layers each masked the other**, so deleting either one changed no test result. Layer-isolating unit tests were added; the score is 22/22. If you can delete a safety check and nothing fails, you do not know that the check works.

## What a real model did (Qwen2.5-1.5B on CPU)
The permission layer held against a real model too: 434 model calls in run 1, 95 forbidden-action attempts, **0 external actions, 100% approval-boundary compliance**. That is the point of putting the model behind deterministic validation instead of trusting it. (The same run shows the model is not *useful* on this suite; see [PLANNER-EXPERIMENT.md](PLANNER-EXPERIMENT.md).)

## Remaining limitation
Grounding checks that a key *appears* in trusted evidence, not that flagging it is a good idea; a model can still pick a real but irrelevant record, and a human reviewer is the control for that. A different real model might find a path the stand-ins do not; the mutation score and the stand-ins bound the pipeline, they do not prove it.
