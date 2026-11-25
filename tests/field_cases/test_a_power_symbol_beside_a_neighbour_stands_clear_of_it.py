"""Field case: the earth symbol of a supply's PE pin stands clear of the breaker beside the supply.
The bug: the earth symbol was posed straight out from the PE pin, so it overlapped the breaker's body (an OVERLAP finding).
Fixed by el-0050 (R360), an anchored item takes the first pose that meets no body, no other anchored item and not the page frame."""

import fransys as fr
from _model_build_cover import cabinet_document
from fransys.colours import BK


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    with d.function("SUP", "Incoming supply 230 V AC"):
        x0 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
        line, neutral, pe = x0.run("L", 1), x0.run("N", 1), x0.run("PE", 1)
        ac = d.ac_supply("230V", 230, line[1], n=neutral[1])
        q0 = d.device("Q1", "DEMO-MCB-2P")
        g1 = d.device("G1", "DEMO-PSU-24-PE")
        d.series(ac.L1, q0.pole_1, g1.input, q0.pole_2, ac.N, wire=(BK, 1.5))
        d.earth(pe[1], g1["PE"])
        d.dc_supply("24VDC", g1.output)
    doc = cabinet_document(d.location("CAB", "Cabinet"))
    return fr.build(d, doc)


def _overlaps(built: fr.BuildResult) -> list[fr.Finding]:
    return [f for f in fr.check(built) if f.code == "OVERLAP"]


def test_the_earth_symbol_of_the_supply_meets_no_neighbour() -> None:
    assert _overlaps(_build()) == []
