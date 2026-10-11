# IP and Ownership Framework

**Status:** `[PLAN]` framework so that future work is created with **clean provenance from the start**. **This is not legal advice and gives no clearance, no registration status and no ownership conclusion.** Facts about law are T1/T3 search summaries (`research/VERIFICATION-LEDGER.md` V-28..V-30, V-34) or general knowledge flagged for attorney review. An **IP/trademark attorney** (separate from the Texas alcohol attorney) is added to the professional roadmap. Registers: `founder-asset-register.csv`, `website-asset-rights-register.csv`.

## 1. Principles
1. **Nothing is "ours" until ownership is documented.** The registers start at NOT ESTABLISHED. 2. **Written agreements before work starts** for every contractor, designer, developer, photographer, videographer, agency, advisor and collaborator. 3. **The company (or the founder, until it exists, with a planned assignment) must be able to show rights to every public asset.** 4. **Record how each asset was made** (human / AI-assisted / AI-generated / third-party) and under which licence or tool terms. 5. **Do not invent protectable inventions.** 6. Separate **public** (build-in-public) from **protected** (secrets) *before* publishing.

## 2. Forms of protection: what appears potentially relevant (not clearance)
| Form | Potentially relevant to | What it does/does not do | Evidence status | Needs |
|---|---|---|---|---|
| **Trademark** | Parent/company name; restaurant/food-truck/brewery sub-names; logo; slogans; beer and product names | Protects identifying marks in commerce for specified goods/services; **does not** protect the concept, menu or recipes. The USPTO says to search before filing (federal register is not enough; common-law use counts) and will not run or interpret searches (V-29) | **Preliminary web screen only** (`brand/TRADEMARK-SCREENING.md`); no clearance | IP attorney: knockout + filing strategy; use-in-commerce vs intent-to-use |
| **Copyright** | Original website copy, photography, video, illustrations, menu artwork, graphics, brand assets, original code, written recipes (text) | Automatic for original human authorship; **a contractor's work is generally not work-made-for-hire unless it fits a statutory category and a signed written agreement says so; otherwise transfer needs a signed written assignment** (V-28). Does not protect ideas, methods, or the functional recipe itself (general knowledge, verify) | Not applicable yet; many repo assets are **AI-assisted or AI-generated** (unclear eligibility; attorney) | Contractor assignment/licence templates; provenance log |
| **Patents** | Only a genuinely novel, useful, non-obvious invention in a process, machine, manufacture or composition (V-34). Recipes and restaurant concepts are generally hard to patent (general knowledge; attorney) | Exclusive right for a limited term, public disclosure required | **No candidate invention exists**; do not create one to file | Investigate only if a real invention emerges; avoid public disclosure first |
| **Trade secrets** | Proprietary recipes, sauce formulas, processes, operating methods, supplier terms, certain financial models | Protected only while secret and subject to **reasonable secrecy measures** (Texas law summary, V-30; current codified text unconfirmed) | None formalised | Access control, NDAs, marking, need-to-know; decide what is **not** published |
| **Contract** | Ownership/licence of deliverables; confidentiality; advisor, investor, partner, brewery-collaboration terms | The main tool for clean ownership and transferability | None in place | Templates via attorney |
| **Domain/digital control** | Domains, handles, hosting, repos, analytics, ad accounts, email lists | Control, not IP; losing control loses the asset | Unknown | Ownership register, company-owned accounts, 2-person recovery |

## 3. AI-assisted and generated material (provenance rule)
Much of the repository text was drafted with an AI model, and concept images were produced with external AI tools. **Treat their copyright status and tool-terms licensing as unresolved** until an attorney advises. Record per asset: `creation_method` (human / AI-assisted / AI-generated / third-party), the tool and date, and the founder's human contribution (selection, direction, editing). Do not claim copyright or exclusivity over purely generated imagery; do not use generated imagery as a logo or trademark asset without attorney review. Concept visuals remain labelled "Concept visualization".

