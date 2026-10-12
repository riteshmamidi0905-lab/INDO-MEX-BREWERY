---
name: js-tailor
description: >-
  Tailor Ritesh's résumé bullets, cover note and a keyword-gap list to one specific job posting, using only facts in the claims register. Use when the user says "tailor my resume for this job", "cover letter", "match my resume to this posting".
---

# js-tailor

Input: the posting text (user pastes, or from `js-search`) and the base résumé facts in `.claude/linkedin/claims-register.md` (P1-P5, C1-C14).

## Rules
- **Only reorder, emphasise, and rephrase real facts.** No new employers, titles, dates, tools, metrics, certifications, or scale. A requirement the register does not support goes in **GAPS**, never into the résumé.
- Carry caveats: independent projects are synthetic and not deployed; label them "independent open-source". Résumé percentages (P2-P4) appear exactly as on the résumé ("reported") and never inflated.
- Mirror the posting's vocabulary only where it truthfully describes the same thing (e.g. "evals" for LLM evaluation). Never claim a tool the candidate has not used.
- Do not state or imply work authorization. Do not include the phone number in drafts shown on screen.
- ATS-safe: plain text, standard headings, no tables or columns.

## Output
1. **Match table:** requirement | evidence (register ID) | strength (strong/partial/none).
2. **Tailored summary + 5 to 7 bullets** (each tagged with its register IDs in a trailing comment `[C3, C5]` for checking; remove the tags before sending).
3. **Cover note** (150 to 220 words), run through `/li-human` for style cleanup only (no claim of undetectability).
4. **GAPS** and how to address them honestly (e.g. "no production LLM ownership: say so, point to MT-02 as a reliability finding").
5. **Approval gate:** save to `~/.claude/jobsearch/private/` only on request; the user reviews and submits themselves. Offer `js-track set ID --status READY_FOR_YOUR_APPROVAL`.
