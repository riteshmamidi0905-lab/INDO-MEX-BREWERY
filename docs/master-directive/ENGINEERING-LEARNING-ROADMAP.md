# Engineering learning roadmap

Principle: Claude-generated working code is never evidence of your skill. A level is recorded only for work you did yourself, with the evidence listed in SKILL-EVIDENCE-MATRIX.md.

## Levels
1 not started; 2 learning; 3 can implement with guidance; 4 can implement independently; 5 can debug and explain tradeoffs; 6 can design and defend production-style solutions.

## Module template (every module has all seven parts)
A theory; B small independent implementation; C where it appears in this lab (file paths); D a failure to debug; E design tradeoffs; F interview defence questions; G evidence record (what you did unaided, date, link).

## Sequence (the first three are started by the diagnostic and the existing lab)
1. **Now:** take `python -m learning.diagnostic run --out learning/results.jsonl` (27 items, 9 areas, no tools). Return the results file; Claude reviews the short answers against the rubric in conversation and records only observed performance.
2. SQL + data quality against `career/p4-analytics-mart-clean` (mart, 24 library queries).
3. FastAPI + auth + idempotency against the P5 service.
4. RAG evaluation and the planner experiment in `lab/docs/`.
5. Agent safety: trust gateway, THE WEIR approvals, negative tests.
6. Docker/CI, observability, system design, FDE discovery exercises.

Existing private material (not in this repo): an interview question bank and three unassisted assessments, prepared and not administered.

## Journal
`LEARNING-JOURNAL.md`: what was built, why, what you did yourself, what Claude did, what failed, what remains unverified.
