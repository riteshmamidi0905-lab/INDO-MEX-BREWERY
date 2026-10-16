"""Dashboard render script and committed accessibility checks (Milestone 5). SYNTHETIC / OFFLINE."""
import glob
import os
import subprocess
import sys

import pytest
from nasha_lab.ops import render_dashboard as RD
from nasha_lab.ops.util import RESULTS_DIR, load_json

CHECKS = load_json(os.path.join(RESULTS_DIR, "dashboard_checks.json"))


def test_committed_checks_cover_all_four_renderings_and_are_clean():
    assert {n for n, *_ in RD.COMBOS} <= set(CHECKS) and CHECKS["first_tab_focus"].startswith("skip:")
    for name, scheme, w, h in RD.COMBOS:
        c = CHECKS[name]; assert c["viewport"] == w and c["scrollWidth"] <= w and not c["horizontal_scroll"] and c["axe"]["violations"] == [] and c["axe"]["passes"] > 0


def test_pngs_are_not_tracked_and_are_ignored():
    root = os.path.abspath(os.path.join(RESULTS_DIR, "..", "..", ".."))
    if not os.path.isdir(os.path.join(root, ".git")) and not os.path.isfile(os.path.join(root, ".git")): pytest.skip("not a git checkout")
    tracked = subprocess.run(["git", "ls-files", "lab/results/ops/*.png"], cwd=root, capture_output=True, text=True).stdout.strip()
    ign = subprocess.run(["git", "check-ignore", "lab/results/ops/dashboard-dark-phone.png"], cwd=root, capture_output=True, text=True).stdout.strip()
    assert tracked == "" and ign


def test_rendering_reproduces_the_committed_checks(tmp_path):
    pytest.importorskip("playwright"); pytest.importorskip("axe_playwright_python")
    exe = RD.chromium_path()
    if not exe or not os.path.exists(exe): pytest.skip("no Chromium available")
    got = RD.render(str(tmp_path), png=True)
    assert got == CHECKS
    for name, *_ in RD.COMBOS: assert (tmp_path / f"dashboard-{name}.png").stat().st_size > 20_000
