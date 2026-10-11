# 20-21. Business Feasibility and Visual-Production Plan

> HISTORICAL: see phase-one/00 banner; research/, food/, beer/ and docs/decisions/ now govern.

## 20. Preliminary business feasibility (NOT legal or financial advice)

### Texas alcohol licensing (partly verified)
- **[VERIFIED S-01, S-02]** TABC's Brewpub License (BP) is subordinate to a primary license: a Wine and Malt Beverage Retailer's Permit (BG), Mixed Beverage Permit (MB) or Retail Dealer's On-Premise License (BE). The holder may brew and package malt beverages and sell its beer on premises; TABC treats brewpubs as retailers. Source documents are 2020-21.
- **[VERIFIED S-01 secondary; S-04]** The total annual production cap is **10,000 barrels** per brewpub according to TABC's license description, raised from 5,000 by SB 515 (83rd Legislature). A bill analysis also describes limited brewpub self-distribution to retailers (e.g., 1,000 bbl), but whether those caps were enacted is **not confirmed**.
- **[UNVERIFIED]** Off-premise sale in containers up to ½ barrel (search summary of S-01); guest beer permissions; canning and distribution rules. Unconfirmed: do not rely.
- **[VERIFIED S-03/S-05, grade C for S-05]** A Brewer's Permit is the alternative path (sell to wholesalers); this structure matters for a national-brand ambition.
- **Flag `[PRO]`:** which license path, whether you can serve guest beer or others' wine/cocktails, and how to scale to distribution. Retain a Texas alcohol-beverage attorney **before** site selection and equipment orders. Verify against current Alcoholic Beverage Code and TABC.

### Other items, all `[PRO]`, unresearched
Federal TTB brewer's notice, label approval (COLA); food permits, City of Austin health; commercial kitchen and hood; wastewater / trade-waste (brewery effluent is high in BOD); water supply; CO₂ storage and detectors; glycol chilling; kegging/canning (mobile canner vs. in-house); cold storage; floor drains and slopes; fire code and occupancy (assembly); ADA; parking; noise (live music); insurance (liquor liability); staffing; construction cost; operating cost; site selection (visibility, zoning, outdoor space, truck access).

### Financial reality checks (placeholders, no numbers asserted)
Build-out of a visible brewhouse + full kitchen + large patio is capital-intensive. Possible phased approach: (1) pilot batches and pop-ups with a partner brewery to validate beers and food, (2) a smaller first location, (3) scale. **Do not trust any projection until Phase Four.**

## 21. Visual-production plan
**Honest constraint:** no image generation was available in the authoring session. What's here is the prompt system. Generated outputs go in `visuals/generated/` with prompt, tool, seed and date recorded, and are labeled **"Concept visual"**.

Pipeline:
1. Lock the style bible (`visuals/prompts/00-STYLE-BIBLE.md`).
2. Generate architecture first (Images 01-04): lock the building as a reference.
3. Use the first exterior and interior outputs as image references for subsequent scenes.
4. Generate beer and glass (05-06), food (07-10), flight and courtyard (11-12).
5. Review for artifacts (hands, text, logos, cheese physics, glassware geometry), then retouch.
6. Replace any AI-invented signage/logos with approved marks. No fake awards, customers or testimonials.
7. Food photography should be re-shot from real dishes once the kitchen exists. These are visual targets only.

Tooling options to consider (founder's choice): a dedicated image model with image-reference support, plus a human retoucher. A real photographer/CGI studio for final architecture renders after an architect is engaged.

First 12: see `visuals/prompts/01-first-twelve.md`.
