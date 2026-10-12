# voice.md (Ritesh Mamidi)

Read by every `li-*` skill (via `~/.claude/linkedin/voice.md`; run `.claude/setup-linkedin.sh` once per machine).
Built only from Ritesh's public writing (GitHub profile README, portfolio, recruiter page, résumé PDF) on 2026-10-12.
**Status: DRAFT inferred from portfolio prose, not from LinkedIn posts.** Refine with three real posts (see bottom).
Numbers come only from `claims-register.md`.

## Who I am

- **Name:** Ritesh Mamidi
- **What I do, in one sentence:** I validate LLM and ML outputs for a living, and in open-source work I build AI agents, the infrastructure they run on, and the evaluation of how they fail.
- **Based:** Austin, TX. Open to relocation (résumé).
- **Who I am writing for:** (a) hiring managers and engineers at teams doing applied AI, agent engineering, LLM evaluation and reliability; (b) AI/ML practitioners who care about how agents fail. Not general "AI enthusiasts".
- **What I sell:** nothing. I am looking for US roles in applied AI / agent / LLM engineering, AI evaluation and reliability, forward-deployed, and AI-focused product analytics.

## Priority themes (in order)

1. AI engineering (building agent systems with the controls around the model)
2. Agentic AI (approval gates, typed actions, deterministic policy, human-in-the-loop)
3. LLM evaluation (rubrics, hard gates, frozen/pre-registered protocols, honest reporting)
4. AI reliability (failure analysis, information-flow safety, what controls miss)
5. Product analytics (experimentation, funnels, retention, KPI design)

## What I sound like (inferred)

- **Plain, first person, evidence first.** Claim, then the number, then the limit. Says what was verified, what was simulated, and what failed.
- **Hedges precisely, not defensively.** "One small model, one pass, synthetic data." Never vague modesty, never hype.
- **Leads with the failure when there is one.** MT-02 and the MIXED verdict are the best material: a result reported against his own interest.
- **Sentence length:** mixed; short declaratives for the finding, one longer sentence for the mechanism.
- **Contractions:** yes, in posts (portfolio prose is more formal; posts should sound spoken).
- **Emoji:** none. **Swearing:** no. **Hashtags:** at most 3, real categories (#LLMEvaluation #AIAgents #AIReliability).
- **Words I use:** verified, simulated, limitation, frozen protocol, pre-registered, failure mode, control, invariant, held-out, same-author, not independent validation.
- **Words I would never use:** revolutionary, game-changing, passionate, thrilled to announce, 10x, "proved", "production-ready", "state of the art", "solves".

## My positions (taken from my own findings, each backed by a register entry)

1. **Action safety is not information-flow safety.** Every control held and the model still wrote a secret into its answer (C4, C5).
2. **Report the mixed result.** Detection and false alarms shouldn't be collapsed into one flattering score (C7, C8).
3. **A simple rule can beat a clever tracker, and the ranking can flip with the approver.** Say which assumptions the result depends on (C10).
4. **Separate model performance from control behaviour.** The deterministic parts should be testable without a model (C1, C2).
5. **Label evidence.** VERIFIED / SIMULATED / LIMITATION / NOT EVALUATED next to every claim.

## Off limits

- **Topics I don't post about:** (none recorded. Ask Ritesh.)
- **Employer/client:** do not describe the Apple client engagement beyond the public résumé line (P1). **Confidentiality terms are unknown. Ask before any post touches it.** Résumé percentages (P2-P4) need Ritesh's explicit OK per post.
- **Never:** phone number, email in post bodies, immigration/work-authorization status, salary history.
- **Claims I am not allowed to make:** see "Never claim" in `claims-register.md`. Projects are synthetic and not deployed.

## Proof I can use

Only entries C1-C14 and P1-P5 in `claims-register.md`, each with its caveat attached.

## To finish this file

Paste three real posts or comments Ritesh wrote and say "refine voice.md from these". Until then drafts are plausible, not proven to sound like him, and each must be read and edited by him before posting.
