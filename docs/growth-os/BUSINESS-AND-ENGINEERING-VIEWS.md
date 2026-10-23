# Growth OS: Business view, Engineering view and data provenance

**Brand positioning.** NASHA is presented as an independent, premium hospitality brand: *NASHA — The Courtyard* (in Growth OS and the portfolio: "NASHA — Flagship Hospitality Launch Case Study"). Growth OS itself is industry-agnostic; NASHA and Meridian Fitness are two synthetic tenants. The repository name, historical documents and approved product names are left as provenance. `lab/tests/test_brand_positioning.py` guards public-facing copy.

## Two presentation layers over one set of records
`lab/nasha_lab/growth/present.py` derives the Business view from the stored workflow run, its recorded events, the proposal and the lead. It decides nothing and invents nothing:
* every timeline entry carries the sequence number of the recorded event it came from and that event's raw record (`technical`), which the Engineering view shows;
* a completed stage ("CRM updated", "No email or message was sent", "Waiting for a human decision") appears only if the event was recorded;
* the score, factors and verdict in the Business view are the proposal's own values (tests assert equality with the engineering record);
* a blocked, rejected, completed, abstained or failed run exposes no approval action (`can_decide` is true only for `AWAITING_APPROVAL`; the backend still refuses a decision on any other state, tested).
The Engineering view adds correlation/workflow id, lead id, approval id, failure class, evidence keys, raw JSON, tool calls and policy decisions. The toggle is a presentation preference only (stored in the browser).

## Data categories (Settings screen, `GET /v1/tenants/{t}/provenance`)
* **Verified real**: the recorded engineering evidence (tested commit, test counts, release-gate verdict, remote CI status) read from `lab/results/release-gate/`, with its limitation. Not a typed value.
* **Realistic synthetic**: fictional organisations, people, inquiries, opportunities and runs; counts calculated from stored records; real-looking e-mail addresses counted (must be 0; the schema also forbids them).
* **Founder-approved**: concept prices recorded with basis "founder-approved concept price (D-88)". The second tenant has none and says so.

## Scenarios
`scenarios.py` holds coherent fictional scenarios (corporate catering, private event, hospitality partnership, community event, merchandise partnership, guest retention for NASHA; corporate wellness, trial follow-up, win-back, personal training, opt-out for Meridian Fitness). They are proposed use cases, not services offered. Pipeline values are computed from each tenant's stored prices (`test_pipeline_values_are_computed_from_stored_prices_not_typed_in`). Scenarios 7-10 of the founder list (pricing/profitability, inventory, procurement, campaign planning) belong to modules that are not yet connected to Growth OS (see the capability board).
