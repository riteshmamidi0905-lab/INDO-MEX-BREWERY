# Austin competitor price survey (structure + backlog)

**Status (Sprint 3):** 19 price observations and 10 feature rows were added in long form (`observations.csv`, `venue-features.csv`). **All are LOW confidence**: they come from WebSearch summaries of official venue pages (pages not opened; the primary hosts were blocked). **No analysis is justified yet** (no regular pint price exists for three or more venues). Earlier status: **No prices had been collected**; the CSV contains venue identity from existing research and blank fields. Live research was not possible in this environment (primary pages could not be opened), so nothing is assumed.

## Files
- `austin-competitor-price-survey.csv`: 10 rows (9 competitors + the arcade-bar reference), 23 fields (`survey-schema.json`).
- `survey-schema.json`: field list and rules.

## The standard basket (same for every venue)
House flagship beer (price and pint size) · flight price · a cheapest and a most-ordered shareable snack · a taco order · the main pizza/entrée · kids' options · non-alcoholic options · any service fee. Plus observations: family features, outdoor/shade, music/events, parking, brewery visibility, merch, retail/to-go (can/crowler), service model (counter vs table).

## Method
1. Visit or open the official menu; photograph or save the menu with the date.
2. Fill one row per venue per date; leave unknowns blank.
3. Confidence per row as defined in the schema.
4. Compute medians only from filled values (`summary` step in the discovery tool can be reused).
5. Refresh each quarter; prices move.

## Backlog / what each row needs
Pinthouse, Lazarus, Live Oak, Celis, Prost, Draught House, Central Machine Works, Jester King, Aviator, Cidercade: **all price and feature fields blank**; official URLs to confirm. Add any new relevant competitor discovered during customer interviews.

## Long-form files (Sprint 3)
- `observations.csv`: one row per observed price; fields: venue, page, item, category, **price_type** (regular_stated / happy_hour / set_menu / add_on / special / range / membership / admission / from_price), price or low-high, serving size, source, **source_type**, capture date, page date if stated, confidence, notes. Never merge price types; delivery-app prices are not recorded here and would need their own label.
- `venue-features.csv`: non-price observations.
- **Coverage:** Pinthouse 7, Lazarus 5, Celis 3, Cidercade 3, Prost 1 price rows; **no price rows** for Live Oak, Draught House, Central Machine Works (nothing found), Jester King, Aviator. **No Austin regular pint price is established for Lazarus, Prost, Draught House, Aviator or Jester King.**
- **To finish properly:** a person (or an environment that can open the sites) must open each official menu, record the observed price and date, and replace these LOW rows.
