"""P4.1b end to end: `cut_tall` gives a fold end a pin, and route_pages stubs it.

The stubs stand out of the fold pins s of e1 (turned S) and n of e2 (turned N), `open_stub` long.
"""

from __future__ import annotations

from options_fixtures import core_options

from fransys_layout.core import Box, Facts, PlacementProblem
from fransys_layout.core.route import route_pages

from .cut_fixtures import AREA, chain, elem
from .pipeline_fixtures import cut_of, placed_from

FOOT = ((24, 638), (24, 646))  # e1.s (S) out 8 G
HEAD = ((1288, 26), (1288, 18))  # e2.n (N) out 8 G


def tall_problem() -> PlacementProblem:
    """Four 300 G elements in one chain: taller than the page, so cut_tall folds it in two."""
    syms = [elem(f"e{i}", height=300) for i in range(4)]
    return PlacementProblem(AREA, tuple(syms), tuple(chain([s.id for s in syms])), facts=Facts())


def routed(open_stub: int, obstacles: tuple[Box, ...] = ()):
    prob, opts = (
        tall_problem(),
        core_options(
            open_stub=open_stub,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    cut = cut_of(prob, opts)
    return route_pages(placed_from(cut, prob, opts), cut, prob, opts, obstacles)


def stubs(routes) -> list[tuple[tuple[int, int], ...]]:
    return sorted(w.points for p in routes.pages for w in p.wires if w.net == "x1")


def length(routes) -> int:
    return sum(p.counts.length for p in routes.pages)


def test_the_fold_pins_draw_a_stub_of_open_stub_along_their_turned_side() -> None:
    assert stubs(routed(8)) == sorted([FOOT, HEAD])


def test_no_stub_without_open_stub() -> None:
    assert stubs(routed(0)) == []


def test_a_blocked_stub_target_is_drawn_and_counted_not_refused() -> None:
    free, blocked = routed(8), routed(8, (Box(16, 640, 16, 16),))
    assert FOOT in stubs(blocked)
    assert blocked.failed == ()
    assert blocked.findings == ()
    assert length(blocked) == length(free) == length(routed(0)) + 16
