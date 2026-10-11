---
name: nasha-sprint-close
description: Close a NASHA sprint: run all validators, check the diff, update README and roadmap, commit and push the branch, and write the report in the standard section order. Use at the end of every sprint.
---
# NASHA sprint close
1. `git status`, `git diff --stat`; no secrets (`bash tools/security_check.sh`), no stray caches (.cache/ is ignored).
2. Validators: `python3 tools/diet_audit.py`, `python3 tools/validate_repo.py`, `python3 tools/validate_site.py`, `python3 tools/t1_record.py`; rebuild the site (`python3 website/build.py`) only if site inputs changed and confirm `website/dist` diff is intended.
3. Scores: restate evidence X/95 and design Y/95 with before to after; explain any change by the exact criterion, or say unchanged.
4. Physical status line must remain true: "Chicken 65 Totopos: NOT PERFORMED" until real rows exist.
5. Update README sprint line and PROJECT-ROADMAP; commit with the attribution lines; `git push -u origin <branch>`; never merge, never open a PR, never deploy; website stays noindex.
6. Report order: Repository (start/end SHA, branch, push, merge, PR, deployment), what was done, tested vs installed, blocked, founder actions (only real ones), physical status, scores, next physical action. State the Figma originals deadline while it is open.

## Founder-view rule (D-80)
Start every sprint report with a FOUNDER VIEW of at most about 10 lines: WHAT CHANGED, WHAT I NEED FROM YOU, WHAT I CAN KEEP DOING WITHOUT YOU. The technical report follows. Run `bash tools/validate_all.sh` before closing and report its result.

