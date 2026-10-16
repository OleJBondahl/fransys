"""Field case: a slice of strip terminals has an outer and an inner side, as one terminal does.

The engineering shape: a run of three field wires from the outer side of terminals 1 to 3 of a
strip to the poles of a three-pole breaker, and the breaker's load back into the inner side of the
same terminals. Each run is written once for the whole slice, not terminal by terminal.

The bug: `x1[1:4]` is one series element, and a single terminal gives `.outer` and `.inner`, but a
slice gives neither ("AttributeError"), so each run had to be spelled out as a tuple of ports.

Decision author-0061 (API-FRICTION-3 item 8): `x1[a:b].outer` is the tuple of the outer ports of
terminals a to b-1, in order, and `.inner` the same on the inner side; the side is pinned, as for
one terminal. The rewrite gives the same conductors as the explicit tuple.
"""

from typing import Any

import fransys as fr
from fransys.colours import BK


def _name(key: tuple[str, ...]) -> tuple[str, ...]:
    """A port key as its strip, terminal number and side, or as its item and pin."""
    if key[1] == "terminal":
        return key[0], key[2], key[-1]
    return key[0], key[-1]


def _ends(d: fr.Design) -> set[frozenset]:
    """Every conductor as the two ends it joins."""
    model = fr.build(d).model
    conductors: list[Any] = list(model.tables["conductor"].values())
    return {frozenset(_name(model.key_of(p) or ()) for p in (c.a, c.b)) for c in conductors}


def _design() -> tuple[fr.Design, fr.TerminalStrip, fr.Device]:
    d = fr.design("demo_parts")
    return d, d.terminal_strip("X1", "DEMO-TB-2.5", 4), d.device("Q1", "DEMO-MCB-3P")


def _outer_run_by_slice() -> set[frozenset]:
    d, x1, q = _design()
    d.series(x1[1:4].outer, q.element, wire=(BK, 2.5))
    return _ends(d)


def _outer_run_by_tuple() -> set[frozenset]:
    d, x1, q = _design()
    d.series((x1[1].outer, x1[2].outer, x1[3].outer), q.element, wire=(BK, 2.5))
    return _ends(d)


def _inner_run_by_slice() -> set[frozenset]:
    d, x1, q = _design()
    d.series(q.element, x1[1:4].inner, wire=(BK, 2.5))
    return _ends(d)


def _inner_run_by_tuple() -> set[frozenset]:
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
