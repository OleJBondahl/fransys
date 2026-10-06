"""A small motor starter, built and written as one PDF into out/."""

from pathlib import Path

import fransys as fr
from fransys.colours import BK, BU

d = fr.design("demo_parts", place="C1")
cabinet = d.location("C1", "Motor starter")
x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3])
g1 = d.device("G1", "DEMO-PSU-24")
dc = d.dc_supply("24VDC", g1)
q0, q1, f1 = (
    d.device(t, p)
    for t, p in (("Q0", "DEMO-MCB-3P"), ("Q1", "DEMO-CTR-3P-24"), ("F1", "DEMO-OVERLOAD-3P"))
)
s1, s2 = (d.device(t, "DEMO-CTR-BLOCK-1NO1NC") for t in ("S1", "S2"))
x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
w1 = d.cable("W1", "DEMO-CBL-4G1.5")
m1 = d.device("M1", "DEMO-MOTOR-4KW", place=None)
d.series(ac, q0.element, q1.main, f1.main, x1, w1, m1, wire=(BK, 2.5))
d.series(dc.plus, s1.nc, d.parallel(s2.no, q1.aux), f1.aux, q1.coil, dc.minus, wire=(BU, 0.75))
cover = Path("cover.md")
cover.write_text("# Motor starter\n", encoding="utf-8")
result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))
errors = [f for f in fr.check(result) if f.severity is fr.Severity.ERROR]
if errors:
    raise SystemExit(errors)
fr.write(result, Path("out"))
