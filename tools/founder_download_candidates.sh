#!/usr/bin/env bash
# FOUNDER: run this on YOUR computer (not in the cloud sandbox, whose proxy blocks figma.com) before 2026-10-18.
# It downloads the 10 generated candidate PNGs into visuals/archive/candidates/ with canonical names, then prints SHA-256 checksums.
# Then commit/upload the files and ask for: python3 tools/review_candidates.py
set -u
DIR="${1:-visuals/archive/candidates}"; mkdir -p "$DIR"; B="https://www.figma.com/api/mcp/asset"
get() { name="$1"; id="$2"; if [ -e "$DIR/$name" ]; then echo "SKIP (exists, not overwritten): $name"; return; fi
  curl -fsSL -o "$DIR/$name" "$B/$id.png" && echo "OK $name" || { echo "FAILED $name (URL may have expired; see GENERATION-LOG.md)"; rm -f "$DIR/$name"; }; }
get A1-exterior-bluehour-c1.png 7b936b6a-bf5f-4d9d-825c-271a985453bb
get A2-interior-c1.png 3da5c76c-de6c-4f3a-936c-903f1c64f64b
get A3-bar-c1.png 5ac9e101-d7fd-4e52-9dc6-294233ca5dad
get A4-fire-kitchen-c1.png bb4aedbc-a236-46e8-a60e-af7ac8600fa4
get A4-fire-kitchen-c2.png a9f35477-e73b-4fe5-a21d-b06403f0c9e6
get A5-patio-evening-c1.png e6d383dc-5c4d-4a2b-ab75-bb0612983ab7
get A6-entrance-c1.png d9545d4b-1e14-4ea1-bc49-af98d134c8a9
get B1-chicken65-hero-c1.png a44f828b-ec6a-47fe-b7fd-a5bf282264e6
get B1-chicken65-truth-c1.png d5c2cde2-c80a-4b66-95ca-97be95e69980
get C6-gate-beer-family-c1.png e25ee2ee-c47e-48fd-87d2-6218202e9120
( cd "$DIR" && (sha256sum A*.png B*.png C*.png 2>/dev/null || shasum -a 256 A*.png B*.png C*.png) )
