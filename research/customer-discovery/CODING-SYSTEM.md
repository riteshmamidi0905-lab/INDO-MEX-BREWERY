AGENT ANALYSIS - NOT PROFESSIONAL REVIEW - NOT EVIDENCE

# Lightweight Qualitative Coding System

**Status:** DESIGN. No responses exist. Applies to free-text fields in `responses.csv` (`barrier_*`, `quote_*`, `regular_if`, `never_return_if`, `notes`), TASTING-FEEDBACK-FORM.md open lines and tracker reason fields. Extends the existing `barrier_*` convention; existing analyser counts raw barrier strings, so use the code names below as the barrier text for them to be tallied.

## 1. Codes (a quote may carry several; a code means the respondent said or clearly showed it)
| Code | Definition |
|---|---|
| fusion_makes_sense | Sees the Indian + Mexican link as natural or coherent, with a reason |
| fusion_unclear | Cannot see why the two belong together |
| gimmick | Says or implies the concept, dish or beer feels like a trick or trend |
| culturally_respectful_concern | Worry that the food or story is disrespectful, inauthentic or appropriating, about either cuisine. Escalate to cultural advisors |
| culturally_respectful_positive | Says it feels respectful or well-grounded, with a reason |
| pairing_adds_value | Pairing improved dish or drink, or they want guidance, with a reason |
| pairing_no_value | Pairing unnecessary or confusing |
| price_too_high | Names a price or says cost is a reason not to come/buy |
| price_fair_or_low | Fair or bargain, with their own reference |
| confused_by_name | Does not understand, cannot say or remember the name, or misreads what the place is |
| confused_by_menu | Cannot understand dishes or how to order |
| vegetarian_need | Needs a full vegetarian meal, not a side; or says veg options matter to the visit |
| family_need | Child fit: kid food, noise, seating, shade, timing |
| NA_need | Wants or needs a good non-alcoholic option |
| heat_concern | Spice level too high or too uncertain |
| allergy_trust | Allergy, dietary labelling or age-check trust (positive or negative) |
| authenticity_comparison | Compares with food they know (their words, any direction) |
| convenience_barrier | Distance, parking, hours, shade/heat, wait |
| substitute_named | Names a competitor or alternative |
| unprompted_choice | Chose a dish/beer before any recommendation (code the item too) |
| paid_or_precommitted | Paid, pre-ordered or left a deposit (also in tracker) |
| return_with_reason | Stated return with a reason; code the reason |
| no_return_reason | Stated reason they would not return |
| compliment_only | Praise with no reason, choice or commitment (recorded, does not count as signal) |
| other_new | Anything unmatched; review weekly and promote to a code if it recurs |
Add a sentiment tag (+ / 0 / -) per quote. Codes added later are logged with date and the quotes that triggered them; earlier rows are recoded.

## 2. How to code
1. Code from verbatim text or notes made the same day; keep the original wording.
2. First pass: read all responses of one question before moving to the next, to stay consistent.
3. One row per coded quote in a future `coded-quotes.csv`: `quote_id, respondent_id, cohort, relationship_flag, data_source, source_field, quote_verbatim, code, sentiment, coder_id, date`.
4. Code the respondent's meaning, not what the founder hoped; if unsure, use `other_new` and flag.
5. Friend/family/founder_network and SYNTHETIC-FORM-TEST rows are coded for mechanics only and excluded from counts.

## 3. Two-coder check
Where possible, a second person (not the interviewer, ideally not the founder) independently codes at least the first 10 respondents or 20 percent of quotes, whichever is larger. Compare: agreement percentage per code; discuss every disagreement; update definitions, not just the answer. If agreement is below a level the founder fixes beforehand (TBD by founder), tighten definitions and recode. If no second coder exists, say "single coder" in every report.

## 4. Storing quotes
Quote = verbatim, with respondent id (R-###), cohort, relationship flag, date and field. Names, faces, contact details never enter the repository. Mark paraphrase as paraphrase. Keep one quote file; do not create a "best quotes" file separate from the full set.

## 5. Avoiding cherry-picking
- Report every code with its count, including those that hurt the concept; negative codes listed first.
- For each theme, show at least one disconfirming quote if any exist, and say how many did not fit.
- Before showing a quote externally, count how many respondents said something similar and how many said the opposite.
- Do not quote `compliment_only`, friends/family or synthetic items as support.
- Record the full list of codes before reading results, and note any code added after seeing data.
- Founder does not select quotes alone; second reader or coder reviews the selection.

## 6. Small-sample rule
**n below 8 per cohort is directional only.** Report as "X of n said...", never percentages, never cohort comparisons as findings. With the proposed cohort sizes (3-5), every cohort-level result is directional; pooled results across the 30 are exploratory, not statistically representative. Report n, cohort mix, recruitment channel and share of friend-network exclusions with every figure.
