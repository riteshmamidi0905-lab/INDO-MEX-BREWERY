# MVP path and investor-readiness gap (AI planning analysis, not legal or financial advice)
Source: a hospitality-strategist AI agent working from the repository (T4 reasoning; not a qualified review). All legal items are orientation only: every row of `docs/regulatory/REGULATORY-MATRIX.csv` is T1 with no primary page read, and each item marked VERIFY needs a Texas alcohol attorney or the health authority. Nothing here is a forecast; no forecast numbers are invented; thresholds shown (8 or more tasters, 30+ interviews) are agent-proposed planning thresholds, not sourced. Evidence 4/95, design 43/95.

## 1. What is the cheapest legitimate test that yields the most useful evidence?
**A small food-only tasting (free or cost-shared, no alcohol) from a permitted commissary kitchen, run after cooking Sessions 1-5.** Any charge, ticket or deposit is a sale and needs the health-authority and attorney answers first (Q-09, Q-10, Q-05). It would yield cooked-food results, price reaction, sensory scores and a real cost sheet. It uses commercial stand-in beers only if an attorney clears serving them; otherwise serve non-alcoholic pairings and wait for a licensed brewery partner for beer. It is not a licensed sales event.

| Path | Evidence it could generate | Cost class | Alcohol-law dependency | What it cannot prove |
|---|---|---|---|---|
| Commissary or shared-kitchen tasting (food only) | Session 1-5 gates, yields, hold times, ingredient prices, first sensory reactions | low | none if no alcohol | demand from strangers, willingness to pay, beer quality; friends are biased |
| Ticketed private tasting | paid-intent signal, price reaction, pairing flight data | low-medium | ticketing plus alcohol raises sale-vs-gift and venue-permit questions: VERIFY (matrix Q-05: temporary permits reportedly for existing permit holders or nonprofits) | repeat purchase, public demand, licensing |
| Brewery residency or collaboration | strongest combined signal: real guests, licensed partner pours, live pairing, sales data | medium | high: guest/collab beer and food-service rules: VERIFY (Q-02, Q-06) | own-brewhouse economics; host traffic inflates results |
| Food trailer or truck | real service speed and ticket times; Chicken 65, Gobi and Quesadilla fit; goat and tandoor do not | medium-high | mobile alcohol restricted (Q-07): treat as food-only; vending permitting shifting (Q-10) | brewpub concept, architecture, beer program |
| Farmers or event market | fast, cheap price and appeal reads across strangers | low-medium | probably none if food only; health permit and commissary needs unverified (Q-09, Q-10) | pairing, beer, seated experience |
| Small permanent kitchen | full operating data | high | zoning (Q-14) and hood/fire (Q-15) unresearched | too early to risk; needs site, lease, capex, lawyer |
| Other: 30+ structured customer interviews, a paid waitlist or deposit test, a partner-brewer pilot | customer evidence (0 interviews today); brewer pathway data | low | a partner pilot is Pathway 1; whether pilot batches can be served is open: VERIFY | product quality unless a physical product exists |

**Sequence:** (1) cook Session 1 exactly as frozen; (2) confirm the Sessions 2-5 thresholds and cook them, starting goat sourcing early; (3) in parallel run 30+ customer interviews and send the cultural pack; (4) a small tasting of 8 or more people; (5) contact a partner brewer; (6) engage a Texas alcohol attorney; (7) attempt a residency or collaboration only after the attorney answers; (8) consider a trailer or small kitchen only after sales and cost data exist.
**Does the Core 5 change the old path** (digital brand, validation, mobile MVP, brand, capital, flagship)? It still holds as a hypothesis (D-60); the Core 5 narrows what is validated first (5 dishes, 5 beers, untested pairings) and adds format-fit rules (not every dish suits every format). The website and brand work are ahead of the evidence, so digital brand should not drive the next step: physical and customer validation should.

## 2. Investor-readiness gap today
| Question an investor asks | Status | Reason from the repository |
|---|---|---|
| Product proof | NOT READY | nothing cooked |
| Sensory proof | NOT READY | nothing brewed or tasted; pairings are hypotheses |
| Demand | NOT READY | 0 customer interviews |
| Pricing | NOT READY | no prices; 0 ingredient rows priced |
| Margins | NOT READY | financial model has no sourced inputs |
| Repeat purchase | NOT READY | no customers, no event |
| Founder execution | NOT READY | planning output is not execution |
| Team | NOT READY | no GM, chef or brewer |
| Professional brewer | NOT READY | only an AI review |
| Legal path | BLOCKED | all 15 matrix rows T1; attorney and TABC needed; license tier unresolved (Q-01) |
| Site | NOT READY | no site; zoning not researched |
| Capex | NOT READY | no quotes; scale conflict unresolved (`beer/BREWERY-SCALE-DECISION-FRAMEWORK.md`) |
| Operating model | PARTIAL | kitchen capacity is a planning exercise; hood and fire answers missing |
| Trademark | BLOCKED | name founder-selected; clearance pending |
| Supply chain | NOT READY | no supplier contact; goat sourcing open |
| Customer acquisition | NOT READY | no marketing evidence |
| Differentiation | PARTIAL | gap hypotheses exist; competitor sample is secondary; not customer-tested |
Nothing is READY.

## 3. Minimum evidence from BEAUTIFUL CONCEPT to EARLY VALIDATED HOSPITALITY BUSINESS (agent judgement)
All five dishes cooked with logged results, plus at least one beer made by a qualified brewer through a legally verified pathway and tasted; 30+ interviews, then a paid event with real strangers (sales, price reaction, repeat intent); supplier quotes, a priced recipe cost sheet and a model running on sourced inputs; an alcohol attorney's written pathway, trademark counsel's view, a brewer's review and cultural-advisor answers; a repeat or retention signal and a first unit margin from actuals; a cheap next step (a residency or trailer test with real sales). The line between a validated tasting and a validated business is margin plus repeat purchase from real sales.

## 4. Financial-model readiness
`ops/finance/assumptions.csv` now lists the fields an investor model needs (seats, covers, check average, food and beverage mix, COGS, labour, rent, utilities, insurance, licences, marketing, maintenance, waste, debt service, capex, working capital, depreciation, tax) with **every value blank** and `provenance_class = UNKNOWN`. Classes: KNOWN, FOUNDER ASSUMPTION, INDUSTRY REFERENCE, PUBLIC REFERENCE, QUOTE, ACTUAL, UNKNOWN. `tools/fin_model.py` ignores UNKNOWN or unclassified rows (enforced in `run_all`, with a selftest), so it still refuses to run; only QUOTE and ACTUAL rows should feed investor-facing output, while founder assumptions and industry or public references may feed labelled sensitivity ranges only. Break-even and sensitivity are computed outputs, not inputs.
