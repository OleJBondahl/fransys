"""Field case: one core of a cable joins one terminal to one sensor pin, and a series takes one pin in its middle.
The bug: d.pair refused a single pin at either end, and its refusal names neither the single pin nor a tuple of pins.
Fixed by author-0061 item 2, a single pin or terminal is a width-one end of d.pair."""

import fransys as fr
import pytest
from _series_ends import cores
from fransys_author import AuthorError


def test_pair_joins_one_terminal_to_one_pin() -> None:
    """Core 1 joins X8:1 to B1:1, the one wire of a width-one pair."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    d.pair(x8[1], w3, b1.sig[1])
    assert cores(fr.build(d).model, "W3") == {"1": frozenset({"X8:1", "B1:1"})}


def test_pair_refusal_names_a_pin_and_a_tuple_of_pins() -> None:
    """A non-port end is refused, and the message names both a single pin and a tuple of pins."""
    d = fr.design("demo_parts")
    w3 = d.cable("W3", "DEMO-CBL-3X0.34")
    b1 = d.device("B1", "DEMO-SENSOR-2W")
    with pytest.raises(AuthorError) as info:
        d.pair(5, w3, b1.sig)
    assert "a pin" in str(info.value)
    assert "a tuple of pins" in str(info.value)


def test_series_refusal_names_a_pin() -> None:
    """A series given a bare number is refused, and the message names a pin."""
    d = fr.design("demo_parts")
    h1 = d.device("H1", "DEMO-LAMP-24")
    with pytest.raises(AuthorError) as info:
        d.series(5, h1.lamp)
    assert "a pin" in str(info.value)


def test_series_takes_a_single_pin_at_each_end() -> None:
    """A lamp between X8:1 and X8:2 builds with no one-pin tuple and no wire override needed."""
    d = fr.design("demo_parts")
    x8 = d.terminal_strip("X8", "DEMO-TB-2.5")
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.series(x8[1], h1.lamp, x8[2], wire=("BK", 1.0))
    fr.build(d)
