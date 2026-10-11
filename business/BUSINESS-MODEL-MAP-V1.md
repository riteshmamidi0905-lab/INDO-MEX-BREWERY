# Business Model Map v1

**Status:** `[CONCEPT]` + `[PLANNING ASSUMPTION]`. A map of how the business could earn money, with dependencies. **No revenue stream is validated; no number below is a forecast.** Variables are symbols to be filled from evidence (`business/model/assumptions-template.csv`, all blank). Evidence references: `AUSTIN-FEASIBILITY-V1.md` (benchmarks T3), `research/VERIFICATION-LEDGER.md` (law T1). Legal viability needs a Texas alcohol attorney (G-11).

## 1. Revenue streams and dependencies
| # | Stream | How it earns | Viability dependencies | Evidence today | Class |
|---|---|---|---|---|---|
| R1 | **Dine-in food** | seats × turns × occupancy × avg food check | Tested menu, kitchen capacity, labour | None (no tests, no interviews) | Core |
| R2 | **Draft beer (on-premise)** | pints/flights × price; volume cross-check by bbl | Beer passes gates; BP licence structure; vessel size | BA median 2.6 bbl/seat/yr (T3) | Core |
| R3 | **Flights** | flight attach rate × price | Beer lineup; glass supply | None | Core |
| R4 | **Cocktails / non-alcoholic drinks** | drinks per cover × price | Whether to hold a mixed-beverage permit (MB) vs BG (attorney); NA aguas program | None; permit choice open | Optional |
| R5 | **Takeaway food** | to-go orders × avg ticket | Kitchen throughput, packaging, pickup flow | None | Optional |
| R6 | **Merchandise** | traffic × conversion × basket | Brand identity, glass supply; retail layout | BA/Arryved: merch per taproom declining (T2-T3) | Small, unproven |
| R7 | **Packaged beer (to-go own beer)** | crowlers/growlers/cans on-site | BP allows own beer off-premise ≤½ bbl (T1); labelling; equipment | T1 only | Possible |
| R8 | **Packaged beer (retail distribution)** | cases/kegs via self-distribution or wholesalers | §74.08 caps 1,000/2,500 bbl (T1); alternative structures; capacity | T1 only | Not assumed |
| R9 | **Events / private dining** | bookings × minimum spend | Rooms, noise rules, staffing | None | Possible |
| R10 | **Memberships / loyalty** | members × fee | Legal design (alcohol); perceived value | One competitor membership price (LOW obs) | Optional |
| R11 | **Collaborations / sponsorship** | fees, co-branded beers | Brand strength; partner interest (none known) | None | Opportunistic |
| R12 | **Catering** | events × ticket | Kitchen capacity, licences | None | Later |
| R13 | **Brewery experiences (tours, classes)** | tickets × price | Operations, insurance | None | Optional |
| R14 | **Family/arcade/play** | admissions + F&B uplift | Phase B, insurance, minors law | One competitor admission price (LOW obs) | Later, high uncertainty |
| R15 | **Future products** (house sauces, spice blends, cookbook) | units × margin | DSHS licensing, scale | None | Later |
**Do not assume every stream is legal or viable.** The core model is R1-R3 (+ R4/R5 if chosen); everything else is upside to be justified separately.

## 2. Unit-economics frameworks (variables only; no numbers)
Notation: **S** seats · **T** turns per service period · **O** occupancy · **C** average check · **D** operating days · **P** periods per day.
| Stream | Framework |
|---|---|
| Dining (food) | `Rfood = S_dining × T × O × C_food × D × P` (separate weekday/weekend and seasonal factors) |
| Draft beer | `Rbeer = Σ_styles (pints_i × price_i)`; volume cross-check: `bbl_onsite = pints × oz_per_pint / 3968 oz-per-bbl` (1 US bbl = 31 gal = 3,968 fl oz) |
| Beer volume benchmark | `bbl_demand ≈ S × bbl_per_seat` (benchmark 2.6 bbl/seat/yr, T3; **our own value unknown**) |
| Flights | `Rflights = covers × attach_rate × flight_price` |
| Takeaway | `Rtogo = orders × avg_ticket` |
| Merchandise | `Rmerch = traffic × conversion × basket` |
| Events | `Revents = events × avg_guests × spend_per_guest` |
| Membership | `Rmember = members × fee` (net of benefits cost) |
| Family/arcade | `Rplay = visits × avg_spend` with separate cost-to-serve |
| Packaged own beer | `Rpack = units × (price − cost)` within the legal cap |
| Capacity check | `bbl_capacity = N_fermenters × V_working × turns × utilisation` vs demand; **utilisation and turns are brewer inputs** |
Cost side and EBITDA: `financial-model-architecture` (`FINANCIAL-MODEL-ARCHITECTURE-V1.md`).

## 3. Contribution logic (qualitative until data exist)
Food and beer carry most margin and traffic; flights and pairings aim to raise check size; events fill off-peak; family/arcade drive daytime traffic but bring cost and liability; merchandise supports brand and cash but is unproven. **Peak-hour and weather constraints** (court capacity in heat) cap revenue and must be modelled.

## 4. Sensitivities to model first
Seat count, average check, turns, beer volume per seat, labour %, prime cost, rent/occupancy, ramp-up period, weather/seasonality, family-area uptake (if built), packaged-beer share (if any).

## 5. Evidence required before any number is shown to an investor
Observed Austin prices (survey), interview-based spend and frequency, pop-up sales data, supplier quotes (goat/lamb/paneer/fish), brewer's capacity and cost inputs, architect/vendor quotes, attorney confirmation of the permitted streams.
