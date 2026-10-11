# Visual regression log

A baseline refresh must state why the differences are intentional (`node visual-regression.mjs --update --reason "..."`). The baseline itself is local (`.baseline/`, git-ignored); this log is the durable record.

- 2026-10-11 (Sprint 10, recorded retrospectively in Sprint 11): baseline was refreshed after 12 diffs of at most 0.4%. **Explained in Sprint 11** by rendering the Sprint 9 build (`eff294f`) and the Sprint 10 build side by side: Labs, Space and Experience at 768 px each differ by exactly 5,091 px in one 60 px band near the foot of the page, which is the footer's name paragraph (wording changed from "captivated" to "drawn in"); the About page differs across its body because the essence line and the name paragraph changed. All 12 diffs are intentional copy changes (D-71). No unexplained difference remains.
- 2026-10-11: baseline refreshed. Reason: Sprint 16 copy corrections: Chicken 65 wording, Raita-crema to Crema, birria/paneer/gobi inspiration lines, Two-Pour ritual to idea with optional second pour (text only; page heights +19 to +35 px on food and beer)
