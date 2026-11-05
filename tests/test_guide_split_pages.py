"""The drawing, documents and reading pages' rewritten blocks keep their wire rows (API-DETAIL)."""
# RATING_CURRENT_BELOW_BRANCH 2 per default-salt build set: refusal or induced finding, asserted through expect_codes.

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BK, BU, WH
from test_guide_high_level_first import _cols


def _terminal_cabinet(*, series: bool):
    """documents.md's terminal cabinet: a two-terminal strip wired to one coil."""
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, description="Field strip")
    k1 = d.device("K1", "DEMO-CO-4P-24")
    if series:
        d.series(x1, k1.coil, x1, wire=(BK, 1.5))
    else:
        d.series(x1[1].inner, k1.coil["A1"], wire=(BK, 1.5))
        d.series(x1[2].inner, k1.coil["A2"], wire=(BK, 1.5))
    return d


def test_the_terminal_cabinet_series_keeps_the_hand_wired_wires():
    assert _cols(_terminal_cabinet(series=True)) == _cols(_terminal_cabinet(series=False))


def _lamps(*, series: bool, after_contact: bool, colour=BU):
    """drawing.md's lamp pair: two lamps across the rails, or each after a contact of a relay."""
    d = fr.design("demo_parts")
    psu = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", psu.output)
    for i in range(1, 3):
        k = d.device(f"K{i}", "DEMO-RLY-2CO-24")
        h = d.device(f"H{i}", "DEMO-LAMP-24")
        if series and after_contact:
            d.series(dc.plus, k.co_1.no, h.lamp, dc.minus, wire=(colour, 0.75))
        elif series:
            d.series(dc.plus, h.lamp, dc.minus, wire=(colour, 0.75))
        else:
            if after_contact:
                d.series(psu.output["+"], k.co_1["11"], wire=(BU, 0.75))
                d.series(k.co_1["14"], h.lamp["1"], wire=(BU, 0.75))
            else:
                d.series(psu.output["+"], h.lamp["1"], wire=(BU, 0.75))
            d.series(h.lamp["2"], psu.output["-"], wire=(BU, 0.75))
    return d


def test_the_lamp_pair_series_keeps_the_hand_wired_wires():
    for after_contact in (False, True):
        assert _cols(_lamps(series=True, after_contact=after_contact)) == _cols(_lamps(series=False, after_contact=after_contact))


def test_the_lamp_pair_series_differs_when_a_colour_changes():
    """Can fail: a planted one-colour change in the series form is seen by the comparison."""
    assert _cols(_lamps(series=True, after_contact=True, colour=WH)) != _cols(_lamps(series=False, after_contact=True))


def _branch(*, series: bool):
    """reading.md's branch rating: a 160 A fuse and a contactor on a 186 A string."""
    d = fr.design("demo_parts")
    dc = d.dc_supply("HV", d.device("G1", "DEMO-STRING-864V").string)
    f1, k1 = d.device("F1", "DEMO-FUSE-DC-160"), d.device("K1", "DEMO-CONTACTOR-DC")
    if series:
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, external=True)
        d.series(dc.plus, f1, k1, x1, wire=(BK, 1.5))
        d.series(dc.minus, x1, wire=(BK, 1.5))
    else:
        x1 = d.device("X1", "DEMO-TB-2.5", external=True)
        x2 = d.device("X2", "DEMO-TB-2.5", external=True)
        d.series(dc.plus.pin, f1[1], wire=(BK, 1.5))
        d.series(f1[2], k1[1], wire=(BK, 1.5))
        d.series(k1[2], x1["internal"], wire=(BK, 1.5))
        d.series(dc.minus.pin, x2["internal"], wire=(BK, 1.5))
    return d


def _asserted_cols(d):
    """reading.md rates the contactor below the fuse on purpose: the finding is the example's subject."""
    result = fr.build(d)
    expect_codes(result, "RATING_CURRENT_BELOW_BRANCH")
    return frozenset((r.from_, r.to, r.colour, str(r.cross_section_mm2)) for r in fr.derive.wire_rows(result.model))


def test_the_branch_series_keeps_the_wires_but_the_two_end_terminals_join_one_strip():
    """The ends differ by name only: two lone terminals have no poles, so a strip of two holds
    them, and -X1:internal, -X2:internal read -X1:1, -X1:2. The hops before them are the same."""
    new, old = (_asserted_cols(_branch(series=series)) for series in (True, False))
    assert new - old == {("-X1:1", "-K1:2", "BK", "1.5"), ("-X1:2", "-G1:-", "BK", "1.5")}
    assert old - new == {
        ("-K1:2", "-X1:internal", "BK", "1.5"),
        ("-G1:-", "-X2:internal", "BK", "1.5"),
    }


def _relays(*, series: bool):
    """drawing.md's twelve relays on one declared 24 V supply."""
    d = fr.design("demo_parts")
    psu = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", psu.output)
    for i in range(1, 13):
        with d.function(f"F{i}", f"Relay {i}"):
            k = d.device(f"K{i}", "DEMO-RLY-2CO-24")
        if series:
            d.series(dc.plus, k.coil, dc.minus, wire=(BU, 0.75))
        else:
            d.series(psu.output["+"], k.coil["A1"], wire=(BU, 0.75))
            d.series(k.coil["A2"], psu.output["-"], wire=(BU, 0.75))
    return d


def test_the_declared_relays_series_keeps_the_hand_wired_wires():
    assert _cols(_relays(series=True)) == _cols(_relays(series=False))
