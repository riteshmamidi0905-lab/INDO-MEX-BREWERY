# Customer Discovery: 30-Interview Instrument

**Purpose:** find out whether the concept deserves to exist, **not** to collect compliments. Every question is built so the answer can **invalidate** an assumption. **No interviews have been done; no results exist.** Enter real answers in `responses.csv` (schema in `responses-schema.csv`) and analyse with `python3 research/customer-discovery/analyze_interviews.py`.

## 1. Rules for the interviewer
1. Do **not** pitch. Do not say "amazing", "unique", "imagine". Do not defend the concept. Silence is data.
2. Ask about **past behaviour first** (what they actually did), opinions second, hypotheticals last.
3. Prices: ask for their expectation **before** showing any price. Never anchor.
4. Show the concept card and any image **only at the marked point**; ask for reactions, then reasons not to go.
5. Record exact words in `quote_*` fields; code answers afterwards.
6. Get consent (recording optional); no incentives that bias (a gift card is fine, offered for time, not for answers).
7. Stop and note any question the person did not understand.

## 2. Sample (target n = 30; stop early only if answers stop changing)
| Segment | Target n | Screener |
|---|---|---|
| Austin craft-beer drinkers (visit a brewery ≥ monthly) | 7 | |
| Casual beer drinkers / wine-and-spirits who visit restaurants weekly | 5 | |
| Parents with children under 12 who dine out weekly | 6 | |
| South-Asian-heritage Austinites | 4 | Self-identified; no assumptions |
| Mexican-heritage Austinites | 4 | Self-identified |
| Vegetarian/vegan or "mostly vegetarian" | 4 | At least 3 of 4 overlap with other segments allowed (record) |
Mix ages 21-65, neighbourhoods and income; note anyone who works in food/beer (flag, do not exclude).

## 3. Interview flow (30 minutes)
**A. Context and behaviour (no concept shown)**
1. Tell me about the last time you went to a brewery or taproom: where, with whom, what day/time, how long, what you spent, what made you choose it.
2. And the last restaurant dinner you had that you'd call memorable: why?
3. What have you stopped going to, and why?
4. What beer styles do you order most? What do you avoid? (record wheat, lager, pilsner, IPA, sour, other)
5. How far do you travel for a meal or a beer you like? (minutes by car) What is too far?
6. Do you go with children? What makes a place work or not work for kids?

**B. Concept card (read aloud, neutral; then ask)**
> "A brewery and restaurant in Austin where you can see the beer being made behind glass. The beers are mostly wheat beers and lagers. The food draws on Indian and Mexican cooking. There is a shaded outdoor court. It serves no beef and no pork; the meats are chicken, goat, lamb and fish, with many vegetarian dishes."
7. In your own words, what is this place? What is it for?
8. What is your first reaction? What, if anything, concerns you?
9. What would make you **not** go? (list all; then pick the strongest)
10. Who would you go with? Who would **not** want to come?
11. How does "no beef and no pork" change your interest: more, less, no change? Why? (record exact words)
12. How do you feel about goat and lamb on a menu? (never ordered / would try / would order / already order)
13. What do you expect Indian-and-Mexican food to be? What would make it feel gimmicky to you? What would make it feel respectful?

**C. Beer and food**
14. Which of these would you actually order on a first visit? (show list of styles only: Hefeweizen, Mexican-style lager, Vienna amber, Pilsner, Witbier, Dunkelweizen; no descriptions). Which would you skip?
15. How interested are you in a beer that uses an Indian or Mexican ingredient? What ingredient would worry you?
16. Show the menu list (names only; no prices). Which 3 would you order? Which would you not order? Any you do not understand?
17. For vegetarians: would you eat a full meal here, or just a side? Why?
18. How much do you care about pairing guidance for beer and food? (1-5)

**D. Place and experience**
19. Show the exterior image (ARC-01-D) **now**. What does it tell you about the price level, the crowd and the noise?
20. How important is each (1-5): seeing the brewery working; shade and fans in Texas summer; a place for children; live music; a game room; a shop. Which one would you pay extra for? Which would put you off?
21. A hot July afternoon: would you sit outside? What would need to be true?

**E. Price (ask before showing any price)**
22. What would you expect to pay for a pint? A taco order? A shared snack? A main dish? A kid's meal?
23. For each of pint / main dish: at what price is it so cheap you doubt the quality; a bargain; getting expensive but you'd still go; too expensive to go? (four numbers each)

**F. Commitment**
24. How likely are you to visit in the first month it opens (1-5)? In a typical month after that: 0, 1, 2, 3 or more visits?
25. What would have to happen for you to become a regular? What would make you never return after one visit?
26. Where would you go instead tonight? (name specific competitors)
27. What did I not ask that I should have?

## 4. Coding (after the interview)
Code answers into `responses.csv` using the schema: segment, demographics (optional), behaviour (visits/month, spend, distance), concept comprehension (accurate / partly / wrong), first reaction (positive / neutral / negative / confused), barriers (top 3 free text + code), no-beef/pork reaction (more / less / none), goat and lamb comfort (4-level), vegetarian full-meal (yes/no/side only), importance 1-5 items, price expectations and acceptable ranges, first-month and monthly visit likelihood, substitutes named, and quotes.

## 5. Decision rules (set before interviewing; do not move them afterwards)
| Signal | Concern threshold | Action |
|---|---|---|
| Concept comprehension "wrong/confused" | > 30% of interviews | Rewrite the concept explanation before anything else |
| "No beef/pork" reaction "less interest" | > 25% | Examine segments, messaging, menu appeal |
| Goat/lamb "never would" | > 40% | Increase chicken/vegetarian/fish share and revisit lamb/goat prominence |
| Expected pint or main price well below working model | median below model by > 15% | Revisit model |
| First-month likelihood ≥ 4 but monthly visits ≤ 1 | most of the "high interest" group | Treat as curiosity, not repeat demand |
| Top barrier named by ≥ 8 of 30 | n/a | Treat as a design requirement or a kill criterion |
| Vegetarian full-meal "yes" | < half of vegetarians | Strengthen the vegetarian pillar |
Report n and confidence honestly: 30 interviews cannot give precision; they find problems.
