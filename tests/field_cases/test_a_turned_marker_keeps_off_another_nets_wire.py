"""A turned link marker's branch is drawn over a wire of another net.

Engineering shape: a reversing starter. Two contactors feed an overload relay through crossed
phases, and each of the relay's three input terminals carries a wire and a link marker to the
other page. A marker at a terminal where a wire ends turns: it leaves by a branch one grid
off the terminal, along the wire row, then up to its box.

The bug: layout placed the markers first and routed after, and the router knew each marker's box
but not its branch. One phase's wire ran along the row of another phase's branch, so the page
showed three phases joined (DRAWING_SHORTS_NETS).

Fixed by layout-0243: the router keeps off every marker's drawn stub, rail and branch.
"""

from typing import NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BK, BU

from fransys_model.layout import LinkMarker, layout_of

PWR = (BK, 2.5)
CTRL = (BU, 0.75)


class _Io(NamedTuple):
    pass


@fr.unit(
    "reversing", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
    title="Reversing", number="R-1",
)  # fmt: skip
def _reversing(d):
    xp = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    ac = d.ac_supply("400V", 230, xp[1], xp[2], xp[3])
    xc = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    dc = d.dc_supply("24VDC", plus=xc[1], minus=xc[2], voltage=24)
    kf = d.device("K1", "DEMO-CTR-3P-NC")
    kr = d.device("K2", "DEMO-CTR-3P-NC")
    with d.function("MAIN", "Motor power"):
        q1 = d.device("Q1", "DEMO-MCB-3P")
        f1 = d.device("F1", "DEMO-OVERLOAD-3P")
        m1 = d.device("M1", "DEMO-MOTOR-4KW")
        d.series(ac, q1.element, kf.main, f1.main, m1.motor, wire=PWR)
        for src, dst in ((2, 3), (4, 1), (6, 5)):
            d.detail.wire(q1.element[src], kr.main[dst], wire=PWR)
        for out, inp in ((2, 1), (4, 3), (6, 5)):
            d.detail.wire(kr.main[out], f1.main[inp], wire=PWR)
    with d.function("CTRL", "Control"):
        s0 = d.device("S0", "DEMO-PB-NC")
        d.series(dc.plus, f1.aux, s0.sw, kf.coil, dc.minus, wire=CTRL)
        d.series(s0.sw, kr.coil, dc.minus, wire=CTRL)
    return _Io()


def test_no_net_is_drawn_over_a_turned_markers_branch(tmp_path) -> None:
    d = fr.design("demo_parts")
    d.add(_reversing, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Reversing\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "reversing", cover=cover))
    assert layout_of(result.model, LinkMarker)
    assert any(d.wires for d in drawn_pages(result.model).values())
    assert [f for f in fr.check(result) if f.code == "DRAWING_SHORTS_NETS"] == []
