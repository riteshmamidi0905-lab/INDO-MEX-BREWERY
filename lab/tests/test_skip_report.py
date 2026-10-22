"""CI skip reporter: groups skips by reason, enforces the policy only in --strict mode, and shows what a module-level skip hides."""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sr", ROOT / "tools/skip_report.py"); sr = importlib.util.module_from_spec(spec); spec.loader.exec_module(sr)

XML = """<testsuites><testsuite tests="5">
<testcase classname="t.a" name="ok"/>
<testcase classname="t.keys" name="k1"><skipped type="pytest.skip" message="NASHA_PRIVATE_KEYS not set: private answer keys not available"/></testcase>
<testcase classname="t.keys" name="k2"><skipped type="pytest.skip" message="NASHA_PRIVATE_KEYS not set: private answer keys not available"/></testcase>
<testcase classname="t.otel" name="module"><skipped type="pytest.skip" message="could not import 'opentelemetry.sdk.trace': No module named 'opentelemetry.sdk'"/></testcase>
<testcase classname="t.new" name="x"><skipped type="pytest.skip" message="some brand new reason"/></testcase>
</testsuite></testsuites>"""


def test_groups_unexpected_and_over_limit_skips(tmp_path):
    f = tmp_path / "j.xml"; f.write_text(XML)
    tot, skips = sr.collect(f)
    assert tot["tests"] == 5 and tot["skipped"] == 4
    groups, problems = sr.classify(skips, json.loads((ROOT / "tests/skip-policy.json").read_text()))
    assert groups["private answer keys"]["count"] == 2
    assert "OpenTelemetry SDK missing" in groups and any("OpenTelemetry" in p for p in problems)     # the exact hidden-module case found on 2026-10-22
    assert "UNEXPECTED" in groups and any("match no allowed reason" in p for p in problems)


def test_report_only_by_default_and_strict_fails(tmp_path):
    f = tmp_path / "j.xml"; f.write_text(XML)
    assert sr.main([str(f)]) == 0 and sr.main([str(f), "--strict"]) == 1
    clean = tmp_path / "c.xml"; clean.write_text("<testsuite><testcase classname='a' name='b'/></testsuite>")
    assert sr.main([str(clean), "--strict"]) == 0
