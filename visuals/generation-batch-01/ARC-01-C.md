# ARC-01-C: Tank-count correction of ARC-01-B (image-edit prompt)

- **STATUS:** NOT GENERATED
- **PURPOSE:** keep ARC-01-B's architecture, light, entrance and court exactly, and replace only what is seen inside the glass Tank Hall so it shows exactly six fermenters in a horseshoe with charcoal cones and a visible copper brew deck. The rest of the image must not change.
- **METHOD:** use ARC-01-B as the input image with a mask over the glass of the Tank Hall (south glass and east glass, everything behind the mullions). If the tool has no masking, use the whole-image prompt below with ARC-01-B attached and the instruction "change nothing outside the hall glass".
- **ASPECT:** 16:9, same framing as ARC-01-B.

## EDIT PROMPT (masked region)
```
Replace the equipment visible inside the glazed Tank Hall with exactly SIX identical polished stainless-steel conical fermenters arranged in a HORSESHOE that opens toward the camera-side south glass: exactly two tanks along the west wall (far left of the south glass), exactly two tanks along the east wall (seen through the east glass), and exactly one tank on each side of a raised central brew deck at the back (north) wall, so the six tanks form a U around the deck. On the raised brew deck, at the back and centre, show TWO copper-clad brewing vessels with domed tops under a steam hood and a stack, with a stainless hot-liquor tank, pumps and a valve train behind a steel handrail. Each of the six tanks has a polished stainless cylindrical shell, a matte CHARCOAL insulated cone clearly darker than the shell, four legs, a round side manway, tri-clamp fittings, restrained tidy piping on the inner side of the horseshoe, and exactly ONE narrow (about 6 in) deep marigold-orange band around the middle of the shell. No other tanks, no extra tanks, no tanks outside the six, no row of tanks. A steel catwalk with 42-in guardrails at about 11 ft height runs between the legs. Keep the same warm interior uplighting and the same perspective, glazing, mullions and reflections as the input image. Do not change anything outside the glass of the Tank Hall: keep the architecture, entrance, people, arcade, screens, court, landscape, sky, vehicles and light exactly as they are.
```
## NEGATIVE
```
more than six tanks, fewer than six tanks, seven tanks, eight tanks, a straight row of tanks, stainless or silver cones, thick yellow bands, decorated tanks, patterns on tanks, no copper vessels, changes to the building, changes to the screens, new people, new vehicles, logos, text
```
## Review checklist
- [ ] Exactly six tanks; count them twice. U-shaped arrangement around a deck.
- [ ] Charcoal cones clearly darker than the shells; narrow deep-marigold bands.
- [ ] Two copper-clad vessels visible on the deck.
- [ ] Everything outside the glass is unchanged from ARC-01-B.
- [ ] Still reads as a real photograph (reflections consistent).
## Acceptance
Score >= 90 on the ARC-01 rubric with no hard fail, then founder approval.
