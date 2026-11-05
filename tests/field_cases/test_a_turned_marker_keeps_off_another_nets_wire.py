"""Builder of the corpus instance w05_turned_marker: a reversing starter, two contactors feeding an overload relay through crossed phases.
Its field-case test (a wire along a turned marker's branch, layout-0243) was deleted with R873: the build draws no marker now,
and the shorts-around-markers property is held by the corpus ratchet drawing_shorts_nets."""

from __future__ import annotations

from typing import NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK, BU

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
    xc = d.terminal_strip("X2", "DEMO-TB-2.5-TWIN", 2)
    dc = d.dc_supply("24VDC", plus=xc[1], minus=xc[2], voltage=24)
    kf = d.device("K1", "DEMO-CTR-3P-NC")
    kr = d.device("K2", "DEMO-CTR-3P-NC")
    with d.function("MAIN", "Motor power"):
        q1 = d.device("Q1", "DEMO-MCB-3P")
        f1 = d.device("F1", "DEMO-OVERLOAD-3P")
        m1 = d.device("M1", "DEMO-MOTOR-4KW")
        d.series(ac, q1.element, kf.main, f1.main, m1.motor, wire=PWR)
        for src, dst in ((2, 3), (4, 1), (6, 5)):
            d.series(q1.element[src], kr.main[dst], wire=PWR)
        for out, inp in ((2, 1), (4, 3), (6, 5)):
            d.series(kr.main[out], f1.main[inp], wire=PWR)
    with d.function("CTRL", "Control"):
        s0 = d.device("S0", "DEMO-PB-NC")
        d.series(dc.plus, f1.aux, s0.sw, kf.coil, dc.minus, wire=CTRL)
        d.series(s0.sw, kr.coil, dc.minus, wire=CTRL)
    return _Io()


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_reversing, "U1")
    return fr.build(d, unit_document("reversing"))
