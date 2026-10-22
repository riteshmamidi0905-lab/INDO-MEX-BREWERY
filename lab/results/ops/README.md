# lab/results/ops

Committed outputs of `python -m nasha_lab.ops.evaluate_ops ...` (see `docs/OPS-CONTROL-CENTER.md` section 10), plus the failure-policy, authority-rules and gate-calibration trials
(`failure_policy_trials.json`, `authority_trials.json`, `gate_calibration.json`). SYNTHETIC / SIMULATED / OFFLINE / NOT PRODUCTION DEPLOYED.

## Dashboard

`dashboard.html` is the source of truth (rendered from the JSON files here by `python -m nasha_lab.ops dashboard`). `dashboard_checks.json` records the overflow and axe-core checks.
The four screenshots (`dashboard-{light,dark}-{desktop,phone}.png`, about 1 MB each) are **not** version-controlled: they are derived, and Pillow cannot shrink them without changing the text rendering
(lossless re-encoding made them 3-5 % larger; a 64-colour palette made them about 70 % smaller but altered anti-aliased glyph edges by up to 90 of 255 levels). Regenerate them, and re-check accessibility, with:

    cd lab && python -m nasha_lab.ops.render_dashboard --png

It needs `playwright`, `axe-playwright-python` and the Chromium already installed under `PLAYWRIGHT_BROWSERS_PATH` (override with `NASHA_CHROMIUM`); it does not run `playwright install`.
Earlier commits in history still contain the PNGs.
