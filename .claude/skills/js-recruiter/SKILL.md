---
name: js-recruiter
description: >-
  Research the company and the people behind a role (hiring manager, recruiters, team) from public sources and draft outreach for Ritesh to review. Use when the user says "research this company", "who is the recruiter", "draft a message to the hiring manager".
---

# js-recruiter

## Research (public sources only)
Company's own careers/blog/docs, press, GitHub org, public conference talks, and the posting itself. **No LinkedIn scraping, no logging in, no guessing email addresses, no data brokers.** If a name is not on a public page, say "not found" and tell the user how to look it up themselves.

Report: what the company builds, the team/role context, evidence of AI-evaluation/agent work (cite URLs), recent news, red flags (layoffs, vague role, repost churn), and 3 specific talking points tied to the claims register.

## Outreach drafts
- Connection note <= 200 characters (count shown) and one follow-up. Use `/li-dm` rules, which are manual-send only. Never fabricate a mutual connection, familiarity, or having read something the candidate has not read.
- One specific, true reason to reach out (a post, release, role detail). If there is none, say so and advise against messaging.
- Run drafts through `/li-human` (style cleanup; no claim of undetectability).
- **Gate:** nothing is sent. The user sends every message by hand. Max 20 invites/day, no sequences.
- Record contact intent in `js-track` notes only after the user confirms they sent it.
