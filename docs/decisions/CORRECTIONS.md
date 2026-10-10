# Corrections to Phase One (nothing deleted; errors recorded)

| # | Phase One statement | Problem found | Correction | Evidence |
|---|---|---|---|---|
| 1 | TABC: "Brewpubs cannot sell alcohol to other businesses for resale" (from a first-pass search summary) | Texas Alcoholic Beverage Code §74.08 text surfaced later authorizes a brewpub meeting conditions (holder of a BG permit, own-premises beer) to sell its beer to wholesalers/distributors/retailers; SB 515 history shows caps debated | Treat self-distribution as **possible but capped/conditional**; exact caps unresolved `[PRO]` | S-38, S-04 |
| 2 | BJCP 10A SRM 14-23 | Suspicious; hefeweizen is typically pale. May be a retrieval error | Use "pale to deep gold" and verify the official PDF | S-06; flagged in `beer/HEFEWEIZEN-BENCHMARK.md` |
| 3 | Vienna-lager heritage implied broadly for "dark/amber" Mexican lagers | Negra Modelo is a **Munich Dunkel-style** lager; Dos Equis Ámbar is Vienna-style | Distinguish Vienna (Ámbar) from Dunkel (Negra) | S-49 |
| 4 | Prost Alehouse listed as an Austin competitor | It is in **Pflugerville** | Note suburban; Aviator is a pizza/draft chain without in-house brewing | S-28 |
| 5 | Rajasthan × Oaxaca rated A | Food overlap is weak; design overlap strong | Design-only | `PAIRING-MATRIX-V2.md` |
| 6 | Badshah described as simply "strong" | It is a living artist's stage name; likely crowded | Reframed around energy | `NAMING-UNIVERSE-V2.md` |
| 7 | "Cerveceria details uncited" | Many background claims were `[UNCITED]` | Upgraded where sources found; remaining listed in `research/RESEARCH-QUALITY-AUDIT.md` | |
| 8 | Pinthouse etc. descriptions from guide pages | Pinthouse opened in 2012 and is Austin's largest brewery by volume; Lazarus opened late 2016/Jan 2017 | Updated in Austin landscape | S-29, S-30 |
| 9 | `VISUAL-DNA.md` v2 said marigold, black stoneware and terrazzo were linked to shared India/Mexico traditions ("Why" notes) | Those links are unverified `[U]` | Downgraded to design rationale under verification; materials chosen on merit (D-25) | `research/RESEARCH-QUALITY-AUDIT.md` §B |
| 10 | `visuals/prompts/V2-*` building descriptions (HALL, COURT blocks) were looser than needed (no tank orientation, arcade depth, plan) | Risk of image drift | Blocks in `build_prompts.py` aligned to `LOCKED-SCENE-DNA.md`; ARC-01, ARC-02, BRW-01, GLS-01, GLS-02 superseded by `generation-batch-01/` | D-23 |
| 11 | V2 ARC-01 asked for a "three-quarter view of the whole front"; operational diagram showed a straight row of tanks | Inconsistent with the horseshoe and with the court visible in ARC-01 | Hero camera defined (SE looking NNW); horseshoe is canonical | `LOCKED-SCENE-DNA.md` |
