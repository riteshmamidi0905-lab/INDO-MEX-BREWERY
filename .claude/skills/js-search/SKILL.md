---
name: js-search
description: >-
  Find current US job openings that match Ritesh's qualifications and stated work authorization, rank them, and report each one's authorization terms and liveness honestly. Use when the user says "find jobs", "job search", "any new AI evaluation roles", "run the weekly job search", or asks what to apply to.
---

# js-search

Discovers and screens US roles. It **never applies, messages anyone, or logs into any site**.

## Read first
1. `~/.claude/jobsearch/profile.md` (private; template at `.claude/jobsearch/profile.template.md`). If missing, use the template and say so.
2. `.claude/linkedin/claims-register.md` for what the candidate can honestly claim.

## Hard rules
- **Work authorization is never inferred.** Read `work_authorization` from the profile. If `UNSET`, every result is `authorization_fit=UNKNOWN`, the posting's own sponsorship/citizenship/clearance wording is quoted, and the top of the report says the status is missing. Never say a role "matches" authorization when UNSET.
- **Active means verified, not assumed.** A role is `LIVE-VERIFIED` only if `verify_live.py` returned OPEN or a fetched page shows an apply control and no closed text. Anything found only through search snippets is `UNVERIFIED (search snapshot)`. Say which environment you ran in: the Claude cloud sandbox blocks ATS hosts, so there everything is UNVERIFIED until the user runs `python3 .claude/skills/js-search/verify_live.py URL...` locally.
- Do not scrape or automate LinkedIn. Use WebSearch/WebFetch on public company career pages and ATS boards (Greenhouse, Lever, Ashby, Workable), or accept URLs/text the user pastes.
- Never invent a role, company, salary, date, or requirement. Missing field = `not stated`.
- US only: exclude roles whose location is non-US or that require a clearance (candidate holds none).

## Procedure
1. Build 6 to 10 searches from the profile's target roles, in priority order: AI/agent engineering, LLM evaluation, AI reliability/safety, forward-deployed AI, AI/product analytics. Use `mode: standard` WebSearch with `site:`-style terms for the ATS domains; prefer postings seen in the last 14 days and note any date shown.
2. For each candidate, fetch the posting text if possible (WebFetch) and run `python3 .claude/skills/js-search/screen.py POSTING.txt --status <value from profile>` (use `UNSET` if unset). Include its evidence lines verbatim.
3. Dedupe against `~/.claude/jobsearch/applications.csv` (`js-track list`).
4. Score fit 0-5 against the **requirements as written** and the candidate's register-backed strengths; list the biggest honest gap per role (e.g. production LLM ownership). Do not inflate.
5. Output (max 12 rows, best first):

```
JOB SEARCH  <date>  profile: work_authorization=<value>  environment: <cloud sandbox | local>
#  company | title | location | pay (if stated) | posted | link-state | auth-fit | fit/5 | biggest gap
   auth evidence: "<verbatim quote or 'no statement'>"
NEXT: tell me which to save (js-track) or tailor (js-tailor). Nothing has been applied for.
```
6. Offer to save chosen roles with `js-track`. Do not save without a yes.
