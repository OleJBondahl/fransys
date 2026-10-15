"""Field case: the page score of `fr.readability` counts wire bends, wire length and loose symbols.

Engineering shape: a cabinet unit with a supply and a lamp joined by two wires, drawn as two
three-segment routes (two bends and 50 mm each). Beside them stands a relay nobody wired: its coil
has nothing connected, so it is drawn on no page (layout-0218).

Purpose: the score was blind to wire length and to symbols left out. A page with a known route
now gives its known bends and length. The unwired coil counts one loose symbol in the build and in
its unit's row; no page row carries it. A unit row adds its pages' wire counts up. The score is a
report, never an optimiser goal.

Deciding record: model-0254.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}


class _Io(NamedTuple):
    H1: Any


def _wired(c: Any) -> Any:
    h1 = c.device("H1", "DEMO-LAMP-24")
    psu = c.device("G1", "DEMO-PSU-24")
    for a, b in ((psu.output["+"], h1.lamp["1"]), (h1.lamp["2"], psu.output["-"])):
        c.detail.wire(a, b, wire=("RD", 50))
    return _Io(H1=h1)


@fr.unit("cab", **_UNIT)
def _with_loose_coil(c: Any) -> _Io:
    c.device("K2", "DEMO-RLY-2CO-24")
    return _wired(c)


@fr.unit("cab", **_UNIT)
def _without(c: Any) -> _Io:
    return _wired(c)


def _report(unit: Any) -> fr.derive.ReadabilityReport:
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=cover)
    return fr.readability(fr.build(d, doc))


@pytest.fixture(scope="module")
def loose() -> fr.derive.ReadabilityReport:
    return _report(_with_loose_coil)


@pytest.fixture(scope="module")
def wired() -> fr.derive.ReadabilityReport:
    return _report(_without)


def test_a_page_with_a_known_route_gives_its_bends_and_length(
    wired: fr.derive.ReadabilityReport,
) -> None:
    """Routes (168,128)-(168,152)-(48,152)-(48,128) and (32,128)-(32,144)-(152,144)-(152,128)."""
    (page,) = wired.pages
    assert page.wire_bends == 4
    assert str(page.wire_length_mm) == "100.0"  # 320 grid units of 0.3125 mm


def test_a_build_with_every_symbol_wired_counts_no_loose_symbol(
    wired: fr.derive.ReadabilityReport,
) -> None:
    assert wired.loose_symbols == 0
    assert [unit.loose_symbols for unit in wired.units] == [0]


def test_an_unwired_coil_counts_one_loose_symbol_and_changes_no_wire_count(
    loose: fr.derive.ReadabilityReport, wired: fr.derive.ReadabilityReport
) -> None:
    (page,) = loose.pages
    (clean,) = wired.pages
    assert loose.loose_symbols == 1
    assert (page.wire_bends, page.wire_length_mm) == (clean.wire_bends, clean.wire_length_mm)


def test_the_loose_symbol_is_counted_in_its_units_row_and_no_page_row(
    loose: fr.derive.ReadabilityReport,
) -> None:
    assert not hasattr(loose.pages[0], "loose_symbols")
    assert sum(unit.loose_symbols for unit in loose.units) == loose.loose_symbols == 1


def test_a_unit_row_adds_its_page_rows_up(loose: fr.derive.ReadabilityReport) -> None:
    (unit,) = loose.units
    assert unit.wire_bends == sum(page.wire_bends for page in loose.pages)
    assert unit.wire_length_mm == sum(page.wire_length_mm for page in loose.pages)
