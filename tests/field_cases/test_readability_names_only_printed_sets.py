"""Field case: a cabinet unit placed in a design reports readability for a set nobody prints.

Engineering shape: a design adds one cabinet unit (a relay, a lamp and a supply). One
CABINET_SCHEMATIC document prints that unit. The design's own top-level set 1 holds only the
unit's box and no document prints it.

The bug: `fr.readability` returned a row for set 1, and `PAGE_UNDERFILLED` named its page, though
no document prints that set. A reporter cabinet showed nine such pages.

Fixing decision: model-0201 (`printed_drawing_sets` is the one fact; amends 0182 and layout-0179).
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import DrawingSet, Page, layout_of

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}
_LOOK_CODES = {"PAGE_UNDERFILLED", "WIRE_OVER_LABEL", "TEXT_OVERLAP", "LONE_CELL"}


class _Io(NamedTuple):
    K1: Any


@fr.unit("cab", **_UNIT)
def _cab(c: Any) -> _Io:
    k1 = c.device("K1", "DEMO-RLY-2CO-24", interface=("coil",))
    h1 = c.device("H1", "DEMO-LAMP-24")
    psu = c.device("G1", "DEMO-PSU-24")
    for a, b in (
        (psu.output["+"], k1.coil["A1"]),
        (k1.coil["A2"], psu.output["-"]),
        (psu.output["+"], k1.co_1["11"]),
        (k1.co_1["14"], h1.lamp["1"]),
        (h1.lamp["2"], psu.output["-"]),
    ):
        c.detail.wire(a, b, wire=("RD", 50))
    return _Io(K1=k1)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_cab, "U1")
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=root / "c.md"))


def _sets(built: fr.BuildResult) -> tuple[set[int], set[int]]:
    """The numbers of the sets some document prints, and those of the unprinted ones."""
    sets = layout_of(built.model, DrawingSet).values()
    printed = {s.number for s in sets if s.unit is not None}
    return printed, {s.number for s in sets if s.unit is None}


def test_readability_has_no_row_for_a_set_nobody_prints(built: fr.BuildResult) -> None:
    printed, other = _sets(built)
    pages = layout_of(built.model, Page)
    sets = {
        layout_of(built.model, DrawingSet)[pages[row.page].drawing_set].number
        for row in fr.readability(built).pages
    }
    assert sets == printed
    assert not other & sets


def test_no_look_finding_names_a_page_of_an_unprinted_set(built: fr.BuildResult) -> None:
    """No look finding names a page of the unprinted set; only an under-fill finding may stand."""
    found = [f for f in built.findings if f.code == "PAGE_UNDERFILLED"]
    assert len(found) <= 1
    assert {f.code for f in built.findings if f.code in _LOOK_CODES} <= {"PAGE_UNDERFILLED"}
