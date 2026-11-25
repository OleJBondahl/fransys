"""SYSTEM-UNIT-SETS (model-0485): from_release prints no set (A), unmarked is UNPRINTED_SET (B), an unprinted unit cannot be released (C)."""

from __future__ import annotations

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from _expected_codes import expect_codes

from fransys_model.derive import printed_by_release, unit_has_printer
from fransys_model.derive.document_sets import printing_document
from fransys_model.layout import DrawingSet, layout_of
from fransys_model.vocab.tables import units

pytestmark = pytest.mark.rule("UNIT-SCOPE")


class _Io(NamedTuple):
    out: fr.TerminalStrip


@fr.unit("demo-mini-mcc", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cabinet(c: fr.Design) -> _Io:
    x = c.terminal_strip("X1", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5", interface=True)
    c.earth(x.run("PE", 1)[1])
    return _Io(x)


def _system_build(tmp_path: Path, *, from_release: bool) -> fr.BuildResult:
    d = fr.design("demo_parts", place="PLANT")
    d.project(title="Demo plant", number="P-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-01-01", text="first", created="AB")
    cabinet = d.add(_cabinet, "U1", from_release=from_release)
    m = d.device("M1", "DEMO-MOTOR-4KW", external=True)
    d.series(cabinet.out, d.cable("W11", "DEMO-CBL-4G1.5", length_m=25), m.motor, wire=2.5)
    (tmp_path / "c.md").write_text("# Plant\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=tmp_path / "c.md"))


def test_a_marked_unit_prints_its_boundary_only_and_gives_no_finding(tmp_path: Path) -> None:
    result = _system_build(tmp_path, from_release=True)
    model = result.model
    unit_sets = [s for s in layout_of(model, DrawingSet).values() if s.unit is not None]
    assert unit_sets
    assert all(printed_by_release(model, u) for u in units(model))
    assert all(printing_document(model, s.unit, s.location) is None for s in unit_sets)
    assert [f for f in result.findings if f.code == "UNPRINTED_SET"] == []


def test_the_same_unit_unmarked_is_an_unprinted_set(tmp_path: Path) -> None:
    result = _system_build(tmp_path, from_release=False)
    expect_codes(result, "UNPRINTED_SET")
    assert not any(printed_by_release(result.model, u) for u in units(result.model))
    assert [f.code for f in result.findings if f.code == "UNPRINTED_SET"] == ["UNPRINTED_SET"]


def test_fr_release_of_a_unit_no_document_prints_is_refused_naming_the_unit(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    d.add(_cabinet, "U1")
    result = fr.build(d)
    assert not any(unit_has_printer(result.model, u) for u in units(result.model))
    with pytest.raises(fr.BuildFailedError) as refused:
        fr.release(result, tmp_path / "rel", unit="demo-mini-mcc")
    assert {f.code for f in refused.value.findings} >= {"RELEASE_UNIT_UNPRINTED"}
    assert "demo-mini-mcc" in str(refused.value)
    assert not (tmp_path / "rel").exists()
