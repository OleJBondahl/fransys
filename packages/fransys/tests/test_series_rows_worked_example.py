"""The SERIES-GAPS worked example (A1): wire rows by potential and phase, and changeover throws.

Every colour and size named in the spec's comments is asserted by pin pair. The example is built
inside each test, because its names (`fr.DC_SUPPLY`, `k1.co_1.no`, ...) land in Part 2 and 3.
"""

import fransys as fr
from fransys.colours import BK, BN, GY, RD, WH


def _build() -> list:
    """The spec's worked example, verbatim, and its wire rows."""
    d = fr.design(
        "demo_parts",
        wiring={
            fr.DC_SUPPLY: (RD, 0.75),
            fr.DC_CONTROL: (WH, 0.75),
            fr.DC_GROUND: (BK, 0.75),
            fr.AC_L1: BN,
            fr.AC_L2: BK,
            fr.AC_L3: GY,
        },
    )
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3])
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    q0, q1 = d.device("Q0", "DEMO-MCB-3P"), d.device("Q1", "DEMO-CTR-3P-24")
    f1, m1 = d.device("F1", "DEMO-OVERLOAD-3P"), d.device("M1", "DEMO-MOTOR-4KW")
    s1, s2 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("S2", "DEMO-CTR-BLOCK-1NO1NC")
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-CTR-3P-24")

    d.series(ac, q0.element, q1.main, f1.main, m1, wire=2.5)
    d.series(dc.plus, s1.nc, d.parallel(s2.no, q1.aux), f1.aux, q1.coil, dc.minus)
    d.series(dc.plus, k1.co_1.no, k2.coil, dc.minus)
    d.series(k1.co_1.nc, s2.nc, dc.minus, wire={fr.DC_CONTROL: (WH, 0.5)})
    return list(fr.derive.wire_rows(fr.build(d).model))


def _row(rows: list, a: str, b: str):
    """The one wire row whose two ends are pins `a` and `b`, in either order."""
    want = {f"-{a}", f"-{b}"}
    found = [r for r in rows if {r.from_, r.to} == want]
    assert len(found) == 1, f"{a} to {b}: {[(r.from_, r.to) for r in rows]}"
    return found[0]


def _check(rows: list, a: str, b: str, colour, size: float) -> None:
    row = _row(rows, a, b)
    assert (row.colour, row.cross_section_mm2) == (colour, size), f"{a} to {b}"


def test_a_power_path_keeps_each_poles_phase_colour_through_every_element() -> None:
    rows = _build()
    colour = {1: BN, 3: BK, 5: GY}
    for supply, pole in zip(("X0:1", "X0:2", "X0:3"), (1, 3, 5), strict=True):
        _check(rows, supply, f"Q0:{pole}", colour[pole], 2.5)
    for pole in (1, 3, 5):
        _check(rows, f"Q0:{pole + 1}", f"Q1:{pole}", colour[pole], 2.5)
        _check(rows, f"Q1:{pole + 1}", f"F1:{pole}", colour[pole], 2.5)


def test_a_power_path_reaches_the_motor_on_the_same_phase_colours() -> None:
    rows = _build()
    for pole, phase, colour in ((2, "U", BN), (4, "V", BK), (6, "W", GY)):
        _check(rows, f"F1:{pole}", f"M1:{phase}", colour, 2.5)


def test_a_control_path_takes_supply_potential_at_the_rails_and_control_between() -> None:
    rows = _build()
    _check(rows, "G1:+", "S1:61", RD, 0.75)
    for a, b in (
        ("S1:62", "S2:53"),
        ("S1:62", "Q1:13"),
        ("S2:54", "F1:95"),
        ("Q1:14", "F1:95"),
        ("F1:96", "Q1:A1"),
    ):
        _check(rows, a, b, WH, 0.75)
    _check(rows, "Q1:A2", "G1:-", BK, 0.75)


def test_a_changeover_throw_feeds_a_coil_with_its_common_wired_once() -> None:
    rows = _build()
    _check(rows, "G1:+", "K1:11", RD, 0.75)
    _check(rows, "K1:14", "K2:A1", WH, 0.75)
    _check(rows, "K2:A2", "G1:-", BK, 0.75)


def test_the_second_throw_branch_takes_its_table_row_and_ground_rail() -> None:
    rows = _build()
    _check(rows, "K1:12", "S2:61", WH, 0.5)
    _check(rows, "S2:62", "G1:-", BK, 0.75)
    assert sum("-K1:11" in (r.from_, r.to) for r in rows) == 1
