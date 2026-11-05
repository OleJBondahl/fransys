"""G1 (decision 0028): layout runs only on a model with no `ERROR`.

A function marked as the boundary of two unrelated units is a validator `ERROR`
(`BOUNDARY_NOT_IN_UNIT`); layout used to raise `LayoutError` on the same model and the finding
"""

from typing import Any

import fransys as fr
import fransys_pdf
import fransys_render
import pytest
from _expected_codes import expect_codes
from fransys import BuildFailedError, DocumentPreset, Severity
from fransys_author.design import Design

from fransys_model.layout import Page, layout_of

_PROJECT: dict[str, Any] = {
    "title": "Layout gate",
    "number": "P-1008",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _a_boundary_of_two_unrelated_units(tmp_path) -> fr.BuildResult:
    """Two cabinets; the first cabinet's header is the boundary of both units."""
    parts = fr.parts("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    c1, grp = d.location("C1", "Cabinet"), d.group("PLC", "PLC")
    cab_a = d.scope("a").unit("demo-cabinet-a", revision=1, interface="1")
    cab_a.revision(1, date="2026-01-01", text="First release", created="XX")
    cab_b = d.scope("b").unit("demo-cabinet-b", revision=1, interface="1")
    cab_b.revision(1, date="2026-01-01", text="First release", created="XX")
    header = cab_a.item("DEMO-CONN-2P", tag="X1", at=c1, group=grp)
    far = cab_b.item("DEMO-CONN-2P", tag="X2", at=c1, group=grp)
    for n, (unit, end) in enumerate(((cab_a, header), (cab_b, far)), start=1):
        loose = unit.item("DEMO-CONN-2P", tag=f"X{n}1", at=c1, group=grp)
        cable = d.cable("DEMO-CBL-4G1.5", tag=f"W{n}", at=c1)
        cable.core(1, end.fn("x1")["1"], loose.fn("x1")["1"])
        cable.core(2, end.fn("x1")["2"], loose.fn("x1")["2"])
    cab_a.boundary(header)
    cab_b.boundary(header)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo\n", encoding="utf-8")
    document = fr.document(DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    return fr.build(parts, d.draft(), document)


def test_a_boundary_of_two_unrelated_units_is_a_finding_not_a_layout_crash(tmp_path) -> None:
    result = _a_boundary_of_two_unrelated_units(tmp_path)
    expect_codes(result, "BOUNDARY_NOT_IN_UNIT", "BOUNDARY_UNCONNECTED")
    assert not layout_of(result.model, Page), "no layout ran on a model with an ERROR"


def test_check_of_an_errored_build_runs_no_pdf_or_render_check(tmp_path, monkeypatch) -> None:
    result = _a_boundary_of_two_unrelated_units(tmp_path)

    def _refuse(*_args, **_kwargs):
        pytest.fail("a check that needs layout ran on a model with an ERROR")

    monkeypatch.setattr(fransys_pdf, "check", _refuse)
    monkeypatch.setattr(fransys_render, "check", _refuse)
    findings = fr.check(result)
    expect_codes(result, "BOUNDARY_NOT_IN_UNIT", "BOUNDARY_UNCONNECTED")
    assert findings[0].severity is Severity.ERROR


def test_write_of_an_errored_build_raises_build_errors_and_writes_nothing(tmp_path) -> None:
    result = _a_boundary_of_two_unrelated_units(tmp_path)
    out_dir, intermediates = tmp_path / "out", tmp_path / "inter"
    with pytest.raises(BuildFailedError):
        fr.write(result, out_dir, intermediates=intermediates)
    expect_codes(result, "BOUNDARY_NOT_IN_UNIT", "BOUNDARY_UNCONNECTED")
    assert list(out_dir.iterdir()) == []
    assert any(intermediates.glob("*.typ")), "the Typst source still comes out"
    assert list(intermediates.glob("*.svg")) == [], "an errored build draws no page (0028 amended)"