## 4. Founder Asset Register
`founder-asset-register.csv` lists 18 asset classes (entity, marks, domains, website, repository, brand files, recipes, concept images, photography, video, social, email list, contracts, advisor agreements, investor documents, models, manuals, research corpus). **Every row currently reads NOT_ESTABLISHED, NOT_CREATED, UNKNOWN or ESTABLISHED_FOR_ACCESS_ONLY**: nothing is claimed as owned. A status may become `OWNED_DOCUMENTED` only with an `evidence_ref` to an existing file (checked by `tools/validate_repo.py`).

## 5. Contractor and collaborator agreement checklist (before any paid or unpaid creative work)
Written, signed, **before** work begins: parties and deliverables; **ownership** (assignment of all rights in deliverables to the company/founder, or a defined licence; if "work made for hire" is used, confirm the category fits and consult counsel); **licences for third-party material** (fonts, stock, music, code libraries) with commercial-use and transfer terms; moral rights waivers where relevant; **confidentiality**; right to use for portfolio (limited); source files and credentials delivered; **no AI use without disclosure** and tool-terms compliance; warranties of originality; payment tied to assignment; **handover of accounts** (domains, hosting, repos, social); termination terms. Advisors (cultural, brewing, culinary): advisory agreements covering confidentiality, credit, compensation and **no ownership of our marks or recipes**.

## 6. Website rights checklist (every public asset must eventually answer five questions)
**Who owns this? What licence permits our use? Can we use it commercially? Can we modify it? Can we transfer the business with it?** Track in `website-asset-rights-register.csv` (header only: no website exists).
| Asset class | Provenance to record | Typical pitfalls |
|---|---|---|
| Original code | Author(s), repository, commit history, contributor agreements | Contractor code without assignment; copied snippets |
| Third-party libraries | Name, version, **licence** (permissive/copyleft), notices | Copyleft obligations; missing attribution |
| Fonts | Foundry, licence type, web embedding rights, modification rights | Desktop-only licences used on the web |
| Stock photography/video | Source, licence tier, commercial/transfer terms | Editorial-only or non-transferable licences |
| **Generated imagery** | Tool, date, prompt/inputs, tool terms, human edits | Terms limiting commercial use; unclear copyright; looks-like-real-people issues |
| Commissioned photography/video | Creator, signed agreement, releases (people, locations, props) | No model/location releases; ownership stays with creator |
| Music/audio | Composer/licensor, sync + master licences | Using unlicensed tracks |
| Illustrations/icons | Creator, licence, modification rights | Icon packs with attribution/limits |
| Copy | Author, AI assistance, source texts | Unattributed quotes; historical claims without audited wording (`HISTORICAL-CLAIMS-AUDIT.md`) |
| Trademarks on page | Owner, status (unregistered/applied/registered) | Using ® before registration; using others' marks |
| Datasets | Source, licence, personal data | Scraped or restricted data |
| Analytics/ad scripts | Vendor, data terms, consent | Missing consent, vendor lock-in, data ownership |
| People/customer content | Releases, platform terms | Testimonials without permission; **no fabricated quotes** |

## 7. Digital asset ownership rules
Domains registered to the company with a role-based email (not a personal mailbox) and 2FA with recovery documented; repositories under a company organisation; social handles registered consistently on company accounts; email list and CRM exportable and consent-based; design files, fonts, photography masters stored in company-controlled storage; analytics and advertising accounts owned by the company, agencies as **users**, never owners; password manager with shared vault; an offboarding checklist for contractors.

## 8. IP/trademark attorney scope (to scope and quote)
Entity/ownership questions as appropriate · trademark searches and filing strategy (including **NASHA** if retained as a candidate) · copyright ownership and contractor assignment · AI-provenance advice · trade-secret policy · website asset ownership review · patentability only if a real invention emerges. Questions list: `docs/decisions/ATTORNEY-QUESTIONS.md` §B. Cost `TBD`. Not a substitute for the Texas alcohol attorney.

## 9. Where things stand today
No trademark filed or cleared; no entity documented in the repository; the repository's remote account is a personal/lab GitHub account (owner of record = that account, observed from the remote URL); no website, brand files, photography, video, domains or social handles are documented; AI-generated concept images and AI-assisted text exist; **no contractor agreements, advisor agreements or IP assignments exist**. See the register.
