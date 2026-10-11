# NASHA: Identity System (logo brief, typography, colour, visual language)

**Status:** `[PROPOSED]` design proposals for a **founder-selected name pending legal clearance** (`NASHA-BRAND-STRATEGY.md`, D-62). **No logo has been designed.** The website prototype uses a **typographic placeholder wordmark**, not a logo. Colours and type are proposals; contrast numbers below are computed (WCAG 2.x formula) by our script; font files and licences are recorded in `ip/website-asset-rights-register.csv`. Visual authority for architecture remains ARC-01-D; Visual DNA v2.1 rules (marigold used narrowly, collar ring) carry over.

## 1. Logo system brief (for a professional designer; ownership by written assignment, `ip/IP-OWNERSHIP-FRAMEWORK.md` §5)
**Deliverables:** primary wordmark; secondary lockup (wordmark + descriptor); compact mark; favicon/app mark; monochrome and one-colour versions; horizontal and vertical lockups; signage version (readable from a road, simple enough to fabricate in steel); packaging version (small cans/cards); merchandise version (embroidery/screen-print safe). Provide vector masters, usage rules, minimum sizes, clear-space and misuse guide; accessibility (contrast, legibility at 16 px).
**Design intent:** an identity that is **recognisable from the word NASHA itself**, with stereotype-free imagery. Direction ideas for exploration (not prescriptions): (1) **letterform-first**: a custom, quiet wordmark with one considered detail (for example the crossbar or counter of the A), (2) **the ring**: the collar/sleeve ring from the glass and tank as a recurring, abstract form, (3) **the arch**: the glass-hall elevation reduced to a single abstract shape.
**Avoid by default:** Taj Mahal, sombrero, cactus, elephant, chili pepper, agave, mandala pasted onto Mexican motifs, moustache, generic hop cone, beer mug, flags, saffron/green/white or red/white/green flag colour logic, faux-Devanagari or faux-"Mexican" type, anything that reads as nightclub or cannabis branding. An exception needs an unusually sophisticated reason, documented.
**Must work:** one colour; on dark and on light; at favicon size; embossed; in steel; with and without the descriptor.
**Process:** brief → 3 directions → advisor review for cultural/linguistic reading → trademark search on the final mark → refinement → rights assignment. **No logo work before the IP attorney's first view.**

## 2. Typography direction
| Role | Proposed family | Why | Licence / use status | Notes |
|---|---|---|---|---|
| Display / wordmark placeholder / headings | **Instrument Serif** (regular + italic) | A refined condensed serif with warmth; distinctive without cliché; light (~21 KB each) | SIL Open Font License 1.1 (from npm package `@fontsource/instrument-serif`; licence file stored) | Single weight; use large sizes only |
| Text / UI / menu | **Inter** (variable, latin subset) | Highly readable, accessible, supports tabular figures; ~48 KB | SIL OFL 1.1 (`@fontsource-variable/inter`) | Latin subset only |
| Fallbacks | system serif and sans stacks | Performance and resilience | system fonts (no embedding) | |
**Licensing clarity:** both are OFL (commercial use, modification and embedding allowed; the font may not be sold by itself; reserved font names). Files are self-hosted (no third-party font CDN: privacy and rights). **Multilingual potential:** Spanish accents are in the Latin subset. Hindi/Telugu/Tamil (Devanagari etc.) are **not included**; add a verified family (e.g. an OFL Noto Sans family) **only when verified non-English text exists**, with its licence recorded. **Usage:** web (above); menu (Inter text + Instrument Serif dish names); signage (Instrument Serif caps, tracking +); packaging/beer (Inter small caps, keep ≥ 6 pt); merchandise (display only); investor materials (Inter, tabular figures). **Rule:** no new font enters the build without a row in the rights register.

