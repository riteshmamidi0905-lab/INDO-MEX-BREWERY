# Verification Ledger (Sprint 3; supports D-53 and D-56)

**Purpose:** show which high-impact facts moved to stronger evidence and which did not. **Nothing here is "verified" in the sense of us opening and quoting the primary document.** In this environment every primary host was blocked (see §2), so the strongest tier reached is **T1**.

## 1. Evidence tiers (use these words, not "verified")
| Tier | Meaning | May be called |
|---|---|---|
| **T0** | We opened the primary document/page and can quote it (URL, date accessed, exact words) | "verified (primary)" |
| **T1** | A search-tool summary of an **official/primary-domain page** that states the specific claim; page not opened by us | "corroborated by official-domain summary; **not verified**" |
| **T2** | Reputable secondary source (press, university, trade body) | "reported" |
| **T3** | Search extract of vendor/blog/mirror/job-board/unknown-date page | "unconfirmed" |
| **T4** | Hypothesis, assumption, or unresolved | "assumption / unresolved" |
Other evidence classes are kept separate and never mixed with the above: **professional advice** (none yet), **founder assumption**, **internal hypothesis**, **test target**, **synthetic test data** (never counted as evidence), **physically tested result** (none yet), **supplier-confirmed fact** (none yet), **actual quote/price** (none yet), **calculated estimate** (labelled derived).

