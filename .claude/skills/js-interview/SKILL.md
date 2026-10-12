---
name: js-interview
description: >-
  Prepare Ritesh for an interview for a specific role: likely questions, STAR-style stories drawn only from real projects, technical drills on agents/evals/reliability/analytics, and questions to ask. Use when the user says "interview prep", "prepare me for the screen", "mock interview".
---

# js-interview

Inputs: posting text, interview stage/format if known, `.claude/linkedin/claims-register.md`.

## Build
1. **Role read:** the 5 things the interviewer must come away believing, from the posting.
2. **Stories (5 to 6):** each from register entries only, in Situation/Task/Action/Result/**Limit** form. The Limit line is mandatory (synthetic data, one small model, same-author). Strongest candidates: MT-02 (C5), MIXED MAREF verdict (C7/C8), Weir ranking flip (C10), Copilot 10/22 interface failures vs held invariants (C2). For professional stories use P1-P4 wording as on the résumé; mark details Ritesh must supply as `{{ask Ritesh}}`. Never invent a result, team size, or timeline.
3. **Technical drills** matched to the role: agent loop/state/approvals; tool-call schema validation; eval design (rubrics, hard gates, held-out splits, false-alarm rates, judge bias); information-flow vs action safety; retrieval (pgvector, hybrid + RRF); A/B (power, MDE, CUPED, FDR); SQL/window functions. Give 8 questions with answer outlines grounded in his own repos.
4. **Hard questions, honest answers:** "Is any of this in production?" (No: synthetic, not deployed.) "Did MAREF beat baselines?" (No, MIXED.) "Why only a 4B model?" etc.
5. **Questions to ask them** (6), and a salary/authorization-neutral logistics checklist. Do not state or guess work authorization; the user answers those questions himself.
6. **Mock mode:** ask one question at a time, wait for his answer, critique for specificity and unsupported claims.
