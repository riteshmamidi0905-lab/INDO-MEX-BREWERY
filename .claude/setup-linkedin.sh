#!/usr/bin/env bash
# Link the repo's LinkedIn profile files to where the li-* skills read them (~/.claude/linkedin),
# and create the PRIVATE job-search data dir (~/.claude/jobsearch). Nothing here is committed.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$HOME/.claude"
if [ -e "$HOME/.claude/linkedin" ] && [ ! -L "$HOME/.claude/linkedin" ]; then
  echo "~/.claude/linkedin exists and is not a symlink; leaving it alone. Copy voice.md etc. manually." >&2
else
  ln -sfn "$repo/.claude/linkedin" "$HOME/.claude/linkedin"; echo "linked ~/.claude/linkedin"
fi
mkdir -p "$HOME/.claude/jobsearch"; chmod 700 "$HOME/.claude/jobsearch"
[ -e "$HOME/.claude/jobsearch/profile.md" ] || cp "$repo/.claude/jobsearch/profile.template.md" "$HOME/.claude/jobsearch/profile.md"
echo "private job-search dir: ~/.claude/jobsearch (edit profile.md; never commit it)"
