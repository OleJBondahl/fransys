"""Field case: a cable's spare core can be marked, and a marked core clears the core-count warning.
The bug: CABLE_CORES_FEWER warned for the two cores nobody wires, because nothing in the authoring surface cleared it.
Fixed by model-0204, W1.spare(...) marks a core spare and CABLE_CORES_FEWER counts wired and spare cores together."""

import fransys as fr
from fransys.colours import BK, BN, GY


def _count_findings(*, marked: bool = True) -> list[fr.Finding]:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
    w1.core(BN, x1[1], h1[1])
    w1.core(BK, x1[2], h1[2])
    if marked:
        w1.spare(GY, at=x1[7])
        w1.spare()
    result = fr.build(d)
    return [f for f in fr.check(result) if f.code == "CABLE_CORES_FEWER"]


def test_a_spare_core_clears_the_core_count_warning() -> None:
    assert _count_findings() == []


def test_without_the_marks_the_warning_stands() -> None:
    assert len(_count_findings(marked=False)) == 1
