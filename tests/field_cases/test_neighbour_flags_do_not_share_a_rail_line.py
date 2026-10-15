"""Link markers on neighbouring terminals are drawn on one line.

Engineering shape: a motor whose three terminals each carry two wires, to two contactors
on another page. Each terminal has link markers, and the terminals stand two grids apart.

The bug: the placer checked a marker's box against the boxes and stubs placed before it, but not
its stub against their stubs. Two neighbours' branches and rails ran along one row, so one
marker's rail overlapped the next marker's stub and the page showed two nets joined
(DRAWING_SHORTS_NETS).

Open: the row has no place clean of every neighbour, so layout-0244 keeps the old places here.
The crowded-marker order fixes it (designer 2026-10-14, Q4 (c)).
"""

from typing import NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model.layout import LinkMarker, Route, layout_of


class _Io(NamedTuple):
    pass


@fr.unit(
    "motor", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
    title="Motor", number="M-1",
)  # fmt: skip
def _motor(d):
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4)
    ac = d.ac_supply("400V", 230, x0[1], x0[2], x0[3], n=x0[4])
    q1 = d.device("Q1", "DEMO-MCB-3P")
    k1 = d.device("K1", "DEMO-CTR-3P-NC")
    k2 = d.device("K2", "DEMO-CTR-3P-NC")
    with d.function("MOT", "Motor"):
        m1 = d.device("M1", "DEMO-MOTOR-4KW")
    with d.function("MAIN", "Main circuit"):
        d.series(ac, q1.element, k1.main, wire=(BK, 2.5))
        for contactor, pins in ((k1, (2, 4, 6)), (k2, (2, 4, 6))):
            for pin, phase in zip(pins, "UVW", strict=True):
                d.detail.wire(contactor.main[pin], m1.motor[phase], wire=(BK, 2.5))
    return _Io()


@pytest.mark.xfail(
    strict=True, reason="a crowded marker row: its own order (designer 2026-10-14, Q4 (c))"
)
def test_no_two_markers_stubs_share_a_line(tmp_path) -> None:
    d = fr.design("demo_parts")
    d.add(_motor, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Motor\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "motor", cover=cover))
    assert layout_of(result.model, LinkMarker)
    assert layout_of(result.model, Route)
    assert [f for f in fr.check(result) if f.code == "DRAWING_SHORTS_NETS"] == []
