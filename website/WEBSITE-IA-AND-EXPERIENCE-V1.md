# Website Information Architecture and Experience v1

**Status:** `[DESIGN]` for a future site. **No website code is written** (still by instruction). This defines storytelling, sitemap, public vs investor layers, interactions and requirements so a build can start cleanly. Content sources and their evidence status are mapped in §6. Every public page must carry the right honesty label (§5). Concept visuals only until real photography exists.

## 1. Storytelling goals: what a visitor should understand
What is it? Why should it exist? Why Austin? Why Indian × Mexican? What will the food and beer be? What will the building feel like? Who will visit? How does it make money *(investor layer only)*? What makes it defensible *(investor layer)*? How could it expand *(investor layer)*? What remains to be validated *(both layers, in different depth)*? Why could this become a major hospitality brand *(investor layer; public gets the vision)*.

## 2. Recommended sitemap
| Page | Layer | Purpose / story | Notes |
|---|---|---|---|
| **Home** | Public | Cinematic intro: the glass hall, the idea in one line, pairing teaser, "a place in development" | Hero uses ARC-01-D class imagery labelled concept |
| **Our Story** | Public | Why India × Mexico × Austin, told honestly (analogy not history) | Audited wording only |
| **Food** | Public | Opening-menu vision (proposed dishes, "designed around") | No claims of tasting; no beef/pork; no halal claim |
| **Beer** | Public | House program (intent), the gate-beer idea, the glass | "Not yet brewed" visible |
| **Experience** | Public | The guest journey, the Cloister reveal, the shade | Audience stories |
| **Space** | Public | Conceptual architecture and atmosphere; concept renders | "Concept visualization" label |
| **Culture** | Public | How inspiration is handled respectfully; advisors (when real); what we do not claim | Advisor names only if agreed |
| **Austin** | Public | Why the concept belongs here (climate, food-and-beer culture, shade) | No unverified stats |
| **Journey** | Public | From concept to opening: dependency timeline, no dates | Progress honesty |
| **Journal / Lab** | Public | Real tests, brewing pilots, sketches, decisions as they happen | Only real events; empty states are fine |
| **Partners / Investors** | **Gated, private** | Evidence, market, economics, operations, risk, validation, capital | Access-controlled; legal review before any capital language |
| **Contact** | Public | Advisors, partners, suppliers, press, community | Separate form for investor interest (no offering) |

## 3. Storytelling sequence (public, scroll order on Home → deeper pages)
1. **Cold open:** the hall at blue hour, no text. 2. **One sentence:** what it is. 3. **The idea:** beer and food designed together. 4. **The crossing:** two kitchens, one logic (animated, analogy-labelled). 5. **The place:** Tank Cloister reveal, Shade Court. 6. **The plate and the glass:** pairing teaser. 7. **The honesty line:** "This place is still being designed. Here is what we know and what we are testing." 8. **Follow the build:** Journal, Journey. 9. **Say hello.**

## 4. Interaction concepts (progressive, optional; none replaces content)
| Idea | What it does | Requirement |
|---|---|---|
| Cinematic hero | Slow image/video of concept views | Poster fallback, no autoplay with sound, reduced-motion respected |
| Scroll storytelling | Panels reveal story beats | Works without JS (static sections) |
| Cultural intersection animation | Shows cooking-logic parallels (heat, acid, fat, toast) | Clearly labelled "analogy", never history |
| **Interactive menu** | Filter by vegetarian, heat, dairy/peanut/sesame markers; pairing shown | Dietary data must be verified; "proposed" label |
| **Beer explorer** | Pick a mood or dish → matching beers and flight | Descriptions are intent, not tasting notes |
| **Pairing visualization** | Beer ↔ dish links with the reason | Marked hypotheses until trials |
| Conceptual walkthrough | Step through zones of the proposed venue | "Concept, not engineering" label |
| Progress timeline | Stages with status (not dates) | Pulls from roadmap |
| Interactive brewery diagram | Explains how a brewery works (educational) | Generic process, not our unbuilt system |
| Austin context map | Why Austin (shade, climate, neighbourhood types) | Verified data only |
| Investor data visualisations (gated) | Scoreboard, model structure, risk map | Evidence/assumption/gap on every chart |

## 5. Non-negotiable requirements
- **Performance:** target good Core Web Vitals (LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 are Google's published "good" thresholds; **re-verify** current values at build); image/video budgets; lazy loading; no heavy library for effects that CSS can do.
- **Accessibility:** WCAG 2.2 AA minimum; keyboard and screen-reader paths for every interaction; `prefers-reduced-motion`; contrast checks (marigold is used narrowly, never as the only signal); captions and transcripts.
- **Mobile-first**, offline-tolerant text, readable without animation.
- **Honesty labels (every page):** "Concept visualization" on renders; "Proposed" on dishes/beers; "Not yet brewed/cooked/tested" where relevant; "In development, not open" in the header; no real customer quotes, reviews or awards.
- **Privacy:** minimal analytics, no dark patterns, clear contact-form policy; investor gate with real access control.
- **Content integrity:** culture and history text only in audited wording; advisors credited only if real; no halal claim; "We do not serve beef or pork" only after kitchen verification.

## 6. Content readiness map (how close the repo is to a build)
| Page | Source documents | Content ready? | Gaps |
|---|---|---|---|
| Home | master concept; VISUAL-DNA; ARC-01-D | Copy drafts possible now | Brand/name, hero assets, labels |
| Our Story | master concept; historical audit (addendum G) | Yes with audited wording | Advisor review |
| Food | `MENU-STORYTELLING-V1.md`, matrix | Yes as proposed | Food photography (not generated), T1 results |
| Beer | `BEER-BRAND-EXPERIENCE-V1.md`, program | Yes as intent | Gate-beer result, GLS imagery |
| Experience | `GUEST-EXPERIENCE-ARCHITECTURE-V1.md`, journey | Yes | Interior visuals |
| Space | `SPATIAL-VISION-V1.md`, master plan, ARC-01-D | Partly (night, interior imagery unresolved) | Night hall, BRW interior |
| Culture | `CULTURAL-INTEGRITY-AND-ADVISORS.md` | Yes | Advisors |
| Austin | competitive landscape; climate notes | Partly | Verified Austin data |
| Journey / Journal | roadmap; (no real tests yet) | Journey yes; Journal empty | Real events |
| Investors | investor story, data room map, scoreboard | Structure only | Evidence |
| Contact | n/a | Simple | Legal/privacy text |
**Assessment:** the repository supports a **content-complete prototype of the public site as a clearly labelled concept**; it does **not** support a credible investor site until Track B evidence arrives. Missing for a high-quality build: brand name/identity, hero imagery set (GLS, food, interiors), advisor and legal text, and a design system.

## 7. Technical direction (later)
Static-first site generator with a small interactive layer for the menu/beer explorer; content in repo-managed data files (menu and beer as structured data with evidence flags); investor area behind authentication; analytics minimal. **Do not start coding until the name/brand direction and hero visuals are chosen.**
