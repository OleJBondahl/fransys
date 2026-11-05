"""Field case: a 2-wire sensor B1 wired to two strip terminals through a 2-core cable, joined pin for pin by a tuple or a function part.
The bug: d.pair accepted terminal ranges and whole functions but refused a tuple of ports at either end and a slice of a function's pins.
Fixed by author-0061 item 3, d.pair takes a tuple of pins or a function part at either end; two devices' pins are refused as in series."""

import fransys as fr
import pytest
from _series_ends import cores
from fransys_author import AuthorError


def test_pair_takes_a_tuple_of_pins_at_the_second_end() -> None:
    """Core 1 joins X8:1 to B1:1 and core 2 joins X8:2 to B1:2, the sensor end as a tuple."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1:3], w3, (b1.sig[1], b1.sig[2]))
    assert cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_takes_a_part_of_a_function() -> None:
    """A slice of the sensor's signal function, its first two pins, joins pin for pin."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1:3], w3, b1.sig.pins[:2])
    assert cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_takes_a_tuple_of_pins_at_the_first_end() -> None:
    """A tuple at the first end joins B1:1 to X8:1 and B1:2 to X8:2."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair((b1.sig[1], b1.sig[2]), w3, x8[1:3])
    assert cores(fr.build(d).model, "W3") == {
        "1": frozenset({"X8:1", "B1:1"}),
        "2": frozenset({"X8:2", "B1:2"}),
    }


def test_pair_refuses_a_tuple_of_pins_from_two_devices() -> None:
    """A tuple whose pins belong to two devices is refused, as a series refuses it."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    b2 = d.device("B2", "DEMO-SENSOR-2W")
    with pytest.raises(AuthorError, match="holds the pins of one device"):
        d.pair(x8[1:3], w3, (b1.sig[1], b2.sig[2]))
