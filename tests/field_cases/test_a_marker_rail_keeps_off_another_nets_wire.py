"""Builder of the cross-link study's "seal" row: a starter whose supply and control circuits share a page.
Its field-case test (a link marker's rail across another net's wire, layout-0243) was deleted with R873: the build draws no marker now,
and the shorts-around-markers property is held by the DRAWING_SHORTS_NETS check on every build (neighbour-flags xfail deleted as vacuous, R1297)."""

from typing import NamedTuple

import fransys as fr
from fransys.colours import BK, BU


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
        d.series(dc.plus, s1.sw, d.parallel(s2.no, q1.aux), f1.aux, q1.coil, dc.minus, wire=(BU, 0.75))
    return _Io()
