"""SERIES-GAPS rows: split branch A4, unit scope A5, refusals A6, AC control A8, DC power A9."""

from typing import NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK, BN, BU, RD, WH

_HOUSE = {fr.DC_SUPPLY: (RD, 0.75), fr.DC_CONTROL: (WH, 0.75), fr.DC_GROUND: (BK, 0.75)}


def _rows(d) -> dict[frozenset[str], tuple[str, float]]:
    """Each wire's (colour, size) by its two printed ends."""
    found = fr.derive.wire_rows(fr.build(d).model)
    return {frozenset((r.from_, r.to)): (r.colour, float(r.cross_section_mm2)) for r in found}


def _wire(rows: dict, a: str, b: str) -> tuple[str, float]:
    return rows[frozenset((a, b))]


def test_a_split_branch_starts_on_a_control_net_and_takes_control_rows() -> None:
    d = fr.design("demo_parts", wiring=_HOUSE)
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    s1, s2 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("S2", "DEMO-CTR-BLOCK-1NO1NC")
    k2, k3, k4 = (d.device(f"K{n}", "DEMO-CTR-3P-24") for n in (2, 3, 4))
    d.series(dc.plus, s1.nc, s2.no, k2.coil, dc.minus)
    d.series(s1.nc, k3.aux, k4.aux, k2.coil, wire=0.5)
    rows = _rows(d)
    assert _wire(rows, "-S1:62", "-K3:13") == (WH, 0.5)
    assert _wire(rows, "-K3:14", "-K4:13") == (WH, 0.5)
    assert _wire(rows, "-K4:14", "-K2:A1") == (WH, 0.5)


def test_a_series_that_reaches_no_supply_and_starts_on_no_series_net_raises() -> None:
    d = fr.design("demo_parts")
    k3, k4 = d.device("K3", "DEMO-CTR-3P-24"), d.device("K4", "DEMO-CTR-3P-24")
    with pytest.raises(fr.AuthorError, match=r"reaches no supply: give wire=\(colour, size\)"):
        d.series(k3.aux, k4.aux, wire=0.5)


class _Io(NamedTuple):
    """No boundary."""


def _unit_rows(wiring) -> dict:
    @fr.unit(
        "cab",
        revision=1,
        interface_version=1,
        date="2026-10-14",
        text="First",
        by="XX",
        title="Cabinet",
        number="C-1",
        wiring=wiring,
    )
    def cab(c):
        dc = c.dc_supply("24VDC", c.device("G1", "DEMO-PSU-24"))
        s1, k1 = c.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), c.device("K1", "DEMO-CTR-3P-24")
        c.series(dc.plus, s1.no, k1.coil, dc.minus, wire=0.75)
        return _Io()

    d = fr.design("demo_parts", wiring=_HOUSE)
    d.add(cab, "U1")
    return _rows(d)


def test_a_unit_with_no_wiring_draws_the_iec_default_not_its_parents_rows() -> None:
    rows = _unit_rows(None)
    assert {colour for colour, _ in rows.values()} == {BU}


def test_a_unit_with_wiring_draws_its_own_rows() -> None:
    rows = _unit_rows({fr.DC_SUPPLY: BN, fr.DC_CONTROL: WH, fr.DC_GROUND: BK})
    assert sorted(colour for colour, _ in rows.values()) == sorted([BN, WH, BK])


def test_a_row_with_no_size_and_no_size_on_the_series_raises() -> None:
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    s1, k1 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("K1", "DEMO-CTR-3P-24")
    with pytest.raises(fr.AuthorError, match=r"give a size: wire=0.75, or a row with a size"):
        d.series(dc.plus, s1.no, k1.coil, dc.minus)


def test_a_wiring_key_that_is_not_a_row_raises_and_names_the_rows() -> None:
    with pytest.raises(fr.AuthorError, match=r"fr.DC_SUPPLY, fr.AC_L1"):
        fr.design("demo_parts", wiring={"24V": RD})  # ty: ignore[invalid-argument-type] -- the test plants a wrong key


def test_a_table_on_the_series_replaces_only_its_rows() -> None:
    d = fr.design("demo_parts", wiring=_HOUSE)
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    s1, k1 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("K1", "DEMO-CTR-3P-24")
    d.series(dc.plus, s1.no, k1.coil, dc.minus, wire={fr.DC_CONTROL: (BN, 1.0)})
    rows = _rows(d)
    assert _wire(rows, "-G1:+", "-S1:53") == (RD, 0.75)
    assert _wire(rows, "-S1:54", "-K1:A1") == (BN, 1.0)
    assert _wire(rows, "-K1:A2", "-G1:-") == (BK, 0.75)


