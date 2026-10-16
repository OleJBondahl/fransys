"""Field case: a one-pole fuse and a neutral pin, as a tuple, make a two-wide series end.

The engineering shape: a single-pole fuse on the line and a separate neutral pin feed a two-wire
load, the load's two poles taking the fuse's load pin and the neutral in the order written.

The bug: a tuple in a series held fixed terminals or the pins of one device, so `(q1.pole_1, n.N)`
raised "a tuple in a series holds fixed terminals ... not Fn", and each wire needed a
`d.detail.wire`. A mixed tuple with a multi-pole function is refused, but in words that do not
say why.

Decision author-0061 (API-FRICTION-3 item 6): a one-pole function and a pin, given as a 2-wide
tuple, are accepted as a 2-wide end, in the order written.
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


def _parts() -> tuple[fr.Design, fr.Device, fr.Device, fr.Device]:
    d = fr.design("demo_parts")
    q1 = d.device("Q1", "DEMO-MCB-2P")
    n = d.device("N1", None, external=True, pins=("N",))
    load = d.device("SW1", "DEMO-SWITCH-DC-2P")
    return d, q1, n, load


def test_a_one_pole_fuse_and_a_neutral_pin_feed_the_two_poles_in_order() -> None:
    d, q1, n, load = _parts()
    d.series((q1.pole_1, n.N), load.main, wire=(BK, 2.5))
    assert _ends(d) == {
        frozenset((("Q1", "2"), ("SW1", "1"))),
        frozenset((("N1", "N"), ("SW1", "3"))),
    }


def test_the_order_written_sets_which_pole_each_end_takes() -> None:
    d, q1, n, load = _parts()
    d.series((n.N, q1.pole_1), load.main, wire=(BK, 2.5))
    assert _ends(d) == {
        frozenset((("N1", "N"), ("SW1", "1"))),
        frozenset((("Q1", "2"), ("SW1", "3"))),
    }


def test_a_tuple_with_a_multi_pole_function_is_refused_by_name() -> None:
    d, q1, n, load = _parts()
    with pytest.raises(AuthorError, match=r"one-pole function"):
        d.series((load.main, n.N), q1.pole_1, wire=(BK, 2.5))
