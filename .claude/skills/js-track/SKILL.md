---
name: js-track
description: >-
  Track job applications, statuses and follow-ups in a private local CSV, and show what is due. Use when the user says "track this application", "what's due", "update my pipeline", "log that I applied".
---

# js-track

Backed by `tracker.py` in this folder (stdlib, local only, file `~/.claude/jobsearch/applications.csv`, mode 600, outside any git repo).

```bash
python3 .claude/skills/js-track/tracker.py add --company "X" --role "Y" --url "U" --source "js-search"
python3 .claude/skills/js-track/tracker.py set 3 --status READY_FOR_YOUR_APPROVAL --follow-up 2026-10-20
python3 .claude/skills/js-track/tracker.py set 3 --status APPLIED --approved   # only after the USER says they submitted it
python3 .claude/skills/js-track/tracker.py list | due | show 3
```

## Rules
- It records; it never submits, emails, or contacts anyone. `APPLIED` is refused without `--approved`, which you only pass after the user confirms they submitted it themselves.
- Never mark a status the user did not report. Follow-up suggestions: 7 days after APPLIED, 5 business days after an interview; the user decides.
- In the Claude cloud sandbox this file is ephemeral (the container is reclaimed). Say so, and tell the user to run locally (`.claude/setup-linkedin.sh`) for durable tracking.
- Never write tracker contents into a git repo or a public artifact.
