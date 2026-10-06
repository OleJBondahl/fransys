"""A small motor starter, built and written as one PDF into out/."""

from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BK, BU


class Starter(NamedTuple):
    x1: fr.TerminalStrip
    pe: fr.Run


@fr.unit(
    "motor-starter",
    title="Motor starter",
    number="MS-1",
    revision=1,
    interface_version=1,
    date="2026-10-06",
    text="v1",
    by="OJ",
)
def starter(c: fr.Design) -> Starter:
    x0 = c.terminal_strip("X0", "DEMO-TB-2.5")
    ac = c.ac_supply("400V", "230", x0[1], x0[2], x0[3])
    dc = c.dc_supply("24VDC", c.device("G1", "DEMO-PSU-24"))
    q0, q1, f1 = (
        c.device(t, p)
        for t, p in (("Q0", "DEMO-MCB-3P"), ("Q1", "DEMO-CTR-3P-24"), ("F1", "DEMO-OVERLOAD-3P"))
    )
    s1, s2 = (c.device(t, "DEMO-CTR-BLOCK-1NO1NC") for t in ("S1", "S2"))
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5", interface=True)
    c.series(ac, q0.element, q1.main, f1.main, x1, wire=(BK, 2.5))
    c.series(dc.plus, s1.nc, c.parallel(s2.no, q1.aux), f1.aux, q1.coil, dc.minus, wire=(BU, 0.75))
    return Starter(x1, x1.run("PE", 1))


d = fr.design("demo_parts")
s = d.add(starter, "U1")
w1 = d.cable("W1", "DEMO-CBL-4G1.5")
m1 = d.device("M1", "DEMO-MOTOR-4KW")
d.series(s.x1, w1, m1.motor, wire=(BK, 2.5))
cover = Path("cover.md")
cover.write_text("# Motor starter\n", encoding="utf-8")
result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "motor-starter", cover=cover))
fr.write(result, Path("out"))
