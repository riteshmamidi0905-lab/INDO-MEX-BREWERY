# Activation evidence checklist — NOT APPROVED

Candidate: qwen2.5:7b-instruct, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, engineering revision `32316fdb1f6cf4af60e8d4abb3e41dc204f967df`.

**Current decision: REQUIRES_REVIEW; activation BLOCKED.** No evaluation or inference was dispatched to prepare these documents.

## A. Reconcile existing reported evidence

- [ ] Obtain latest original 17-case artifact, CI run/job/attempt identifiers and timestamps; immutable artifact SHA-256, exact full source revision and harness command/configuration.
- [ ] Reconcile user-reported 11/17 with case IDs, pass/fail/inconclusive criteria and six actual failed-case outputs. Identify failure causes without guessing.
- [ ] Preserve retained previous 7/11 baseline (`32316fd:lab/results/model-validation/baseline-run-40109758918.json`) separately. Older executed=false live.json does not establish latest execution status.
- [ ] Record exact model weights digest, runtime version, quantization, tokenizer/options, effective temperature/seed/context/output caps and approved host identity/resources.
- [ ] Retain exact prompts, configuration and corpus/case revisions; original first output, every repair/retry, parsed result, verifier result and exception for every case. Redact secrets without losing proof hashes.
- [ ] For injection cases prove poisoned evidence actually reached the model. Guard-blocked or unexposed cases are inconclusive for raw resistance. Report attempted and executed tool calls separately.
- [ ] Explain held-out status, exclusions, missing outputs, run contamination, known limitations and reproducibility; do not remove failed or slow cases from denominators.

## B. Four independent scorecards

- [ ] Raw quality: first-attempt factual grounding, arithmetic, comparisons, entity binding, supported negative-existence behavior, exposed injection compliance; repaired quality separately.
- [ ] Boundary containment: unsupported claims rejected versus accepted, exact rejection reasons, model tool attempts versus executions, no authority transferred by rejected output.
- [ ] Workflow completion: useful completion, abstention, timeout, cancellation, interruption, audited recovery; deterministic proposal and human approval tracked separately.
- [ ] Security correctness: tenant/reviewer binding, capabilities, WEIR decisions, grant expiry/maker-checker/replay, durable audit and unchanged fixtures. A quality score cannot substitute for security results.

## C. Future target-specific qualification — requires separate authorization

- [ ] Approve proposed thresholds in SPECIFICATION section 11 and exact dataset/denominator policy before running anything; do not call proposed targets already approved requirements.
- [ ] Freeze target schema, prompt and execution-profile hashes, adapter/runtime revisions and source/provenance fixtures. Requalify changed configurations.
- [ ] Authorized isolated evaluation meets the 240-case/three-repeat/held-out design and all critical zero-tolerance controls; genuine exposed-injection denominator and useful-answer coverage demonstrated.
- [ ] Include both businesses, price/comparison/completeness edge cases, cross-tenant/reviewer attempts, cancellation/restart/replay/audit failures, resource and latency distributions.
- [ ] Run separately authorized integration tests from section 12 plus retained deterministic regressions; attach original reports and hashes. Mock success is not model evidence.
- [ ] Independently review all four scorecards and unresolved failures. Record signed, durable reviewer identity, decision, scope, expiry and evidence hashes. No automatic activation from a passing CI status.

## D. Activation prerequisites

- [ ] Implementation separately authorized on an isolated branch; no second framework, no model-controlled effect tools, no warehouse/corpus mutation.
- [ ] Trusted tenant/reviewer identity, scoped capabilities, durable keys/nonces, maker-checker and restart-safe ledger/outbox design reviewed.
- [ ] Dedicated runtime authorization and capacity; no interference with Claude Code's current evaluation, no paid fallback, no silent model/tag substitution.
- [ ] Effective digest/configuration attestation, bounded async transport, cancellation and default-deny audit failure behavior proven.
- [ ] Explicit human authorization for limited read-only activation/deployment after evidence review. Keep disabled until that decision.

Completion of this checklist is a future review process. No unchecked item is implicitly satisfied by this specification.