## 3. Colour system (proposed; contrast computed)
Not a flag mix: the palette comes from **materials, fire and food**: soot, limestone/bone, stainless, copper, marigold (the Visual DNA accent), indigo dusk, plus herb, hibiscus and tamarind from the plate.
**Primary:** Soot `#141110` · Char `#241E1B` · Bone `#F3ECDD` · **Marigold `#E8870E`** (accent, used narrowly).
**Secondary:** Limestone `#E4DAC6` · Stainless `#C9CCCB` · Smoke `#9A9087` · Copper `#C47A45` · Indigo `#1A2142` · Dusk `#2B3563`.
**Food palette:** Herb `#7D9A45` (ink version `#3F5A1E`) · Hibiscus `#9B2447` · Tamarind `#5A3A25` · Straw `#E9C46A`.
**Beer palette (illustrative, per drinking experience):** Straw `#E9C46A` · Gold `#D9A441` · Amber `#B5651D` · Copper-red `#8B3A1D` · Dark `#2B1B14`.
**Digital neutrals:** Soot / Char / Ember `#3A2B22` / Smoke / Limestone / Bone / White.
**Accessible text pairs (computed contrast; WCAG AA needs 4.5 for body, 3 for large text and UI components):**
| Foreground on background | Ratio | Use |
|---|---|---|
| Bone on Soot | 15.98 | Body on dark |
| Bone on Char | 13.99 | Body on dark cards |
| Limestone on Soot | 13.55 | Secondary text |
| Stainless on Soot | 11.62 | Captions |
| Smoke on Soot | 6.01 | Muted text |
| **Marigold on Soot** | **7.07** | Accent text/links on dark |
| Marigold on Char | 6.19 | Accent on cards |
| Marigold on Indigo | 5.90 | Accent on night panels |
| Marigold on Dusk | 4.41 | **Large text/UI only** |
| **Marigold on Bone** | **2.26** | **Fails: never use for text on light** |
| Marigold-ink `#8A4A00` on Bone | 5.83 | Accent text on light |
| Marigold-ink on Limestone | 4.95 | Accent text on light |
| Soot on Bone | 15.98 | Body on light |
| Char on Limestone | 11.86 | Body on limestone |
| Soot on Marigold | 7.07 | Buttons (dark text on marigold) |
| Herb-ink `#3F5A1E` on Bone | 6.63 | Vegetarian marker text on light |
| Hibiscus on Bone | 6.52 | Alerts/labels on light |
| Smoke on Bone | 2.66 | **Fails for text** |
| Copper on Bone | 2.87 | **Decorative only** |
**Rules:** marigold is the **one accent** (never a background wash); on light surfaces use marigold-ink; never colour alone to convey state (add icon/text); focus ring marigold on dark and char on light, 3 px with offset.

## 4. Visual language
**Grammar elements:** fire and char (warm light, glow, ember); fermentation (liquid, foam, time); grain and spice (texture); smoke; stainless (cool highlights); clay and stone (limestone, bone); a **ring** motif (collar, sleeve); long shadows and nighttime hospitality; warm food photography; contemporary Austin architecture (shade, concrete, cedar elm).
**India × Mexico intelligently:** through **material and process** (clay, char, toasted seeds, tortilla/flatbread surfaces, steel, hand-finished textures), through **craft objects** (stoneware, katori, collar glass), and through **ingredient pairs** shown honestly; never through costume, flags, sacred imagery, pattern clichés or maps-as-wallpaper.
**Photography:** natural light, real hands, honest plating, steam only where plausible, no stock crowds. **Illustration:** original vector art made by us (the website uses this until photography exists). **Motion:** slow, warm, purposeful (embers, steam, light), always optional and reduced-motion safe.
**Do-not list:** terracotta walls, brass décor, mosaic/jaali/mandala, string lights, neon, Day-of-the-Dead props, faux-script type.

## 5. Open items
Logo and wordmark (designer); final type pairing validation (accessibility audit of real pages); real photography; Devanagari/Spanish specimen review with advisors; trademark and domain strategy.
