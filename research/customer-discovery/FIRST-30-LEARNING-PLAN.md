AGENT ANALYSIS - NOT PROFESSIONAL REVIEW - NOT EVIDENCE

# First-30 Learning Plan

**Status:** DESIGN of a learning process. No prospect has been contacted, no tasting has happened, no result exists. Extends `INTERVIEW-GUIDE.md` (interview flow, decision rules section 5), `responses-schema.csv` / `analyze_interviews.py` (interview data) and `validation/TRACTION-METRICS.md` (sales sessions). Does not replace them. Final plan owner: founder. Research-method and legal/consent questions: verify with a qualified researcher / Texas attorney (alcohol service, age checks, food allergy handling).

Goal: learn from the first 30 genuine prospective customers (not necessarily buyers) whether, why and at what price people would choose NASHA, and what confuses or repels them. Find problems, not precision.

## 1. Cohorts (PLANNING PROPOSAL - agent-proposed, founder to confirm)
Cohorts describe **food and drink familiarity or situation, not ethnicity, religion or class**. Never infer a cohort from name, appearance or accent; the person self-selects on a screener question ("Which of these describe you? pick all that apply"). One person has one **primary** cohort for counting (the one they pick as best fit) and any secondary tags.

| Cohort | Self-selected screener wording | Proposed n (AGENT-PROPOSED) | Why it matters |
|---|---|---|---|
| Indian-food familiar | "I cook, eat or order Indian food regularly" | 4 | Tests authenticity and respect concerns, spice/heat calibration |
| Mexican-food familiar | "I cook, eat or order Mexican food regularly" | 4 | Same, from the other side |
| Craft-beer familiar | "I visit a brewery/taproom about monthly or more" | 5 | Tests beer credibility and pairing value |
| Fusion-curious | "I like trying unusual food combinations" | 3 | Tests upside among early adopters (and whether they stay) |
| Austin casual diner | "I eat out weekly, not a beer or cuisine enthusiast" | 4 | Closest to the volume customer |
| Vegetarian diner | "I eat vegetarian or mostly vegetarian" | 3 | Tests whether veg is a full meal, not a side |
| Families | "I dine out with children under 12" | 4 | Tests kid fit, noise, timing, heat |
| Non-drinkers | "I do not drink alcohol (any reason; no reason asked)" | 3 | Tests NA pour and whether the place works without beer |
| **Total** | | **30** | |

- Mapping to the existing guide table (INTERVIEW-GUIDE.md section 2): craft-beer = its craft row; casual diner = its casual row; families = its parents row; vegetarian = its veg row; Indian/Mexican-familiar replace the heritage rows (familiarity, not identity). Founder may keep the heritage rows instead; if so, record which scheme was used before the first interview.
- With n of 3-5 per cohort, per-cohort findings are **directional only** (see CODING-SYSTEM.md rule). Cross-cohort patterns across the 30 are the main use.
- Overlaps are expected and allowed; record secondary tags. Do not recruit to fill a quota with someone who does not fit.

## 2. Recruitment rules
1. **Genuine prospects:** people who plausibly would visit a brewery-restaurant in Austin, recruited through channels the founder does not control socially (public events, partner venues, community groups, cold intercepts with permission). Channel to be chosen by founder; Lane A (needs people).
2. **Friends, family, colleagues, and anyone with a stake are separate.** Tag `relationship_flag` = `friend_family` or `founder_network` on every record. They may be interviewed for practice and rehearsal but are **excluded from the 30 and from every signal count**. If a friend's friend, tag `acquaintance`; report with and without.
3. No more than 1 person from the same household or friend group per cohort.
4. Record how each person was found (`recruit_channel`); no more than a third of the 30 from any single channel (planning proposal), to limit one-community bias.
5. Flag people who work in food, beer or hospitality (keep, do not exclude).
6. Consent first; recording optional; an incentive (if any) is for time, offered the same to everyone, never tied to answers. Anyone served alcohol must be 21+ verified by the legally required process (verify with a Texas alcohol attorney; no NASHA alcohol service exists today).
7. No personal data in the repository: respondent ids only (e.g. R-001). Contact details live in a consent-based store outside git.
8. Stop rule: not before each cohort has at least 3 people unless recruitment is failing, which is itself a finding to record.

## 3. What to ask (use the existing guide; this adds the tasting/commitment layer)
- Behaviour first (guide section 3A), concept second, hypotheticals last.
- At a real tasting: unprompted choice before any recommendation; then TASTING-FEEDBACK-FORM.md.
- Price: ask expected/fair price **open-ended before showing any price**; any price shown later is founder-set and recorded in the tracker as `price_shown_usd` with basis.
- Commitment: what would they do now (order, pre-order, leave contact, bring someone), and what would make them never return.
- Always: "What would make you not come?" and "Where would you go instead?"

## 4. What to observe (not only what they say)
- First dish/beer they point at, and what they do before asking (read menu, ask staff, look at others).
- Hesitation, questions asked, words they use for the food (their words, not ours).
- Whether they finish the item, share it, leave food, ask for water or milk (heat).
- Whether a non-drinker or child was served as well as the drinkers.
- Whether the group agrees or one person decides.
- Time spent deciding; any item skipped without comment.
Record behaviour in notes separately from stated opinion.

