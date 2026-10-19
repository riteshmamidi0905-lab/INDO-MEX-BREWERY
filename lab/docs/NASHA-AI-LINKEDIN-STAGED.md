# NASHA AI — Five-post LinkedIn launch (STAGED, NOT PUBLISHED)

**Publishing gate:** Re-check current CI, security integration and portfolio preview before publication. NASHA is an independent, synthetic-data engineering project, not an operating brewery. Do not represent plan-only role handoffs as executed agents. Do not imply THE WEIR integration is verified until an end-to-end enforcement test passes.

## Post 1 — Introducing NASHA AI
I've been building NASHA, an Indo-Mexican brewpub concept, as a practical environment for AI and data engineering.

The engineering question is more interesting than making a chatbot: how do you combine evidence, operations data, business decisions, approvals and security without allowing an AI system to act beyond its authority?

NASHA AI is my evolving answer. It includes a tested operations lab, evaluation and retrieval components, a twelve-role architecture, and structured workflow prototypes. The data is synthetic, and the business isn't operating commercially.

I'm documenting what actually works, what fails, and what still needs to be built.

**Visual:** Dark-basalt NASHA AI wordmark, three evidence-status labels, simple operations-to-approval diagram.
**Video (20 s):** Concept → engineering lab → existing verified tests → current prototypes → next security integration.

## Post 2 — Meet the Twelve Roles
I designed twelve specialist roles for NASHA AI, but I deliberately didn't create twelve independent LLM agents.

ATLAS handles strategy, BREWMASTER brewing intelligence, FORGE menu development, SENTINEL inventory, MERIDIAN procurement, PULSE analytics, ECHO customer insights, SPARK marketing, NEXUS operations, GUARDIAN compliance, SCRIBE knowledge, and LUMEN evaluation.

Some are better implemented as deterministic services. Others need retrieval, supervised orchestration, or human review. The role contracts are in code; a defined role is not the same as a deployed agent.

**Visual:** Twelve geometric cards, grouped by orchestration, deterministic services, and proposals.
**Video (25 s):** Show three clusters and explain why deterministic services are preferable for calculations and authorization.

## Post 3 — Collaboration Without Fake Autonomy
A seasonal beer concept creates dependencies: research, ingredient requirements, synthetic inventory, supplier comparison, estimated cost, food pairing, quality checks, and founder approval.

I built a structured handoff planner for this flow and two others: inventory/procurement and customer intelligence/marketing. The current planner is intentionally **plan-only**; executable service handoffs and end-to-end evaluations are still being built.

That distinction matters. A workflow diagram is a design. An execution trace is evidence.

**Visual:** Annotated dependency graph, with a clear PLAN-ONLY badge.
**Video (30 s):** Replay a synthetic handoff plan, then highlight the missing execution boundary.

## Post 4 — Securing Agents With THE WEIR
One of the biggest challenges in agentic systems is deciding who has authority to do what.

THE WEIR is a separate deterministic MCP information-flow security gateway. NASHA has its own local permission and human-review controls. The next integration milestone is proving that every protected NASHA tool call traverses THE WEIR's actual enforcement path.

The target is simple: unauthorized actions never execute; approvals are scoped, time-limited and consumed once; decisions are auditable. **Cross-repository enforcement is not yet verified.**

**Visual:** Proposal → THE WEIR → allow / approve / deny → human review → action, labeled TARGET ARCHITECTURE.
**Video (30 s):** Contrast a proposed action with an authorized execution; don't show a fictional passing integration test.

## Post 5 — What Building NASHA AI Taught Me
Three engineering lessons have stood out.

First, synthetic benchmark scores need context: a duplicate detector can perform perfectly on injected examples while still confusing legitimate close-in-time transactions.

Second, reproducible evidence is more valuable than impressive but unverified claims.

Third, agent autonomy should be earned. Use deterministic rules for permissions, calculations, and release decisions; use supervised AI where investigation and synthesis add value.

This project is ongoing. I'm keeping the code, evaluations, failures, and limitations visible as it develops.

**Visual:** Three lesson cards: AMBIGUITY / EVIDENCE / AUTHORITY.
**Video (30 s):** One synthetic DQ ambiguity, one CI regression, and one approval boundary.

## Launch checklist
- [ ] Latest engineering branch CI green, with exact test count recorded.
- [ ] Preview accessibility, keyboard, mobile and reduced-motion tested.
- [ ] Verify every badge and metric against current code and CI.
- [ ] Replace target security architecture graphics with actual traces only after real tests pass.
- [ ] Generate/review graphics and videos; no asset is claimed to exist yet.
- [ ] Obtain explicit approval before publishing.
