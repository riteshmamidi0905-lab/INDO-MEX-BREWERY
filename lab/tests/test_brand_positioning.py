"""Public-facing brand positioning guard (founder direction): NASHA is presented as an independent, premium hospitality brand — 'NASHA — The Courtyard' — with no geographical or cultural fusion labels in
public-facing copy, and Growth OS itself stays industry-agnostic. Historical records, the repository name and product names are NOT scanned (they are provenance/approved menu content)."""
import re
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PF = LAB.parents[1] / "pf"
FORBIDDEN = re.compile(r"indo[\s‑-]?mex|fusion|indian|mexican|tex-mex|desi\b", re.I)
PUBLIC = [*(LAB / "nasha_lab/growth/ui").glob("*"), LAB / "nasha_lab/growth/scenarios.py"] + [p for n in ("index", "nasha", "nasha-lab", "growthos", "reliability", "security", "projects", "recruiter") for p in [PF / f"{n}.html"]] \
    + [PF / "js" / f for f in ("growth.js", "pipeline.js", "trace.js", "arch.js", "dash.js", "verify.js", "hero.js")]


def test_public_facing_copy_has_no_geographic_or_cultural_fusion_labels():
    bad = []
    for p in PUBLIC:
        if p.exists() and p.is_file():
            for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                m = FORBIDDEN.search(re.sub(r"github\.com/[^\s\"']+", "", line))     # repository URLs are provenance
                if m:
                    bad.append(f"{p.name}:{i}: {m.group(0)}")
    assert not bad, bad


def test_growth_os_is_industry_agnostic_and_nasha_is_presented_as_the_courtyard_case_study():
    ui = (LAB / "nasha_lab/growth/ui/index.html").read_text()
    assert "NASHA — The Courtyard" in ui and "GROWTH OS" in ui and "NASHA GROWTH" not in ui.upper()
    assert "restaurant" not in ui.lower() and "brewery" not in ui.lower()
    if (PF / "growthos.html").exists():
        g = (PF / "growthos.html").read_text()
        assert "industry-agnostic" in g and "NASHA — Flagship Hospitality Launch Case Study" in g
        assert "NASHA — The Courtyard" in (PF / "nasha.html").read_text()
