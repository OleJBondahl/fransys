"""Field case: the page reading of `fr.readability` counts wire bends and wire length.

Engineering shape: a cabinet unit with a supply and a lamp joined by two wires, drawn as two
three-segment routes (two bends and 50 mm each).

Purpose: the reading was blind to wire length. A page with a known route gives its known bends
and length in G. The reading is a report, never an optimiser goal. The loose-symbol and unit-row
counts this case once held are dropped with the old report (R239).

Deciding record: model-0254.
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


@fr.unit("cab", **_UNIT)
def _wired(c: Any) -> _Io:
    h1 = c.device("H1", "DEMO-LAMP-24")
    psu = c.device("G1", "DEMO-PSU-24")
    for a, b in ((psu.output["+"], h1.lamp["1"]), (h1.lamp["2"], psu.output["-"])):
        c.detail.wire(a, b, wire=("RD", 50))
    return _Io(H1=h1)


def test_a_page_with_a_known_route_gives_its_bends_and_length() -> None:
    """Routes (168,128)-(168,152)-(48,152)-(48,128) and (32,128)-(32,144)-(152,144)-(152,128)."""
    d = fr.design("demo_parts")
    d.add(_wired, "U1")
    cover = Path(tempfile.mkdtemp()) / "c.md"
    cover.write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "cab", cover=cover)
    (page,) = fr.readability(fr.build(d, doc)).pages
    assert page.wire_bends == 4
    assert page.wire_length_g == 320  # 320 grid units of 0.3125 mm
