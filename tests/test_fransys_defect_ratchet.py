"""The Fransys-defect ratchet (WARNINGS-ACTIONABLE W6, decision 0180).

The layout package's invented cabinet is laid out in both its variants. Each finding whose code
`findings.md` marks "Fransys" is a layout defect on a well-formed design. Their count may never
rise above the value `ceilings.toml` records under `[fransys_defects]`; the cleanup round
lowers it toward zero. The pump-station example lives in another repository, so this fixture
stands for it.
"""

import importlib.util
import sys
import tomllib
from importlib.resources import files
from pathlib import Path

from fransys_el import OPTIONS

from fransys_layout.engines import lay_out_schematic
from fransys_model.kernel import Finding, freeze

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_TESTS = ROOT / "packages" / "fransys-layout" / "tests"
SITE = "packages/fransys-layout/tests/layout_cabinet.py::build_cabinet"


def fransys_codes() -> frozenset[str]:
    """Codes whose "Who acts" cell in a `findings-*.md` page is `Fransys`."""
    found: set[str] = set()
    for page in ("findings-validators", "findings-render", "findings-pdf", "findings-kicad"):
        text = files("fransys").joinpath("guide", f"{page}.md").read_text(encoding="utf-8")
        lines = [x.strip() for x in text.splitlines() if x.strip().startswith("|")]
        rows = [[c.strip() for c in line.strip("|").split("|")] for line in lines[2:]]
        found.update(r[0] for r in rows if r[3] == "Fransys")
    return frozenset(found)


def defect_count(findings: tuple[Finding, ...], codes: frozenset[str]) -> int:
    """How many of `findings` carry a Fransys-class code."""
    return sum(1 for f in findings if f.code in codes)


def _cabinet_findings() -> tuple[Finding, ...]:
    sys.path.insert(0, str(FIXTURE_TESTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "layout_cabinet_for_ratchet", FIXTURE_TESTS / "layout_cabinet.py"
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(FIXTURE_TESTS))
    found: list[Finding] = []
    for variant in ({}, {"discovery": True}):
        found.extend(lay_out_schematic(freeze(module.build_cabinet(**variant)), OPTIONS)[1])
    return tuple(found)


def test_the_cabinet_fixture_holds_no_more_fransys_defects_than_the_ceiling():
    ceiling = tomllib.loads((ROOT / "ceilings.toml").read_text(encoding="utf-8"))[
        "fransys_defects"
    ][SITE]
    findings = _cabinet_findings()
    assert findings, "the fixture must lay out and report something, or the count proves nothing"
    assert defect_count(findings, fransys_codes()) <= ceiling


def test_the_count_sees_a_fransys_class_code():
    """Probe: a finding with a Fransys-class code adds one."""
    codes = fransys_codes()
    assert "REDUNDANT_JOG" in codes
    fake = Finding(
        code="REDUNDANT_JOG",
        severity=next(iter(_cabinet_findings())).severity,
        subjects=(),
        message="x",
    )
    assert defect_count((fake,), codes) == 1
