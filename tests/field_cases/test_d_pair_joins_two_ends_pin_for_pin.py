"""Field case: a 2-wire sensor and a terminal strip joined by a 3-core cable, with the sensor's signal function stating no side.
The bug: `d.series` refused the sideless function ("has no poles"), so `W3.core(1, ...)` by hand was the only way to join the pins.
Fixed by author-0058, `d.pair(a, cable, b)` reads no side and joins `a`'s pin i to `b`'s pin i, one verb for a pin-for-pin pair."""

import fransys as fr
from _series_ends import cores


def test_pair_joins_pin_for_pin() -> None:
    """Core 1 joins X8:1 to B1:1 and core 2 joins X8:2 to B1:2."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1:3], w3, b1.sig)
    assert cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_does_not_flip_on_a_sided_function() -> None:
    """A lamp with pin 1 on the line and pin 2 on the load side still goes pin for pin."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.pair(x8[1:3], w3, h1.lamp)
    assert cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "H1:1"}),
        "2": frozenset({"X8:2", "H1:2"}),
    }
