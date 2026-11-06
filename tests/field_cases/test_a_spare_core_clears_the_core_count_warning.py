"""Field case: a cable's spare core can be marked, and a marked core clears the core-count warning.
The bug: CABLE_CORES_FEWER warned for the two cores nobody wires, because nothing in the authoring surface cleared it.
Fixed by model-0204, W1.spare(...) marks a core spare and CABLE_CORES_FEWER counts wired and spare cores together."""

import fransys as fr
from _expected_codes import expect_codes
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


def _screened(*, earthed: bool, spare_rest: bool) -> fr.BuildResult:
    """A 2x2x0.75 instrument cable (cores 1-4 conductors, 5 and 6 pair screens) with every conductor wired."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8, pe="DEMO-TB-PE-2.5")
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 8)
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=5)
    for n in range(1, 5):
        w1.core(n, x1[n], x2[n])
    if earthed:
        w1.core(5, x1.run("PE", 1)[1])
    if spare_rest:
        w1.spare()
    return fr.build(d)


def _cable_rows(result: fr.BuildResult):
    (cable,) = fr.derive.cable_items(result.model)
    return fr.derive.open_core_rows(result.model, cable)


def test_a_screen_is_no_core_for_the_count_and_spare_adds_no_screen_row() -> None:
    """R1793, SCREEN-0225: every conductor wired, one screen earthed on a PE terminal, spare() marks nothing."""
    result = _screened(earthed=True, spare_rest=True)
    expect_codes(result, "SCREEN_DISABLED")
    assert [f for f in fr.check(result) if f.code in {"CABLE_CORES_FEWER", "CABLE_CORES_MORE"}] == []
    assert [row.colour for row in _cable_rows(result)] == ["SH"]


def test_an_open_screen_gives_no_count_warning_and_no_row() -> None:
    result = _screened(earthed=False, spare_rest=True)
    assert [f for f in fr.check(result) if f.code == "CABLE_CORES_FEWER"] == []
    assert _cable_rows(result) == ()
