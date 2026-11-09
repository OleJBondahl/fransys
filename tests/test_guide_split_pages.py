"""The drawing, documents and reading pages' rewritten blocks keep their wire rows (API-DETAIL)."""
# RATING_CURRENT_BELOW_BRANCH 2 per default-salt build set: refusal or induced finding, asserted through expect_codes.

import fransys as fr
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
