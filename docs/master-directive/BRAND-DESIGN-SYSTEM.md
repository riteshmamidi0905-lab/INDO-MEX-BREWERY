# Brand design system: status and extension rules

**Do not duplicate:** the design system already exists. Identity (type, colour, contrast, visual language): `brand/NASHA-IDENTITY-SYSTEM.md`. Implementation (tokens, components, behaviour, QA gates): `website/DESIGN-SYSTEM.md` and `website/src/styles.css`. Logo: none designed (D-66; `brand/NASHA-LOGO-GOVERNANCE.md`).

## Added this session
- `website/tools/check_contrast.py`: recomputes the documented WCAG contrast table from the real CSS tokens and fails on drift or on a forbidden text pair that passes. Result: 19 documented pairs checked, 0 problems; a deliberately wrong ratio is detected.

## Name handling (decision pending, see DIRECTIVE-CONFLICTS.md #1)
The working name stays internal (D-79/D-80). New brand pages must take the name from one token/data field, never hard-code it in copy, so a different final name is a one-line change and nothing public depends on the working name.

## Rules for the new collections (BADSHAH, PAAPI, Goods) when the founder approves them
1. Colour: use existing tokens only; beer colours come from the beer palette; marigold stays the single accent; marigold-ink on light.
2. Merchandise: garment colours are chosen from the palette and recorded with computed contrast against the print colour; artwork is original vector work made here, rights-registered before any file ships (`nasha-rights-audit`).
3. Labels: every product image is tagged "Concept visualization/illustration"; products are "concept merchandise", never purchasable; no cart, no payment field.
4. Cultural material: floral and architectural references carry a source and a label (documented tradition vs modern interpretation) in `research/HISTORICAL-CLAIMS-AUDIT.md`; flag for a qualified reviewer (`brand/CULTURAL-INTEGRITY-AND-ADVISORS.md`).
5. Accessibility and performance budgets in `website/DESIGN-SYSTEM.md` sections 6-7 apply unchanged.

## Not done (and why)
No new pages, hoodie art, beer labels or imagery: they depend on founder decisions #2-#4 and on an image tool and rights audit that are not in place. No NASHA media was created or uploaded.
