"""Field case: a cabinet unit's supply and lamp are joined by two wires, each drawn as a three-segment route.
The bug: the page reading was blind to wire length, so a known route's bends and length were not counted.
Fixed by model-0254, the reading reports bends and length as a report, never an optimiser goal."""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document

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
        c.series(a, b, wire=("RD", 50))
    return _Io(H1=h1)


def test_a_page_with_a_known_route_gives_its_bends_and_length() -> None:
    """Routes (168,128)-(168,152)-(48,152)-(48,128) and (32,128)-(32,144)-(152,144)-(152,128)."""
    d = fr.design("demo_parts")
    d.add(_wired, "U1")
    doc = unit_document("cab")
    (page,) = fr.readability(fr.build(d, doc)).pages
    assert page.wire_bends == 4
    assert page.wire_length_g == 320  # 320 grid units of 0.3125 mm
