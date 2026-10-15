"""Field case: a series names the side of a fixed terminal, `x1[3].outer` or `x1[3].inner`.

The engineering shape: a field wire lands on the outer side of a terminal and goes on to a fuse; a
fuse's load goes back to the outer side of another terminal. The terminal's side is the engineer's
choice, not the series' guess.

The bug: `.outer` and `.inner` are ports, and a port in a series was refused ("a pin is one wire:
pass its function or strip to the series"), so each such wire needed a `d.detail.wire`.

Decision author-0055 (API-FRICTION-2 C1): the side joins the series where the element stands; the
default of an unpinned terminal stays as it was. The rewrite keeps the pinned side.
"""

from typing import Any

import fransys as fr
import pytest
from fransys.colours import BK
from fransys_author import AuthorError


def _sides(d: fr.Design) -> set[tuple[str, str]]:
    """Each terminal end of a conductor as (terminal number, side), and the other end's pin."""
    model = fr.build(d).model
    found = set()
    conductors: list[Any] = list(model.tables["conductor"].values())
    for c in conductors:
        keys = [model.key_of(p) or () for p in (c.a, c.b)]
        for key in keys:
            if "terminal" in key:
                found.add((key[2], key[-1]))
    return found


def _design() -> tuple[fr.Design, fr.TerminalStrip, fr.TerminalStrip, fr.Device]:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 4)
    return d, x1, x2, d.device("F1", "DEMO-MCB-C6")


def test_a_pinned_outer_terminal_starts_a_series_on_its_outer_side() -> None:
    d, x1, _, f1 = _design()
    d.series(x1[3].outer, f1.element, wire=(BK, 1.5))
    assert _sides(d) == {("3", "external")}


def test_a_pinned_inner_terminal_starts_a_series_on_its_inner_side() -> None:
    d, x1, _, f1 = _design()
    d.series(x1[3].inner, f1.element, wire=(BK, 1.5))
    assert _sides(d) == {("3", "internal")}


def test_a_pinned_terminal_ends_a_series_on_the_side_it_names() -> None:
    d, _, x2, f1 = _design()
    d.series(f1.element, x2[1].outer, wire=(BK, 1.5))
    assert _sides(d) == {("1", "external")}
    d2, _, x2b, f1b = _design()
    d2.series(f1b.element, x2b[1].inner, wire=(BK, 1.5))
    assert _sides(d2) == {("1", "internal")}


def test_an_unpinned_terminal_keeps_its_default_side() -> None:
    d, x1, x2, f1 = _design()
    d.series(x1[3], f1.element, x2[1], wire=(BK, 1.5))
    assert _sides(d) == {("3", "external"), ("1", "internal")}


def test_a_pin_that_is_not_a_terminal_side_is_refused_in_the_middle() -> None:
    d, x1, x2, f1 = _design()
    with pytest.raises(AuthorError, match=r"only at the start or the end of a series"):
        d.series(x1[1].outer, f1.element["1"], x2[1].inner, wire=(BK, 1.5))
