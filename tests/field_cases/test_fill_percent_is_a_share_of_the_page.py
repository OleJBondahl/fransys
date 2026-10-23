"""Field case: `fr.readability` gives each page a `fill_percent`, the share of the page it fills.

Engineering shape: one cabinet unit of four lamps on a supply.
A reader judging how full the printed pages are reads `fill_percent` of the row: a whole number
from 0 to 100, the placed extent over the content box (layout-0194).

Purpose: the reading lost `fill_percent` with the old report (R239). It is back, measured on the
`Drawing` alone (the placed ink against the page's content box). Deciding record: el-0043,
amended by R517.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}


class _Io(NamedTuple):
    H1: Any


def _unit(lamps: int):
    @fr.unit("cab", **_UNIT)
    def _lamps(c: Any) -> _Io:
        psu = c.device("G1", "DEMO-PSU-24")
        first = None
        for n in range(1, lamps + 1):
            lamp = c.device(f"H{n}", "DEMO-LAMP-24")
            first = first or lamp
            c.detail.wire(psu.output["+"], lamp.lamp["1"], wire=("RD", 50))
            c.detail.wire(lamp.lamp["2"], psu.output["-"], wire=("BK", 50))
        return _Io(H1=first)

    return _lamps


def _fill(lamps: int) -> int:
    d = fr.design("demo_parts")
    d.add(_unit(lamps), "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=cover)
    pages = fr.readability(fr.build(d, doc)).pages
    return pages[0].fill_percent


def test_fill_percent_is_a_share_of_the_page() -> None:
    assert 0 < _fill(4) <= 100


def test_the_page_row_names_the_unit_of_its_drawing_set() -> None:
    d = fr.design("demo_parts")
    d.add(_unit(4), "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=cover)
    (page, *_) = fr.readability(fr.build(d, doc)).pages
    assert page.unit is not None
