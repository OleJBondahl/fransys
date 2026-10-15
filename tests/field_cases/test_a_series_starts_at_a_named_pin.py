"""Field case: a series starts at a named pin, or at a tuple of pins for a looped branch.

The engineering shape: a relay coil whose first terminal A1 also feeds a digital input channel,
and a breaker F8 fed from the line screws of breaker F4 (a branch looped at the line screws, not
drawn from the common feed).

The bug: `d.series(k1.coil, di)` taps the coil's load side, A2, and a coil pin as the first
element was refused ("a pin is one wire"), so each wire needed a `d.detail.wire`; the looped
branch the same, one hop per pole.

Decision author-0057 (SERIES-FROM-PIN, API-FRICTION-2 C6): a pin, or a tuple of one function's
pins, is a series element. First, its pins are the load ends (the wire leaves from them); last, they
are the line ends; in the middle it is refused. The rewrite keeps a series that starts at a pin.
"""

from typing import Any

import fransys as fr
import pytest
from fransys.colours import BK
from fransys_author import AuthorError


def _name(key: tuple[str, ...]) -> tuple[str, str]:
    """The item and pin of a port key."""
    return key[0], key[-1]


def _ends(d: fr.Design) -> set[frozenset]:
    """Every conductor as the two (item, pin) it joins."""
    model = fr.build(d).model
    conductors: list[Any] = list(model.tables["conductor"].values())
    return {frozenset(_name(model.key_of(p) or ()) for p in (c.a, c.b)) for c in conductors}


def _coil() -> tuple[fr.Design, fr.Device, fr.Device]:
    d = fr.design("demo_parts")
    return d, d.device("K1", "DEMO-RLY-2CO-24"), d.device("A1", "DEMO-PLC-DI-2")


def _branch() -> tuple[fr.Design, fr.Device, fr.Device]:
    d = fr.design("demo_parts")
    return d, d.device("F4", "DEMO-MCB-3P"), d.device("F8", "DEMO-MCB-3P")


def test_a_series_leaves_a_coil_from_its_first_terminal() -> None:
    d, k1, di = _coil()
    d.series(k1.coil["A1"], di.di_1, wire=(BK, 1.0))
    assert _ends(d) == {frozenset((("K1", "A1"), ("A1", "1")))}


def test_a_looped_branch_starts_at_the_line_pins_of_the_fuse() -> None:
    d, f4, f8 = _branch()
    line = (f4.element["1"], f4.element["3"], f4.element["5"])
    d.series(line, f8.element, wire=(BK, 1.5))
    assert _ends(d) == {frozenset((("F4", pin), ("F8", pin))) for pin in ("1", "3", "5")}


def test_the_pole_order_of_the_tuple_sets_the_pairing() -> None:
    d, f4, f8 = _branch()
    d.series((f4.element["1"], f4.element["5"], f4.element["3"]), f8.element, wire=(BK, 1.5))
    assert _ends(d) == {
        frozenset((("F4", "1"), ("F8", "1"))),
        frozenset((("F4", "5"), ("F8", "3"))),
        frozenset((("F4", "3"), ("F8", "5"))),
    }


def test_a_pin_in_the_middle_is_refused_by_name() -> None:
    d, k1, di = _coil()
    with pytest.raises(AuthorError, match=r"only at the start or the end of a series"):
        d.series(di.di_1, k1.coil["A1"], k1.coil)


def test_a_tuple_in_the_middle_is_refused_by_name() -> None:
    d, f4, f8 = _branch()
    mid = (f4.element["1"], f4.element["3"], f4.element["5"])
    x = d.device("F9", "DEMO-MCB-3P")
    with pytest.raises(AuthorError, match=r"only at the start or the end of a series"):
        d.series(f8.element, mid, x.element)


def test_a_looped_branch_of_a_two_pole_breaker_spans_its_two_functions() -> None:
    d = fr.design("demo_parts")
    f4, f8 = d.device("F4", "DEMO-MCB-2P"), d.device("F8", "DEMO-MCB-2P")
    d.series((f4.pole_1["1"], f4.pole_2["3"]), (f8.pole_1["1"], f8.pole_2["3"]), wire=(BK, 1.5))
    assert _ends(d) == {frozenset((("F4", pin), ("F8", pin))) for pin in ("1", "3")}


def test_pins_of_two_devices_in_one_tuple_are_refused() -> None:
    d = fr.design("demo_parts")
    f4, f8 = d.device("F4", "DEMO-MCB-2P"), d.device("F8", "DEMO-MCB-2P")
    with pytest.raises(AuthorError, match=r"pins of one device, not F4 and F8"):
        d.series((f4.pole_1["1"], f8.pole_2["3"]), f8.pole_1)


def test_a_tuple_of_the_wrong_count_names_both_counts() -> None:
    d, f4, f8 = _branch()
    with pytest.raises(AuthorError, match=r"leaves with 2 poles .* but F8\.element takes 3 poles"):
        d.series((f4.element["1"], f4.element["3"]), f8.element, wire=(BK, 1.5))


def test_a_pin_at_the_end_is_the_line_end_and_a_whole_coil_still_leaves_from_a2() -> None:
    d, k1, di = _coil()
    d.series(k1.coil, di.di_1["1"], wire=(BK, 1.0))
    assert _ends(d) == {frozenset((("K1", "A2"), ("A1", "1")))}


def test_a_series_ends_on_the_named_terminal_of_a_coil() -> None:
    d, k1, di = _coil()
    d.series(di.di_1, k1.coil["A2"], wire=(BK, 1.0))
    assert _ends(d) == {frozenset((("A1", "1"), ("K1", "A2")))}
