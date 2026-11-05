"""examples.md's sixteen sensors keep their wires on core calls (API-DETAIL, C4)."""

import fransys as fr
from fransys.colours import BU, WH
from test_guide_high_level_first import _cols


def _sensors(*, series: bool, colour=BU):
    """examples.md's sixteen sensors: B16 added first, so the strip's next free terminal is B1's."""
    d = fr.design("demo_parts")
    with d.function("SENS", "Sensors"):
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
        for n in range(16, 0, -1):
            b = d.device(f"B{n}", "DEMO-SWITCH-2P")
            d.earth(b.sw.A)
            if series:
                d.series(b.sw, x1, wire=(colour, 0.75))
            else:
                d.series(b.sw.B, x1[17 - n], wire=(colour, 0.75))
    return d


def test_the_sensors_as_a_series_keep_the_hand_wired_wires():
    assert _cols(_sensors(series=True)) == _cols(_sensors(series=False))


def test_the_sensors_as_a_series_differ_when_a_colour_changes():
    """Can fail: a planted one-colour change in the series form is seen by the comparison."""
    assert _cols(_sensors(series=True, colour=WH)) != _cols(_sensors(series=False))
