# Traction Engine: What to Measure from Day 1

**Status:** `[DESIGN]` of a measurement system. **No metric has a value; no event has occurred.** The schema is empty (`traction-event-log.csv`: header only) and is checked by `tools/validate_repo.py`. Purpose: make the first real evidence **clean, comparable and honest**, so it can be shown to investors later. Linked: `MOBILE-MVP-STRATEGY.md` (hypotheses H1-H8), `research/customer-discovery/` (interviews are a separate evidence stream).

## 1. Principles
1. **Define before you collect:** thresholds in the MVP hypotheses are set and frozen before any event. 2. **One row per service session**, recorded the same day. 3. **Real data only** (`data_source = real`); dry runs with friends are labelled `dry_run` and excluded from headline metrics; **synthetic data never enters the log** (the analyser self-test uses a temp directory). 4. **No personal data in the repository.** Emails/SMS/phone numbers live in a consent-based CRM outside git; the log stores **counts only**. 5. **Record failures** (sold out early, long tickets, waste) as carefully as wins. 6. Separate **observed** from **derived** fields.

## 2. Metrics catalogue
| Metric | Definition / formula | Captured how | Why it matters | Hypothesis |
|---|---|---|---|---|
| Customers served | Unique parties/people served in a session | Tally or POS covers | Scale of the sample | all |
| Orders | Count of tickets | POS/tally | Basis for averages | H1 |
| Revenue | Net sales excluding tax/tips | POS | Core economics | H1 |
| Average order value | revenue ÷ orders | derived | Pricing validation | H1 |
| Items per order | items sold ÷ orders | derived | Basket depth | H1 |
| Dish mix | Units per dish ÷ total units | POS item counts | What actually sells | H1, H4 |
| Vegetarian mix | Vegetarian units ÷ total units (and orders containing a vegetarian item) | POS flags | Whether the veg pillar earns its place | H3 |
| Repeat visits | Share of customers who return across sessions | Opt-in loyalty/QR code or staff recognition; **method must be stated** | Repeat demand (hardest, most valuable signal) | H2 |
| Email / SMS signups | Opt-ins per 100 customers (SMS only if used and consented) | CRM counts | Community and launch list | H6 |
| Social follows | Net new followers per period (Instagram/TikTok) | Platform analytics | Attention (weaker than sales) | H6 |
| QR scans | Scans per 100 customers | QR tool counts | Engagement with story/pairing | H6, H7 |
| Website visits | Sessions, sources | Privacy-light analytics | Awareness | H6 |
| Event conversion | Customers per estimated attendance at an event | Event organiser data + tally | Which event types pay | H8 |
| Customer ratings | Star rating collected at pickup or after | Single question | Quality perception | H1, H5 |
| Recommendation (NPS) | "How likely are you to recommend us to a friend? 0-10" → promoters (9-10) minus detractors (0-6) | 1-question card/QR | Word-of-mouth potential; small samples are noisy | H2, H6 |
| Food waste | Portions or weight discarded ÷ prepared | Waste log | Prep accuracy, cost | H5 |
| Ticket time | Order to hand-off, median and 90th percentile | Timestamp or stopwatch sample | Throughput | H5 |
| Gross margin | (revenue − COGS) ÷ revenue | Receipts + recipe cards | Economics | H1 |
| Contribution margin | gross margin − variable costs (labour hours × wage, packaging, fees) | derived | Per-session profit | H1 |
| Labour per order | labour hours ÷ orders | Time sheets | Efficiency | H5 |
| Sold-out frequency | Sessions with at least one sell-out ÷ sessions; items sold out and time | Log | Demand vs supply; goat/lamb supply | H4 |
| Repeat purchase | Same-dish reorders by returning customers | Opt-in | Craveability | H2 |
| Pairing interest | Share asking about or selecting a suggested pairing | Staff tally/QR | Pairing thesis | H7 |
| Flagship-brewery interest | Share expressing interest in a future brewery (e.g. asking to be notified) | Signup tag | Brand pull | H6 |
**Sample-size honesty:** report n for every metric; do not report percentages from tiny samples without saying so.

## 3. Data capture design
`validation/traction-event-log.csv` (one row per session). Counts only. Fields: session id, date, event type, partner, hours open, customers, orders, revenue, units sold, veg units, per-dish units (MVP dishes), sold-out items, median ticket time, waste, COGS total, labour hours, QR scans, email/SMS signups, social delta, ratings count/average, recommend promoters/passives/detractors, repeat-customer count and method, flagship-interest count, notes, **data_source**. Analyse with `python3 validation/analyze_traction.py` (prints metrics only for `real` rows; with no rows it says so).

## 4. Evidence the founder should collect before approaching serious investors
(Aligned with `investor/CAPITAL-LADDER-AND-INVESTOR-STRATEGY.md` §4.) Real sales over multiple sessions and venues; repeat customers with a stated method; margins from receipts; ticket times; food cost per dish; demand patterns by event type; vegetarian and goat/lamb performance; signup and community growth; partner feedback; real interviews; a documented legal pathway; trademark status.

## 5. Not allowed
Hypothetical results, projected "traction", seeded reviews, bought followers, staged sell-outs, quoting NPS from a handful of friends, or publishing numbers without a note on sample and method.
