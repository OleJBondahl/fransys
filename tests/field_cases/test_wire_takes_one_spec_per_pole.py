"""Field case: `wire=` of a series takes one `(colour, size)` per pole.

The engineering shape: a multi-pole device fed from a terminal strip, where each pole has its own
colour and size, such as brown, black and grey phases, or brown line and blue neutral. With no
supply on the path the rows give no colour, and with a supply they give one the engineer
overrides: a stated colour stays stated.

The need: `wire=` took one `(colour, size)` for all the poles of a series, so each pole needed its
own `d.detail.wire` call, the pairing the series already knows.

Decision author-0060: `wire=` also takes a tuple of `(colour, size)`, one per pole in pole order,
its length equal to the series' width. The rewrite keeps the per-pole spelling.
"""

from typing import Any

import fransys as fr
import pytest
from fransys.colours import BK, BN, GY
from fransys_author import AuthorError

_POLES = ((BN, 1.5), (BK, 2.5), (GY, 4))


def _colours(d: fr.Design) -> dict[str, str]:
    """The colour of each wire, by the strip terminal it starts or ends on."""
    model = fr.build(d).model
    return {row.from_: row.colour for row in fr.derive.wire_rows(model)}


def _sizes(d: fr.Design) -> list[str]:
    model = fr.build(d).model
    return [str(row.cross_section_mm2) for row in fr.derive.wire_rows(model)]


def _strip_to_breaker(wire: Any) -> fr.Design:
    d = fr.design("demo_parts", place="C1")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    d.series(x1[1:4], d.device("Q1", "DEMO-MCB-3P").element, wire=wire)
    return d


def _supply_to_strip(wire: Any) -> fr.Design:
    d = fr.design("demo_parts", place="C1")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4)
    out = d.terminal_strip("X2", "DEMO-TB-2.5", 3)
    mains = d.ac_supply("400V", 230, x0[1], x0[2], x0[3])
    d.series(mains, d.device("Q1", "DEMO-MCB-3P").element, out, wire=wire)
    return d


def test_each_pole_takes_its_own_colour_and_size() -> None:
    """X1:1 is brown 1.5, X1:2 black 2.5 and X1:3 grey 4, in pole order."""
    d = _strip_to_breaker(_POLES)
    assert list(_colours(d).values()) == [BN, BK, GY]
    assert _sizes(d) == ["1.5", "2.5", "4"]


def test_a_stated_colour_stays_stated_when_a_supply_would_give_one() -> None:
    """With a supply on the path the rows give black; the stated brown, black and grey win."""
    d = _supply_to_strip(_POLES)
    assert list(_colours(d).values()) == [BN, BK, GY, BN, BK, GY]


def test_a_length_that_differs_from_the_poles_raises() -> None:
    """Two specs for three poles raise, and the message gives both counts."""
    with pytest.raises(AuthorError, match=r"2 specs but the series has 3 poles"):
        _strip_to_breaker(_POLES[:2])


def test_a_size_among_the_specs_raises() -> None:
    """A bare size beside a `(colour, size)` is refused: a per-pole tuple holds specs only."""
    with pytest.raises(AuthorError, match=r"tuple of \(colour, mm2\) specs only"):
        _strip_to_breaker((_POLES[0], 1.5, _POLES[2]))


def test_a_spec_that_is_not_colour_and_size_raises() -> None:
    """A spec of three values is not a `(colour, size)`."""
    with pytest.raises(AuthorError, match=r"specs only"):
        _strip_to_breaker((_POLES[0], _POLES[1], (GY, 4, 1)))


def test_a_colour_that_is_not_allowed_raises() -> None:
    """The colour of a spec is read as a single `(colour, size)` is."""
    with pytest.raises(AuthorError, match=r"colour 'PINK' is not allowed"):
        _strip_to_breaker((*_POLES[:2], ("PINK", 4)))


def test_detail_wire_refuses_a_per_pole_tuple() -> None:
    """`d.detail.wire` is one wire: it names the fix."""
    d = fr.design("demo_parts", place="C1")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    q = d.device("Q1", "DEMO-MCB-3P")
    with pytest.raises(AuthorError, match=r"belongs to d.series"):
        d.detail.wire(x1[1], q.element["1"], wire=_POLES[:2])


def test_one_spec_still_wires_every_pole() -> None:
    """A single `(colour, size)` keeps its meaning: all poles take it."""
    assert set(_colours(_strip_to_breaker((BN, 1.5))).values()) == {BN}


def test_a_parallel_branch_takes_the_colour_of_its_pole() -> None:
    """Two breakers in parallel: each pole keeps its colour on both branches."""
    d = fr.design("demo_parts", place="C1")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4)
    out = d.terminal_strip("X2", "DEMO-TB-2.5", 3)
    mains = d.ac_supply("400V", 230, x0[1], x0[2], x0[3])
    q1, q2 = (d.device(tag, "DEMO-MCB-3P") for tag in ("Q1", "Q2"))
    d.series(mains, d.parallel(q1.element, q2.element), out, wire=_POLES)
    rows = fr.derive.wire_rows(fr.build(d).model)
    by_pole = {(r.from_, r.colour) for r in rows if r.from_.startswith("+C1-X0")}
    assert by_pole == {("+C1-X0:1", BN), ("+C1-X0:2", BK), ("+C1-X0:3", GY)}
