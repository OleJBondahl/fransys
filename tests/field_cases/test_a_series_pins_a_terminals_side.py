"""Field case: a series names the side of a fixed terminal, `x1[3].outer` or `x1[3].inner`.
The bug: `.outer` and `.inner` are ports, and a port in a series was refused, so each such wire needed a `d.detail.wire`.
Fixed by author-0055 (API-FRICTION-2 C1), the side joins the series where the element stands; an unpinned terminal keeps its default."""

from typing import Any

import fransys as fr
from fransys.colours import BK


def _sides(d: fr.Design, f1: Any) -> set[tuple[str, str]]:
    """Each terminal end of a conductor as (terminal number, side), and the other end's pin."""
    _lamp = d.device("H1", "DEMO-LAMP-24")  # closes the breaker's two pins so neither is open
    for pin in ("1", "2"):
        d.series(_lamp[pin], f1.element[pin], wire=(BK, 1.5))
    model = fr.build(d).model
    found = set()
    conductors: list[Any] = list(model.tables["conductor"].values())
    for c in conductors:
        keys = [model.key_of(p) or () for p in (c.a, c.b)]
        for key in keys:
            if "terminal" in key:
                found.add((key[2], key[-1]))
    return found


def _design() -> tuple[fr.Design, fr.TerminalStrip, fr.TerminalStrip, Any]:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 4)
    f1 = d.device("F1", "DEMO-MCB-C6")
    return d, x1, x2, f1


def test_a_pinned_outer_terminal_starts_a_series_on_its_outer_side() -> None:
    d, x1, _, f1 = _design()
    d.series(x1[3].outer, f1.element, wire=(BK, 1.5))
    assert _sides(d, f1) == {("3", "external")}


def test_a_pinned_inner_terminal_starts_a_series_on_its_inner_side() -> None:
    d, x1, _, f1 = _design()
    d.series(x1[3].inner, f1.element, wire=(BK, 1.5))
    assert _sides(d, f1) == {("3", "internal")}


def test_a_pinned_terminal_ends_a_series_on_the_side_it_names() -> None:
    d, _, x2, f1 = _design()
    d.series(f1.element, x2[1].outer, wire=(BK, 1.5))
    assert _sides(d, f1) == {("1", "external")}
    d2, _, x2b, f1b = _design()
    d2.series(f1b.element, x2b[1].inner, wire=(BK, 1.5))
    assert _sides(d2, f1b) == {("1", "internal")}


def test_an_unpinned_terminal_keeps_its_default_side() -> None:
    """R1507: the default side is the one facing the other end; both ends are in this design, so x1[3] lands inner (it was outer before the rule)."""
    d, x1, x2, f1 = _design()
    d.series(x1[3], f1.element, x2[1], wire=(BK, 1.5))
    assert _sides(d, f1) == {("3", "internal"), ("1", "internal")}


def test_a_pin_in_the_middle_between_two_terminal_sides_is_a_node() -> None:
    d, x1, x2, f1 = _design()
    d.series(x1[1].outer, f1.element["1"], x2[1].inner, wire=(BK, 1.5))
    assert _sides(d, f1) == {("1", "external"), ("1", "internal")}
