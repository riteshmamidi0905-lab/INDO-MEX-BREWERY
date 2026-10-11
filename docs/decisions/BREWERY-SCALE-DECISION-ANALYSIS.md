# Decision Analysis G-6: Brewery Scale vs Demand

**Status:** `[ANALYSIS]`, **no recommendation is made and none is implied.** This is the largest unresolved design/economic issue found in Sprint 3 (D-51, correction #19). It is a decision for the founder, informed by a head brewer. Evidence tiers per `research/VERIFICATION-LEDGER.md`; numbers marked **derived** are our arithmetic from stated assumptions, **not** quotes or forecasts.

## 1. The problem
The canonical tank geometry (5 ft diameter, 12 ft shell, 4 ft cone; Locked DNA §4) is **about 63 bbl gross (about 50 bbl working) per fermenter** (derived; 1 US bbl = 31 gal = 4.14 ft³). Six such tanks is a **~300 bbl fill**. The copper vessels shown (~7 ft diameter) are also ~60 bbl-class. By contrast, the only demand benchmark found is a Brewers Association **median of ~2.6 bbl of on-site beer per seat per year** (taproom/brewpub, 2023 data, **T3, not a forecast**), which implies **~780 bbl/yr at ~300 seats** (derived). The visual canon therefore looks like **production-brewery scale for a brewpub-scale demand**. The visual canon was designed for the image, not sized by a brewer.

## 2. Known numbers (all derived; assumptions in brackets)
| Fermenter size (gross / working) | Dia × height if scaled from canon | Six tanks, ideal bbl/yr at 12 / 20 / 26 turns | At ~65% utilisation [assumption A-5] |
|---|---|---|---|
| ~15 / ~12 bbl | ~3.1 × 11.8 ft | 860 / 1,440 / 1,870 | ~560-1,220 |
| ~30 / ~24 bbl | ~3.9 × 14.8 ft | 1,730 / 2,880 / 3,740 | ~1,120-2,430 |
| ~60 (canon) / ~48 bbl | ~4.9 × 18.7 ft | 3,460 / 5,760 / 7,490 | ~2,250-4,870 |
Constraints: Texas BP production cap 10,000 bbl per location and self-distribution cap 1,000 bbl per location (2,500 per licensee) with conditions (**T1**, attorney to confirm). Tank-time budget for ~8 beers at ~780 bbl and 15-bbl tanks is ~1,424 tank-days ≈ 65% of six tanks (derived, `beer/OPENING-BEER-PROGRAM-V1.md` §6).

## 3. Options compared (qualitative judgement; ratings H/M/L are **ours, not evidence**)
| # | Option | What it means | Fits demand | Visual canon | Capex | Beer variety | Flexibility | Main risks / unknowns |
|---|---|---|---|---|---|---|---|---|
| O1 | **Original larger system** (~50 bbl working × 6) | Build as drawn | **L** (3-6× demand) | **H** | **H** | H but each batch is huge | L | Overcapacity; stale beer; wasted capital; **forces a distribution business** to use capacity |
| O2 | **Smaller tanks, six kept** (~15 bbl) | Same six-tank horseshoe, smaller vessels | **H** | M (smaller scale; hall looks emptier) | L-M | H (≈8 beers) | M | Growth ceiling; per-bbl cost higher; hall height mismatch |
| O3 | **Mid tanks** (~30 bbl) | Middle path | M | M-H | M | H | M-H | Slight overcapacity unless demand beats benchmark |
| O4 | **Fewer tanks** (3-4) at chosen size | Reduce count | depends | **L** (breaks "six") | L | **L** (fewer concurrent beers) | M | Loses signature arrangement and variety |
| O5 | **Phased capacity** | Install ~3 now, provisions for 3 more | M-H | M (half-built horseshoe early) | **L now / H later** | M now | **H** | Incomplete visual at opening; second-phase cost and disruption |
| O6 | **Partner/contract brewing for extra volume** | Small on-site system for the flagship and visible brewing; a partner brews more | M | M | L | M | M | **Licensing and brand-control questions (attorney, T4)**; "made here" honesty for those beers |
| O7 | **Production beyond restaurant demand** | Build for sales outside the venue | n/a | H | H | H | M | A **second business** (packaging, wholesale); on-site revenue per bbl is ~231% higher than distributed (T3), so packaged volume is lower-margin; legal caps (T1) |
| O8 | **Distribution strategy** | Sell outside via self-distribution/wholesalers | n/a | n/a | M-H | n/a | M | Caps 1,000/2,500 bbl (T1); sales/marketing capability; **must not be chosen merely to justify oversized equipment** |
| O9 | **Decorative/oversized display vessels** | Large-looking vessels not used for real brewing | n/a | H | M-H | n/a | L | **Rejected on principle:** violates the honesty rule ("they actually make it here"); listed only to rule it out |

## 4. Design implications (any option)
Hall height and mezzanine were sized for ~19-ft tanks: smaller vessels leave a tall, under-filled volume (options for the architect: lower hall, use catwalk/mezzanine to give vertical life, accept generous volume as architecture, plan barrel room later). Visual renders (ARC-01-D, BRW-01) are **illustrative**; no image is a sizing document.

## 5. What evidence would actually resolve it (in order of leverage)
| Evidence | Source | Resolves |
|---|---|---|
| **Brewer's sizing proposal** (working volume, count, turns, cadence) with reasoning and a variety plan | Licensed head brewer | Technical fit; realistic utilisation and tank-time |
| **Demand data:** beer volume per cover from interviews and pop-up; seat count; mix of beer vs other drinks | Customer discovery, pop-up | Whether 2.6 bbl/seat is a good proxy for *this* concept |
| **Vendor quotes** at 15, 30 and 60 bbl (capex per bbl of capacity) | Brewhouse vendors | Whether larger vessels are cheaper per bbl and by how much total |
| **Variety requirement** | Menu/beer program | Whether ~8 concurrent beers justify six tanks even at small size |
| **Legal constraints** on packaging, self-distribution, contract brewing | Attorney | Which of O6-O8 are even available |
| **Packaging/growth intent** (founder) | Founder | Whether production beyond demand is a goal at all |
| **Hall/structure implications** | Architect | Cost of the hall relative to vessel size |

## 6. Decision framework (to apply when evidence exists; thresholds to be set before looking at results)
1. Estimate **mature on-site demand** (bbl/yr) with low/base/high from interviews, pop-up and benchmark.
2. Ask the brewer for the **smallest configuration that meets base demand at a utilisation they will defend**, with variety needs satisfied.
3. Add **growth headroom** only if the founder sets it explicitly (a number chosen before seeing quotes).
4. Compare capex per bbl and total capex across O2/O3/O5 (and O1 only if demand evidence supports it).
5. Treat O6-O8 as separate business decisions with their own evidence; **never** choose them to fill a tank.
6. Record the decision with reversal triggers (e.g., sustained sell-outs for N months → expansion path).
**Tripwires:** if the brewer's recommended working volume is far below canon, update the architectural brief and the visual canon notes (not ARC-01-D itself, which remains the approved exterior); if demand evidence strongly exceeds the benchmark, revisit O3.

## 7. Status and ownership
Owner: head brewer (proposal) → founder (decision). Dependencies: F-2 authorisation; interviews; quotes. Reversibility: R3 once equipment is ordered. **Not decided.**