def test_an_ac_control_path_takes_the_rail_rows_at_its_ends_and_control_between() -> None:
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("230V", "230", x0[1], n=x0[2])
    s1, k2 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("K2", "DEMO-CTR-3P-24")
    d.series(ac.L1, s1.no, k2.coil, ac.N, wire=0.75)
    rows = _rows(d)
    assert _wire(rows, "-X0:1", "-S1:53") == (BK, 0.75)  # AC_L1
    assert _wire(rows, "-S1:54", "-K2:A1") == (RD, 0.75)  # AC_CONTROL
    assert _wire(rows, "-K2:A2", "-X0:2") == (BU, 0.75)  # AC_N


def test_a_dc_power_path_keeps_supply_and_ground_rows_on_every_wire() -> None:
    d = fr.design("demo_parts", wiring={fr.DC_SUPPLY: RD, fr.DC_GROUND: BK})
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    s1, e1 = d.device("S1", "DEMO-SWITCH-DC-2P"), d.device("E1", "DEMO-HEATER-24")
    d.series(dc, s1.main, e1.load, wire=2.5)
    rows = _rows(d)
    assert _wire(rows, "-G1:+", "-S1:1") == (RD, 2.5)
    assert _wire(rows, "-S1:2", "-E1:+") == (RD, 2.5)
    assert _wire(rows, "-G1:-", "-S1:3") == (BK, 2.5)
    assert _wire(rows, "-S1:4", "-E1:-") == (BK, 2.5)


def test_a_whole_spec_wire_ignores_the_rows() -> None:
    d = fr.design("demo_parts", wiring=_HOUSE)
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    s1, k1 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("K1", "DEMO-CTR-3P-24")
    d.series(dc.plus, s1.no, k1.coil, dc.minus, wire=(BU, 1.5))
    assert set(_rows(d).values()) == {(BU, 1.5)}


@pytest.mark.parametrize("size", [0, -1])
def test_a_size_that_is_not_positive_raises(size) -> None:
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    k1 = d.device("K1", "DEMO-CTR-3P-24")
    with pytest.raises(fr.AuthorError, match="positive cross-section"):
        d.series(dc.plus, k1.coil, dc.minus, wire=size)


def test_a_single_phase_power_path_is_l1_and_n_through_a_two_pole_switch() -> None:
    d = fr.design("demo_parts", wiring={fr.AC_L1: BN, fr.AC_N: BU})
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("230V", "230", x0[1], n=x0[2])
    s1, e1 = d.device("S1", "DEMO-SWITCH-DC-2P"), d.device("E1", "DEMO-HEATER-24")
    d.series(ac, s1.main, e1.load, wire=1.5)
    rows = _rows(d)
    assert _wire(rows, "-X0:1", "-S1:1") == (BN, 1.5)
    assert _wire(rows, "-X0:2", "-S1:3") == (BU, 1.5)
    assert _wire(rows, "-S1:2", "-E1:+") == (BN, 1.5)
    assert _wire(rows, "-S1:4", "-E1:-") == (BU, 1.5)  # the second pole stays N, not L2


def _dol(d, ac) -> None:
    q0, q1 = d.device("Q0", "DEMO-MCB-3P"), d.device("Q1", "DEMO-CTR-3P-24")
    f1, m1 = d.device("F1", "DEMO-OVERLOAD-3P"), d.device("M1", "DEMO-MOTOR-4KW")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    d.series(ac, q0.element, q1.main, f1.main, x1, w1, m1, wire=2.5)


def test_a_supply_with_n_feeds_a_three_pole_path_and_no_wire_lands_on_n() -> None:
    d = fr.design("demo_parts", wiring={fr.AC_L1: BN, fr.AC_L2: BK, fr.AC_L3: RD, fr.AC_N: BU})
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    _dol(d, ac)
    rows = _rows(d)
    assert _wire(rows, "-X0:1", "-Q0:1") == (BN, 2.5)
    assert _wire(rows, "-X0:2", "-Q0:3") == (BK, 2.5)
    assert _wire(rows, "-X0:3", "-Q0:5") == (RD, 2.5)
    assert not [k for k in rows if "-X0:4" in k]


def test_a_four_pole_first_element_on_a_supply_with_n_wires_n() -> None:
    d = fr.design("demo_parts", wiring={fr.AC_L1: BN, fr.AC_L2: BK, fr.AC_L3: RD, fr.AC_N: BU})
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    q0, x1 = d.device("Q0", "DEMO-CO-4P-24"), d.terminal_strip("X1", "DEMO-TB-2.5")
    d.series(ac, q0.co.no, x1, wire=2.5)
    rows = _rows(d)
    assert _wire(rows, "-X0:4", "-Q0:41") == (BU, 2.5)


def test_a_two_pole_first_element_on_a_three_phase_supply_with_n_names_both_counts() -> None:
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    s1, e1 = d.device("S1", "DEMO-SWITCH-DC-2P"), d.device("E1", "DEMO-HEATER-24")
    with pytest.raises(
        fr.AuthorError, match=r"S1 has 2 poles, the path from 400V carries 3 .* or 4 .*d\.series"
    ):
        d.series(ac, s1.main, e1.load, wire=1.5)