## 5. What NOT to lead people toward
- No pitch, no adjectives ("authentic", "unique", "amazing", "fusion masterpiece"), no explaining a dish before they react.
- Do not name a favourite, a bestseller, or "most people love..." Do not say what other participants said.
- Do not show a price before asking their expectation; do not offer round-number price menus as anchors.
- Do not ask yes/no "would you like..." questions as the main test; do not ask them to defend a no.
- Do not react to answers (no nodding approval, no disappointment). Silence is data.
- Do not steer cohorts by assumption ("as an Indian person, is this authentic?" is not allowed; ask everyone the same question about how the food compares with what they know).
- Do not promise anything (opening date, menu, price, availability): none exist.

## 6. What counts as signal vs what does not
Strength ranking (strongest first). Every entry needs a recorded reason in the person's words.

| Signal | Counts as | Notes |
|---|---|---|
| Paid commitment (purchase at a real event, pre-order, deposit) | Strong | Only if an actual price was charged and legally permitted to charge; record price and whether discounted |
| Unprompted dish choice | Moderate | Choice made before any recommendation; record what they chose and why |
| Price reaction | Moderate | Open expectation given before price shown, plus reaction to a founder-set price; "too high" is signal as much as "fair" |
| Return intent **with a stated reason and condition** | Moderate-weak | Stated intent, not behaviour; follow up later and log whether they actually returned |
| Actual return / referral that happens | Strong | Logged in repeat-intent-tracker.csv |
| Specific, costly confusion or objection | Strong (negative) | Counts equally; negative signal is the point |

**Does NOT count as validation:** compliments; "I would love that"; "sounds great"; "so unique"; any statement from friends/family/founder_network; survey answers with no cost or trade-off to the respondent; likes, follows or sign-ups without a stated reason; free-tasting enthusiasm without any choice or commitment; anything from SYNTHETIC-FORM-TEST data; the founder's own reading of "vibes". A tasting being free means a positive rating alone is weak; look for what they chose, left, would pay for and would return for.

## 7. How results are stored
| Data | Location | Rule |
|---|---|---|
| Interview answers | `research/customer-discovery/responses.csv` (schema `responses-schema.csv`); analyse with `analyze_interviews.py` | Real only; extend schema in a future change if needed (e.g. add `relationship_flag`, `recruit_channel`, `cohort`; not done here) |
| Tasting form responses | One filled form per person, transcribed to a future `tasting-responses.csv` (columns follow the form field names); paper originals kept outside git | Respondent id only |
| Purchase / conversion | `purchase-conversion-tracker.csv` | One row per respondent per event; links to `validation/traction-event-log.csv` by `session_id` when a sales session occurred |
| Return / repeat / referral | `repeat-intent-tracker.csv` | Stated intent logged at first contact; actual behaviour added at follow-up |
| Codes and quotes | Per CODING-SYSTEM.md | Quote tied to respondent id and cohort |
| Raw contact data | Outside git, consent-based | Never in repo |
Every row carries `data_source` (`real` / `dry_run` / `friend_family` / `SYNTHETIC-FORM-TEST`); analysis uses `real` and non-friend rows only. Report n, cohort, and method with every figure. The existing analyser reads only `responses.csv`; tracker analysis tooling does not exist yet (Lane B task when real rows exist).

## 8. Decision thresholds - TBD BY THE FOUNDER BEFORE THE FIRST INTERVIEW
The agent does not set them. Freeze each below (date and initials) before contacting anyone; moving them afterwards invalidates the learning.

| Question | Threshold | Action if met / not met |
|---|---|---|
| Share of 30 who can restate the concept correctly | TBD by founder | TBD |
| Share who make an unprompted dish choice and can say why | TBD by founder | TBD |
| Share who choose to pay or pre-commit when it is offered (non-friends only) | TBD by founder | TBD |
| Fair-price expectation vs the working model (cohort-level, directional) | TBD by founder | TBD |
| Stated return with a reason, and actual return at follow-up | TBD by founder | TBD |
| Any single objection named by how many people = design requirement or kill criterion | TBD by founder (guide section 5 suggests 8 of 30) | TBD |
| Non-drinker and family cohorts: would the place work for them | TBD by founder | TBD |
| Cultural-respect concerns raised by any cohort | TBD by founder; take to cultural advisors | TBD |
The existing section 5 thresholds in INTERVIEW-GUIDE.md are a prior draft by an earlier author; the founder should confirm or replace them at the same freeze.

## 9. Testing the forms
Synthetic or role-played responses **may be used only to test form mechanics** (columns, skip logic, whether a field is understood, whether analysis scripts run).
1. Every such record is tagged `SYNTHETIC-FORM-TEST` in `data_source` (and in the id, e.g. `SYN-001`) and states it is role-played.
2. Stored apart from real data in a separate folder (proposed: `research/customer-discovery/_form-tests/`), never in `responses.csv`, the trackers, or `validation/traction-event-log.csv`. The analyser self-test already uses a temp directory; follow that pattern.
3. Never counted as evidence, never quoted, never used for thresholds, numbers, investor material or readiness scores. Delete or quarantine after the mechanics are confirmed.
4. Friends role-playing a customer are `SYNTHETIC-FORM-TEST`, not `friend_family` real data; do not blend them.
5. Do not populate any respondent in the repo templates. No real respondent exists.

## 10. Biggest uncertainties
Whether any prospect can be reached without founder-network bias; whether a tasting can legally and safely happen (nothing cooked or brewed; food safety, allergen and alcohol rules need qualified professionals); whether a "paid commitment" can be offered at all before a legal sales pathway exists (verify with a Texas alcohol attorney / health authority).
