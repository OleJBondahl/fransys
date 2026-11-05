"""Field case: a slice of strip terminals has an outer and an inner side, as one terminal does.
The bug: a slice `x1[1:4]` gave neither `.outer` nor `.inner` (AttributeError), so each run was spelled out as a tuple.
Fixed by author-0061 (API-FRICTION-3 item 8), `x1[a:b].outer` is the tuple of outer ports of terminals a to b-1, in order."""

from functools import partial
from typing import Any

import fransys as fr
from _series_ends import ends_of
from fransys.colours import BK


def _name(key: tuple[str, ...]) -> tuple[str, ...]:
    """A port key as its strip, terminal number and side, or as its item and pin."""
    if key[1] == "terminal":
        return key[0], key[2], key[-1]
    return key[0], key[-1]


_ends = partial(ends_of, name=_name)


def _design() -> tuple[fr.Design, fr.TerminalStrip, Any]:
    d = fr.design("demo_parts")
    return d, d.terminal_strip("X1", "DEMO-TB-2.5", 4), d.device("Q1", "DEMO-MCB-3P")


def _outer_run_by_slice() -> set[frozenset[Any]]:
    d, x1, q = _design()
    d.series(x1[1:4].outer, q.element, wire=(BK, 2.5))
    return _ends(d)


def _outer_run_by_tuple() -> set[frozenset[Any]]:
    d, x1, q = _design()
    d.series((x1[1].outer, x1[2].outer, x1[3].outer), q.element, wire=(BK, 2.5))
    return _ends(d)


def _inner_run_by_slice() -> set[frozenset[Any]]:
    d, x1, q = _design()
    d.series(q.element, x1[1:4].inner, wire=(BK, 2.5))
    return _ends(d)


def _inner_run_by_tuple() -> set[frozenset[Any]]:
    d, x1, q = _design()
    d.series(q.element, (x1[1].inner, x1[2].inner, x1[3].inner), wire=(BK, 2.5))
    return _ends(d)


def test_a_slice_outer_starts_a_series_on_each_terminals_outer_side() -> None:
    expected = {
        frozenset((("X1", "1", "external"), ("Q1", "1"))),
        frozenset((("X1", "2", "external"), ("Q1", "3"))),
        frozenset((("X1", "3", "external"), ("Q1", "5"))),
    }
    assert _outer_run_by_slice() == _outer_run_by_tuple() == expected


def test_a_slice_inner_ends_a_series_on_each_terminals_inner_side() -> None:
    expected = {
        frozenset((("Q1", "2"), ("X1", "1", "internal"))),
        frozenset((("Q1", "4"), ("X1", "2", "internal"))),
        frozenset((("Q1", "6"), ("X1", "3", "internal"))),
    }
    assert _inner_run_by_slice() == _inner_run_by_tuple() == expected


def test_a_slice_outer_is_one_port_per_terminal_in_order() -> None:
    _, x1, _ = _design()
    assert len(x1[1:4].outer) == 3
