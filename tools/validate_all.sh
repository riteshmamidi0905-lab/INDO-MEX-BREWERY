#!/usr/bin/env bash
# FULL NASHA VALIDATION: one command. Runs the repository validators, generated-file freshness checks, every tool selftest and the security check.
# Never weakens a validator; exits non-zero if anything fails.   Usage: bash tools/validate_all.sh
cd "$(dirname "$0")/.." || exit 2
fail=0
run() { local label="$1"; shift; if out=$("$@" 2>&1); then echo "PASS  $label"; else echo "FAIL  $label"; echo "$out" | tail -8 | sed 's/^/        /'; fail=1; fi; }
run "validate_repo (includes core5, company, site)" python3 tools/validate_repo.py
run "diet audit D-54" python3 tools/diet_audit.py
run "decision register + contradiction check" python3 tools/decision_register.py check
run "generated file is fresh: vision_handoff" python3 tools/vision_handoff.py --check
for g in founder_center action_board control_center dashboard tool_map blueprint_views; do run "generated file is fresh: $g" python3 tools/$g.py --check; done
for t in photo_ingest t1_record experiment_stats session_record glass_v2 kitchen_capacity pairing_matrix decision_register food_costing fin_model intake; do run "selftest $t" python3 tools/$t.py selftest; done
run "vision layer guard" python3 tools/vision_check.py check
run "selftest vision_check" python3 tools/vision_check.py selftest
run "security check" bash tools/security_check.sh
[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED"
exit $fail
