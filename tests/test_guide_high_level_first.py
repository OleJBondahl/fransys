"""The guide's high-level-first examples build the wires the text says (GUIDE-HIGH-LEVEL-FIRST)."""

import re

import fransys as fr
from fransys.colours import BK, BU, WH


def _cols(d) -> frozenset[tuple[str, str, str, str]]:
    """The wires of a design as (from, to, colour, size): what a rewrite must keep."""
    rows = fr.derive.wire_rows(fr.build(d).model)
    return frozenset((r.from_, r.to, r.colour, str(r.cross_section_mm2)) for r in rows)


def test_a_branch_across_several_elements_is_a_second_series():
    """A2: the second series wires S1:NC-K3, K3-K4 and K4-K2:A1 in WH 0.5."""
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
    s1, s2 = (d.device(t, "DEMO-CTR-BLOCK-1NO1NC") for t in ("S1", "S2"))
    k2, k3, k4 = (d.device(t, "DEMO-CTR-3P-24") for t in ("K2", "K3", "K4"))
    d.series(dc.plus, s1.nc, s2.no, k2.coil, dc.minus, wire=(BU, 0.75))
    d.series(s1.nc, k3.aux, k4.aux, k2.coil, wire=(WH, 0.5))
    white = {w[:2] for w in _cols(d) if w[2:] == ("WH", "0.5")}
    assert white == {("-K3:13", "-S1:62"), ("-K3:14", "-K4:13"), ("-K2:A1", "-K4:14")}


def _coils(*, series: bool, lamp_in_series: bool = False, chain_colour=BU):
    """drawing.md's coil chain with its lamp branch: three coils, one lamp, one supply."""
    d = fr.design("demo_parts")
    psu = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", psu.output)
    ks = [d.device(f"K{i}", "DEMO-RLY-2CO-24") for i in (1, 2, 3)]
    lamp = d.device("H1", "DEMO-LAMP-24")
    if not series:
        d.detail.wire(psu.output["+"], ks[0].coil["A1"], wire=(BU, 0.75))
        d.detail.wire(ks[0].coil["A2"], ks[1].coil["A1"], wire=(BU, 0.75))
        d.detail.wire(ks[1].coil["A2"], ks[2].coil["A1"], wire=(BU, 0.75))
        d.detail.wire(ks[2].coil["A2"], psu.output["-"], wire=(BU, 0.75))
    else:
        d.series(dc.plus, *(k.coil for k in ks), dc.minus, wire=(chain_colour, 0.75))
    if lamp_in_series:
        d.series(ks[0].coil, lamp.lamp, dc.minus, wire=(BU, 0.75))
    else:
        d.detail.wire(ks[0].coil["A2"], lamp.lamp["1"], wire=(BU, 0.75))
        d.detail.wire(lamp.lamp["2"], psu.output["-"], wire=(BU, 0.75))
    return d


def test_the_coil_chain_series_keeps_the_hand_wired_wires():
    assert _cols(_coils(series=True)) == _cols(_coils(series=False))


def test_the_coil_chain_series_differs_when_a_colour_changes():
    """Can fail: a planted one-colour change in the series form is seen by the comparison."""
    assert _cols(_coils(series=True, chain_colour=WH)) != _cols(_coils(series=False))


def test_the_lamp_branch_as_a_series_keeps_the_wires():
    assert _cols(_coils(series=True, lamp_in_series=True)) == _cols(_coils(series=False))


def _fault(*, series: bool):
    """reading.md's fault example: a supply, a fuse and a strip."""
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    f1 = d.device("F1", "DEMO-FUSE-DC-160")
    dc = d.dc_supply("HV", plus=x1[1], minus=x1[2], voltage=24, fault_current_a=6000)
    if series:
        d.series(dc.plus, f1.element, x1, wire=(BK, 1.5))
        d.series(dc.minus, x1, wire=(BK, 1.5))
    else:
        d.detail.wire(dc.plus.pin, f1[1], wire=(BK, 1.5))
        d.detail.wire(f1[2], x1[3], wire=(BK, 1.5))
        d.detail.wire(dc.minus.pin, x1[4], wire=(BK, 1.5))
    return d


def test_the_fault_example_series_keeps_the_hand_wired_wires():
    assert _cols(_fault(series=True)) == _cols(_fault(series=False))


def _growing_run(*, series: bool):
    """authoring.md's growing bridged run: three lamps fed from one run."""
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
    feed = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", bridged=True)
    for tag in ("H1", "H2", "H3"):
        lamp = d.device(tag, "DEMO-LAMP-24").lamp
        if series:
            d.series(dc.plus, feed, lamp, dc.minus, wire=(BU, 0.75))
        else:
            d.detail.wire(dc.plus.pin, feed, wire=(BU, 0.75))
            d.detail.wire(feed, lamp["1"], wire=(BU, 0.75))
            d.detail.wire(lamp["2"], dc.minus.pin, wire=(BU, 0.75))
    return d


def _by_run(d) -> frozenset[tuple[str, ...]]:
    """_cols with a run's terminal number dropped: the two forms number terminals alike by luck."""
    return frozenset(tuple(re.sub(r"(-X1:24V):\d+", r"\1", s) for s in w) for w in _cols(d))


def test_the_growing_run_series_keeps_the_hand_wired_wires():
    assert _by_run(_growing_run(series=True)) == _by_run(_growing_run(series=False))
