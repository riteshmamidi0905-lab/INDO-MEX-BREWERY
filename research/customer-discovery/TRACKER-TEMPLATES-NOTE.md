AGENT ANALYSIS - NOT PROFESSIONAL REVIEW - NOT EVIDENCE

# Note for purchase-conversion-tracker.csv and repeat-intent-tracker.csv

Both files are header-only templates. No data rows exist; no event has occurred. Rules: one row per respondent per event; `data_source` is `real`, `dry_run`, `friend_family` or `SYNTHETIC-FORM-TEST`; only `real` non-friend rows may be analysed, and SYNTHETIC-FORM-TEST rows must live in a separate folder (see FIRST-30-LEARNING-PLAN.md section 9). `price_basis` states who set the price (founder-set / none / market-reference); `price_shown_usd` is blank unless a real price was shown. `session_id_link` joins to `validation/traction-event-log.csv`. Respondent ids only; contact details never in git. Cells with commas must be quoted. `reason_code` / `declined_reason_code` use CODING-SYSTEM.md codes. A stated `would_return_yn` is intent, not behaviour; use `returned_actual_yn` for behaviour. No analyser exists for these files yet (Lane B once real rows exist).
