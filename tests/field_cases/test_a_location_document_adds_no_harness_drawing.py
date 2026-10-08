"""Field case: a location document with an added harness drawing says it draws none.

The engineering shape: a cabinet C1 with two relay modules and one harness W1 (two female
plugs mated to the modules' headers, one plain wire between the plugs, no cable). The cabinet's
schematic document adds a HARNESS_DRAWING page. The same harness also sits inside a unit whose
own mixed document adds the page.

The bug report: the cabinet document stopped with DOCUMENT_NO_DRAWINGS "the harness has no
cable", which named the wrong cause. A location document draws no top-level harness, wire-only
or cabled (ruling W-CABINET, v0.13.1): the message now says so and where to add the page. The
unit's mixed document draws the harness (decisions model-0182, pdf-0024).
"""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import RD

from fransys_model.kernel import Severity


class _Open(NamedTuple):
    """The unit exposes nothing."""


def _loom(d: fr.Design) -> Any:
    c1 = d.location("C1", "Cabinet")
    m1 = d.device("M1", "DEMO-RELAY-MOD-2", place="C1")
    m2 = d.device("M2", "DEMO-RELAY-MOD-2", place="C1")
    w1 = d.harness("W1", place="C1")
    p1 = d.device("P1", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    p2 = d.device("P2", "DEMO-HSG-4F", parent=w1, place="C1", contacts="DEMO-CRIMP-F")
    d.mate(p1, m1.j1)
    d.mate(p2, m2.j1)
    d.wire(p1[1], p2[1], wire=(RD, 0.5))
    return c1


@fr.unit("demo-looms", revision=1, interface_version=1, date="2026-10-08", text="First", by="XX")
def _looms(u: fr.Design) -> _Open:
    _loom(u)
    return _Open()


def _project(d: fr.Design) -> None:
    d.project(title="Looms", number="LM-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-10-08", text="First", created="XX")


def _cover(tmp: Path) -> Path:
    cover = tmp / "cover.md"
    cover.write_text("# Looms\n", encoding="utf-8")
    return cover


def _errors(built: fr.BuildResult) -> list[str]:
    return [f"{f.code}: {f.message}" for f in fr.check(built) if f.severity is Severity.ERROR]


@pytest.fixture(scope="module")
def top_level(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    d = fr.design("demo_parts")
    _project(d)
    c1 = _loom(d)
    cover = _cover(tmp_path_factory.mktemp("top"))
    add = (fr.PageKind.HARNESS_DRAWING,)
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover, add=add))


@pytest.fixture(scope="module")
def in_unit(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    d = fr.design("demo_parts")
    _project(d)
    d.add(_looms, "U1", place=None)
    cover = _cover(tmp_path_factory.mktemp("unit"))
    add = (fr.PageKind.HARNESS_DRAWING,)
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-looms", cover=cover, add=add)
    return fr.build(d, doc)


def test_a_location_document_says_it_draws_no_harness_drawing(top_level: fr.BuildResult) -> None:
    """The one ERROR is DOCUMENT_NO_DRAWINGS with the location text, not "has no cable"."""
    (error,) = _errors(top_level)
    assert error.startswith(
        "DOCUMENT_NO_DRAWINGS: DOCUMENT_NO_DRAWINGS (error): HARNESS_DRAWING: a location "
        "document draws no harness drawing. Add the page to the unit's or the harness's document."
    )


def test_a_units_mixed_document_draws_its_wire_only_harness(in_unit: fr.BuildResult) -> None:
    """The unit shape: its mixed document with an added drawing page builds without an ERROR."""
    assert _errors(in_unit) == []
