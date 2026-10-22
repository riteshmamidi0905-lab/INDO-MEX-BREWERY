import gzip
import json
from dataclasses import asdict

import pandas as pd
import pytest

from nasha_lab import enterprise_sim as es
from nasha_lab import generator


@pytest.fixture(scope="module")
def dev(tmp_path_factory):
    out = tmp_path_factory.mktemp("sim")
    m = es.generate(es.PROFILES["dev"], out)
    return out, m


def test_dev_profile_is_clean_and_close_to_target(dev):
    out, m = dev
    assert es.check(out) == []
    cfg = es.PROFILES["dev"]
    assert abs(m["summary"]["orders"] - cfg.target_orders) / cfg.target_orders < 0.05
    assert m["tables"]["loyalty_profiles"]["rows"] == cfg.loyalty_profiles
    assert m["tables"]["employees"]["rows"] == cfg.employees
    assert m["synthetic"] is True and "SYNTHETIC" in m["disclaimer"]


def test_same_seed_same_bytes_different_seed_different_bytes(dev, tmp_path):
    out, m = dev
    m2 = es.generate(es.PROFILES["dev"], tmp_path / "b")
    assert all(m["tables"][t]["sha256"] == m2["tables"][t]["sha256"] for t in m["tables"])
    cfg = es.SimConfig(**{**asdict(es.PROFILES["dev"]), "seed": 7})
    m3 = es.generate(cfg, tmp_path / "c")
    assert m3["tables"]["orders"]["sha256"] != m["tables"]["orders"]["sha256"]


def test_baseline_generator_is_untouched_by_the_simulation():
    raw, truth = generator.generate(seed=1)
    assert len(generator.LOCATIONS) == 3 and generator.DAYS == 56
    assert len(raw["orders"]) > 1000 and truth


def test_checker_detects_corruption(dev, tmp_path):
    out, _ = dev
    bad = tmp_path / "bad"
    es.generate(es.PROFILES["dev"], bad)
    p = bad / "order_lines.csv.gz"
    df = pd.read_csv(p)
    df.loc[0, "item_id"] = "ZZZ"
    df.loc[1, "qty"] = 0
    with gzip.open(p, "wt") as fh:
        df.to_csv(fh, index=False)
    problems = es.check(bad)
    assert any("unknown item" in x for x in problems) and any("non-positive" in x for x in problems)


def test_catalog_has_no_forbidden_proteins_and_concept_skus_are_labelled():
    for c in es.CATALOG:
        assert not any(t in c[4].lower() for t in es.FORBIDDEN_TERMS)
        if c[0] == "B04" or c[0].startswith("G"):
            assert "concept" in c[5] and "never" in c[5]


def test_new_sites_open_late_and_no_order_precedes_opening(dev):
    out, _ = dev
    locs = pd.read_csv(out / "locations.csv.gz")
    orders = pd.read_csv(out / "orders.csv.gz", keep_default_na=False)
    first = orders.groupby("location_id").ts.min().str[:10]
    assert (first.reindex(locs.location_id).values >= locs.open_date.values).all()


def test_manifest_records_config_and_hashes(dev):
    out, m = dev
    disk = json.loads((out / "manifest.json").read_text())
    assert disk["config"]["seed"] == es.PROFILES["dev"].seed and len(disk["tables"]["orders"]["sha256"]) == 64
