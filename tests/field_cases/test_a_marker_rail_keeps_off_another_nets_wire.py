"""A link marker's rail to a shared box is drawn across a wire of another net.

Engineering shape: a motor starter's control circuit. A 24 V supply feeds a stop button, a
start button in parallel with the contactor's holding contact, an overload relay's auxiliary
contact and the coil. The relay's contact has a marker whose box is shared, so its stub ends on
a rail that runs along the box edge to the box.

The bug: layout placed the markers first and routed after, and the router knew each marker's box
but not its rail. A route from the supply to the stop button crossed the rail, so the page
showed two nets joined (DRAWING_SHORTS_NETS).

Fixed by layout-0243: the router keeps off every marker's drawn stub, rail and branch.
"""

from typing import NamedTuple

import fransys as fr
from fransys.colours import BK, BU

from fransys_model.layout import LinkMarker, Route, layout_of


class _Io(NamedTuple):
    pass


@fr.unit(
    "starter", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB",
    title="Starter", number="S-1",
)  # fmt: skip
def _starter(d):
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("400V", 230, x0[1], x0[2], x0[3])
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    ac1 = d.ac_supply("230V", 230, x2[1], n=x2[2], names=("CL", "CN"))
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1)
    with d.function("MAIN", "Main circuit"):
        q1 = d.device("Q1", "DEMO-CTR-3P-NC")
        f1 = d.device("F1", "DEMO-OVERLOAD-3P")
        d.series(ac, q1.main, f1.main, wire=(BK, 2.5))
    with d.function("PSU", "Control supply"):
        d.series(ac1.L1, g1.input, ac1.N, wire=(BK, 2.5))
    with d.function("CTRL", "Control circuit"):
        s1 = d.device("S1", "DEMO-PB-NC")
        s2 = d.device("S2", "DEMO-BLOCK-1NO")
        d.series(
            dc.plus, s1.sw, d.parallel(s2.no, q1.aux), f1.aux, q1.coil, dc.minus, wire=(BU, 0.75)
        )
    return _Io()


def test_no_net_is_drawn_across_a_markers_rail(tmp_path) -> None:
    d = fr.design("demo_parts")
    d.add(_starter, "U1")
    cover = tmp_path / "cover.md"
    cover.write_text("# Starter\n", encoding="utf-8")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "starter", cover=cover))
    assert layout_of(result.model, LinkMarker)
    assert layout_of(result.model, Route)
    assert [f for f in fr.check(result) if f.code == "DRAWING_SHORTS_NETS"] == []
