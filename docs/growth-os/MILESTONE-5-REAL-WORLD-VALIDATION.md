# Milestone 5: real-world validation, model execution and multi-industry proof

Starting state: engineering `480712f`, portfolio `5780dad`. All data is synthetic except the clearly labelled supplier research leads. No supplier was contacted, nothing was ordered or published, no money was spent, and nothing was pushed.

## 1. Model execution: not achieved, and exactly why

**No language model produced any output in this repository.** The live test (`tests/test_growth_model_live.py`) is skipped and the release gate reports it as unverified, so the gate verdict stays `REQUIRES_REVIEW`.

What was tried, within the permissions given: a local OpenAI-compatible runtime (Ollama, `AP_OLLAMA_BASE_URL`) is not installed and cannot be reached; the environment network policy refuses `huggingface.co` and its CDN hosts, so no model weights can be downloaded; the only model credentials visible belong to this session and were not reused; paid providers are refused by `model_boundary.provider_permitted` unless a person sets `NASHA_ALLOW_PAID_MODEL=1`.

What is ready: `tools/live_model_validation.py` probes the runtime, runs the live test, and writes `results/model-validation/live.json` with `executed: false`, the reason, and the decision needed (it sets `executed: true` only if a runtime answered and the live test passed). The model-output boundary, with 25 scripted cases and 10 rule mutants, is evaluated in Milestone 4 and is unchanged. Scripted cases are test doubles, not model behaviour.

**Smallest founder decision:** allow outbound access to `huggingface.co` and its CDN hosts in the environment network policy (a small instruct model can then be served locally), **or** provide an approved OpenAI-compatible endpoint in `AP_OLLAMA_BASE_URL`, **or** approve a capped paid key. Then run `NASHA_LIVE_MODEL_PROVIDER=ollama python tools/live_model_validation.py`.

## 2. Real-world supplier research

`nasha_lab/growth/data/real_suppliers.json` holds 12 real Austin-area / Texas / national food, dairy, grain and brewing-ingredient businesses (5 shortlisted), found by public web search on 2026-10-23, with source URLs and per-record limitations.

**Verified from a primary page read: 0.** The network proxy refused every supplier and government host (17 hosts, listed in the dataset), so no official page could be opened. Each record carries an evidence tier shown in the UI:

| Tier | Meaning | Count |
|---|---|---|
| primary_page_read | the official page was opened and read | 0 |
| official_domain_snippet | the official domain appeared in a search result; the page was not opened | 5 |
| secondary_only | only directories, press or encyclopedia mentions | 7 |

A database constraint requires a website, a source and a verification date before a record can be marked verified, so none could be. No contact detail, price, quote or partnership is recorded for any real business, and the database rejects e-mail addresses and phone numbers. To complete verification, someone with unrestricted network access opens each official site and records the page, date and what it states.

## 3. A second industry on the same platform

Meridian Fitness (an existing synthetic tenant) launches a boutique studio with: a business profile, a start-up budget with itemised equipment, fit-out, technology and pre-opening costs, 7 equipment/service/consumable requirements, six synthetic fitness suppliers, financial scenarios, a procurement recommendation ($33,190.00, equal to a hand calculation of 3,319,000 cents), human approval by a different person, a project-state transition and an audit history. Hospitality recipes play no part.

What changed in the platform: one generic table (`project_requirements`, migration 111, with RLS, audit guard and grants like every other table), `industry_profiles.py` (needs source and wording only), requirement-driven procurement, a supplier classification vocabulary for fitness, and neutral wording. What did **not** change: authorisation policy structure, audit model, workflow engine, THE WEIR tool contract, database role model. The shared-architecture evidence lists the 27 tables both tenants use and the profile fields that differ.

## 4. Evaluation, with development and held-out sets separated

* **Supplier intelligence.** Development set (rules were tuned against it): dedupe 22 cases, precision 1.0 / recall 1.0; classification 16/16; service area 14/14. **Held-out set** (written after the rules were frozen at commit `168fdb5`, not used to tune them): dedupe 22 cases, precision 1.0, **recall 0.67 (4 misses: name variants such as "Hill Country Dairies" vs "Hill Country Dairy")**; classification 23/24 (**1 miss:** "Fitness studio fit-out contractor" classified as fitness equipment); service area 12/12. The misses are pinned by tests and were not fixed afterwards, so the held-out figures remain honest. The sets are small and author-labelled: they support no general-accuracy claim.
* **Financial model.** Development cases plus 4 held-out cases worked by hand (two products with unequal mix; price rise with discount and elasticity; funded start-up plan; loss-making small budget): all fields match.
* **Generalisation to a second industry.** 9 hand-worked cases; 5 mutants (requirements ignored, recurring needs not scaled by period, one-time needs scaled by period, recipes forced on every industry, equipment given a reorder point), all killed.
* **Authorisation matrix.** Every operation × every role in both businesses against a table written from the intended policy (108 checks, all correct), plus 6 policy-widening mutants, all killed. Cross-tenant, role-refusal, concurrency (parallel requests and approvals in the studio) and tamper tests from earlier milestones remain.

## 5. Product

One app, one workspace switcher (NASHA / Meridian Fitness). The switcher signs the same demo user in to the other tenant with that tenant's own key; the two workspaces share nothing. Wording, the requirements card, and start-up categories come from the industry profile. Supplier cards show the evidence tier. Business and Engineering views read the same records. Phone-width layout and axe checks pass for both businesses.

## 6. Limitations

No model run; no supplier verified from a primary page; no real price or quote; the evaluation sets are small and author-labelled; the studio is a synthetic case study, not a business; remote CI has not run (`NOT_RUN`); the demo passcodes are development credentials.
