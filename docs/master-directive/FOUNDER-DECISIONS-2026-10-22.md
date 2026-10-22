# Founder decisions received 2026-10-22 (as stated in the session; recorded here, not yet entered in docs/decisions/DECISIONS.md)

1. NASHA is the intended name; keep it a WORKING name per D-79/D-80 until trademark and legal clearance; no public launch, advertising or commercial representation as a cleared brand; develop locally on isolated branches.
2. Core 5 menu and Chicken 65 Totopos stay intact. Add Chicken Tikka Nachos, Nawaabi Enchiladas and Mango Habanero Gobi as R&D candidates (not replacements); check duplicates; keep D-54 (no beef or pork); no claim of physical testing.
3. Approved for concept development: BADSHAH (mango juicy IPA), PAAPI (hefeweizen), Hoodie 01 The Courtyard, Hoodie 02 Two Worlds, a small set of original graphic tees. No third-party artwork; no publication of NASHA images.
4. Simulation scale approved with safeguards: 14 fictional locations, 24 months, 2-3 M synthetic transactions, ~150,000 fictional loyalty profiles, ~450 fictional employee records; 3-site baseline preserved; configurable; deterministic; runs on local hardware.
5. Unmerged analytics mart, hardened service and reliability branches: inspect, compare, test, then integrate only into a NEW isolated development branch. Protected/production branches untouched.
6. No push, merge to production, deploy or publish without explicit approval.
7. Skills stay "not assessed" until Ritesh personally completes the diagnostic. Nothing is answered or marked complete on his behalf.
8. Creative and voice tooling (Runway, Wispr Flow, text-to-speech) to be investigated; no account connection or paid generation without authorization; no voice cloning.

## Consequences found by the duplicate and conflict check (open for the founder)
- Mango Habanero Gobi already exists (D-84, Core 5 row 4, id `gobi-taco`). Treated as the existing item, not a new row; new ideas become test variables.
- Chicken Tikka Nachos overlaps Chicken 65 Totopos; the word "nachos" is barred in guest copy and GENERIC_NACHOS is a D-74 failure gate. Logged as BACKLOG, working label only; run only after Session 1.
- BADSHAH is recorded as a HEFEWEIZEN (phase-one/05) with a living-person stage-name flag; a mango IPA re-assigns the name. B-2 (no IPA at opening) and Monsoon Fruit Wheat (mango) overlap.
- PAAPI duplicates the SONA hefeweizen slot, reads as "sinner" in Hindi/Urdu/Punjabi contexts and is unscreened. Treat as a candidate name only.

## Second set of decisions (same day, Phase 2 authorization)
- BADSHAH keeps its existing hefeweizen identity. The mango juicy IPA is a separate experimental concept with a WORKING NAME (this repository uses "AMBA HAZE", unscreened; replace freely). PAAPI is an internal naming candidate only; research its linguistic, cultural and trademark implications; never publish it as finalized.
- Core 5 preserved; Mango Habanero Gobi stays the existing appetizer concept; Chicken Tikka Nachos stays an R&D candidate (overlaps Chicken 65 Totopos; "nachos" conflicts with guest-copy terminology).
- Push authorized ONLY for `career/integration-review` to the existing repository for CI (done; the repository is PUBLIC, content was identical to branches already public, no deploy path). No merge to any production branch, no deploy, no publication.
- Runway means https://runwayml.com/ (not runway.team); Wispr Flow means https://wisprflow.ai/ (dictation, not the meetings connector). No account connection and no paid generation without approval.
- Phase 2: data platform, business intelligence, product analytics, website collection pages, learning modules; all synthetic data labelled.

## Creative direction decision (2026-10-22, later in session)
- **Direction A "The Courtyard"** provisionally selected as NASHA's primary identity **for development only** — not final, not cleared, not for launch. D-66 stays at EXPLORATION until Ritesh reviews the refined board.
- **Direction B** kept as a botanical/illustration language for merchandise and secondary packaging (never a primary logo); small-size problem fixed by a simplified leaf cut.
- **Direction C** preserved as inspiration for nightlife/event campaigns only.
- **Photorealistic generation:** only free, no-subscription generators may be used; none reachable from this environment (see `PHOTOREAL-BLOCKER.md`). No spending.

## Wordmark and plate decisions (2026-10-22, evening)
1. **Original Courtyard wordmark = provisional primary logo** (still not final; D-66 stays EXPLORATION; no trademark search).
2. **Glass-A G1 approved for further development as a large-format alternate** on beer cans, glassware and architectural signage. **Not below 32 px cap height** (founder rule; my own test showed it gets busy at ≤ 24 px). **G2 stays exploratory.**
3. brand-v3 palette and the verified vector masters are preserved exactly (`brand/BRAND-GUIDELINES-v3.md`).
4. Both ChatGPT-generated boards (2026-10-22, plan not independently verified) are exploratory art-direction references only.
5. **Option 1 chosen:** the founder will supply clean, unbranded photorealistic source plates generated through ChatGPT (BADSHAH can + wheat-beer glass, AMBA HAZE can + IPA glass, Court Brewhouse exterior, THE COURTYARD hoodie, Mango Habanero Gobi). Plates must contain no logos, readable text, packaging claims or brand graphics; NASHA vector artwork is applied only at compositing. Only approved product information is used; no invented ABV, volume, tasting results, ingredients or certifications. Every generated image is recorded as a conceptual AI-generated asset, not a photograph of any existing NASHA product or location.
