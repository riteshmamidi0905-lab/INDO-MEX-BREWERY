# Austin competitor price survey (structure + backlog)

**Status:** structure and backlog only. **No prices have been collected**; the CSV contains venue identity from existing research and blank fields. Live research was not possible in this environment (primary pages could not be opened), so nothing is assumed.

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