## 2. Primary-source access attempt (2026-10-11)
Tried: `statutes.capitol.texas.gov`, `tabc.texas.gov`, `bjcp.org`, `austintexas.gov`, `ttb.gov`, `cpsc.gov`, `uspto.gov`, `tmsearch.uspto.gov`, `ada.gov`, `brewersassociation.org`, `liveoakbrewing.com`, `pinthouse.com`. Result: the session proxy answered **403 (policy denial) to every CONNECT** (curl), and the WebFetch tool returned DNS errors. **Not worked around.** To enable primary verification the founder can add these hosts under Allowed domains (environment network settings, see https://code.claude.com/docs/en/cloud-environments#network-access). What was possible: **WebSearch restricted to official domains**, which returns model-written summaries of those pages (tier T1 at best).

## 3. Ledger
| ID | Claim | Previous | Now | Source (URL) | Accessed | What the source summary supports | Limits |
|---|---|---|---|---|---|---|---|
| V-01 | Brewpub production cap: 10,000 barrels per licensed brewpub (§74.03) | T3 (mirror) | **T1** | https://statutes.capitol.texas.gov/Docs/AL/htm/AL.74.htm | 2026-10-11 | Summary quotes "may not exceed 10,000 barrels for each licensed brewpub"; section last amended 2019 (eff. 2021) | Not opened; a 2025 bill (SB 1240) on inter-location transfers has unknown status |
| V-02 | §74.08(d): sales under that section to in-state buyers capped at 1,000 bbl per brewpub location or 2,500 bbl for all brewpubs of one licensee | T3 | **T1** | same statute page; capitol.texas.gov bill texts | 2026-10-11 | Summary quotes the cap; 2013 S.B. 515 origin; amended 2017 and 2019 | Subsections (a)-(c) conditions (BG permit, own-premises beer, class B wholesaler rules) not read; attorney needed |
| V-03 | A BP is subordinate and must sit on BG, MB or BE; own beer may be sold off-premise in lawful containers up to 1/2 barrel | T3 | **T1** | https://www.tabc.texas.gov/static/sites/default/files/2021-08/brewpub-license-bp-lc.pdf | 2026-10-11 | TABC course material (2020-21) per summary | Documents are 2020-21; current rules need TABC/attorney |
| V-04 | BP/BW holders in Texas need no product registration for on-premise sales; to-go containers must show product name and ABV | new | **T1** | https://www.tabc.texas.gov/faqs/product-registration-faqs/ | 2026-10-11 | Per summary | Labelling for packaged/canned product (COLA/TTB) not checked |
| V-05 | Minors may generally enter licensed premises if they do not possess/consume alcohol; a licensee may set a house rule excluding minors | T2 (news) | **T1** | https://www.tabc.texas.gov/faqs/ | 2026-10-11 | Per summary of TABC FAQ | Nothing brewpub-specific; arcades/play areas near alcohol still unaddressed; attorney |
| V-06 | On-premise employees must be 18+; under-18 cashier exception when alcohol sales are under 60% of gross receipts and a person 18+ serves | T3 | **T1** | https://www.tabc.texas.gov/static/sites/default/files/2020-07/mixed-beverage-restaurant-permit-with-food-beverage-certificate-course-rm-fb.pdf | 2026-10-11 | Per summary (mixed-beverage restaurant course) | Course is for another permit type; BG/BP wording differs; attorney |
| V-07 | BJCP 2021 10A: IBU 8-15, SRM 2-6, OG 1.044-1.053, FG 1.008-1.014, ABV 4.3-5.6% | T3 | **T1** | https://www.bjcp.org/style/2021/10/10A/weissbier/ | 2026-10-11 | Summary says official page and the 2021 PDF agree | Not opened; 2015 edition differs (OG 1.044-1.052, FG 1.010-1.014) |
| V-08 | Austin: fermented-beverage producers need a General Industrial User permit; pH 6.0-11.5; discharge below 120 °F; no tap water dilution; SOP and logs; GIU if no categorical standard and under 25,000 gal/day | T3 | **T1** | https://www.austintexas.gov/water/fermented-beverage-producers | 2026-10-11 | Per summary | Pages carry mixed dates; BOD/surcharge for breweries unresolved; engineer |
| V-09 | TTB Industry Circular 2024-2 (2024-12-05) expanded the beer formula-exemption list; extracts/oils/syrups and alcohol-containing flavors are not exempt; mixing exempt and non-exempt ingredients requires a formula; malt beverage needs ≥51% malted barley among fermentables (rule as summarised) | T3 | **T1** | https://www.ttb.gov/public-information/industry-circulars/ttb-industry-circular-2024-2 | 2026-10-11 | Per summary | **The ingredient list itself was not checked: kokum, tamarind, hibiscus, mango, saffron, chile remain UNRESOLVED**; the summary notes the 24-vs-15 ingredient count is unreconciled |
| V-10 | CPSC Public Playground Safety Handbook: current edition Publication 325 (July 2025); Federal Register notice 2025-08-13 | T3 | **T1** | https://www.cpsc.gov/Playground-Handbook ; https://www.federalregister.gov/documents/2025/08/13/2025-15374/notice-of-availability-public-playground-safety-handbook-update | 2026-10-11 | Per summary | Content (fall zones, surfacing) not read; ASTM/ADA not checked |
| V-11 | Austin outdoor music: 85 dB (permitted venues) with hour cutoffs; 70 dBA for restaurant uses; no permit within 100 ft of residential | T3 | **T1 (partial)** | https://www.austintexas.gov/page/outdoor-music-venue-permits ; https://services.austintexas.gov/edims/document.cfm?id=332090 | 2026-10-11 | 85 dB from a 2019 ordinance; 70 dBA and 100 ft from the city permit page | The code section for 70 dBA was not found; Chapter 9-2 is moving to Title 4 per an older memo |
| V-12 | Live Oak Hefeweizen 5.3% ABV, 10 IBU, year-round draft and cans | T3 | **T1** | https://www.liveoakbrewing.com/the-beer | 2026-10-11 | Per summary of the brewery page (and a second official page) | |
| V-13 | Pinthouse Electric Jellyfish: 6.5% ABV hazy IPA, $7 for 16 oz draft | new | **T1** | https://pinthouse.com/flagship-beers | 2026-10-11 | Per summary | Location and date unknown |
| V-14 | BA median 2.6 bbl on-site per seat per year; food $924 per seat | T3 | **T3 (unchanged)** | the-new-brewer.mydigitalpublication.com (S-76) | not re-checked | n/a | Members' publication extract; taproom median; not a forecast |
| V-15 | NRA full-service labour median 36.5% | T3 | **T3 (unchanged)** | S-79 | not re-checked | n/a | |
| V-16 | Austin rent, land, wage figures | T3 | **T3 (unchanged)** | S-80, S-81, S-117, S-118 | not re-checked | n/a | Asking prices, job boards |
| V-17 | Guest-beer sales under a BP | T4 | **T4 (unresolved)** | n/a | n/a | n/a | Attorney |
| V-18 | One entity holding both brewpub and manufacturer-tier permits; Brewer's-permit figures | T4 | **T4** | n/a | n/a | n/a | Attorney |
| V-19 | Austin zoning use class for brewpub/outdoor entertainment; impervious cover; arcade permits | T4 | **T4** | n/a | n/a | n/a | Land-use attorney/City |
| V-20 | DSHS Food Manufacturer licence for packaged sauces | T3 | **T3** | S-93 | not re-checked | n/a | DSHS written answer |
| V-21 | Historical claims (audit G) | T3 | **T3 (unchanged)** | S-100..S-106 | not re-checked | n/a | Scholarly sources still to read |
| V-22 | BJCP 7A, 2A, 5D, 24A, 10B, 10C, 23G ranges | T3 | **T3 (unchanged)** | S-108 | not re-checked | n/a | Only 10A upgraded this sprint |

## 4. Rules
1. A T1 row **may be cited in internal planning with its tier shown**; it may not be used in investor, press, website or signage copy without T0 verification (and, for law, an attorney).
2. When a primary host becomes reachable, re-run V-01..V-13 and move the tier to T0 only after quoting the page.
3. Search summaries can be stale or wrong; discrepancies noted in the "Limits" column are open items.
