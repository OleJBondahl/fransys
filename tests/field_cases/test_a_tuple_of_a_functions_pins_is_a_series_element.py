"""Field case: a sensor function of four pins, pin 3 unused, wired to a terminal strip through a three-core cable.
The bug: a tuple in a series held fixed terminals only, and a whole function took all four pins, so each core needed a `d.detail.wire`.
Fixed by author-0055 (API-FRICTION-2 C4), a tuple of pins is an element whose pins pair in order; `Fn.pins` gives them, typed."""

from functools import partial
from typing import Any

import fransys as fr
import pytest
from _series_ends import ends_of, pin_name
from fransys.colours import BK
from fransys_author import AuthorError

_ends = partial(ends_of, name=pin_name)


def _sensor() -> tuple[fr.Design, fr.TerminalStrip, Any]:
    d = fr.design("demo_parts")
    return d, d.terminal_strip("X3", "DEMO-TB-2.5", 4), d.device("S1", "DEMO-CONN-4P")


def test_three_cores_land_on_pins_one_two_and_four() -> None:
    d, x3, s1 = _sensor()
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    d.series(x3[1:4], w1, (s1.x1[1], s1.x1[2], s1.x1[4]), wire=(BK, 1.5))
    assert _ends(d) == {frozenset((("X3", str(strip)), ("S1", str(pin)))) for strip, pin in ((1, 1), (2, 2), (3, 4))}


def test_a_tuple_of_pins_pairs_with_a_strip_in_order() -> None:
    d, x3, s1 = _sensor()
    d.series(x3[1:3], (s1.x1[4], s1.x1[2]), wire=(BK, 1.5))
    assert _ends(d) == {
        frozenset((("X3", "1"), ("S1", "4"))),
        frozenset((("X3", "2"), ("S1", "2"))),
    }


def test_fn_pins_gives_the_pins_typed_in_order() -> None:
    _, _, s1 = _sensor()
    assert [pin.name for pin in s1.x1.pins] == ["1", "2", "3", "4"]


def test_a_pin_repeated_in_a_tuple_names_the_pin() -> None:
    d, x3, s1 = _sensor()
    with pytest.raises(AuthorError, match=r"names pin 2 twice"):
        d.series(x3[1:3], (s1.x1[2], s1.x1[2]), wire=(BK, 1.5))


def test_a_tuple_of_pins_and_terminals_is_refused_by_name() -> None:
    d, x3, s1 = _sensor()
    with pytest.raises(AuthorError, match=r"fixed terminals.*or the pins of one device"):
        d.series(x3[1:3], (s1.x1[2], x3[3]), wire=(BK, 1.5))
