"""A net cut twice: the page between holds no pin of it, so it gets no end there (layout-0292 d)."""

from __future__ import annotations

from options_fixtures import core_options

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.values import RefKind

from .conftest import MARKER
from .cut_fixtures import AREA, net, side
from .text_fixtures import marked_of, plan_of


def _net_across_three_pages() -> PlacementProblem:
    """Net k joins y (page 1) and z (page 3); x between them on page 2 holds no pin of it."""
    syms = tuple(side(name, 700, 500) for name in "xyz")
    return PlacementProblem(
        AREA,
        syms,
        (net("m", "x.e", "z.e"), net("k", "y.e", "z.e")),
        facts=Facts(),
    )


def test_a_net_cut_twice_links_the_pages_on_either_side_of_the_one_without_a_pin() -> None:
    plan = plan_of(
        _net_across_three_pages(),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    (tag,) = (r for r in plan.spec.reference_plan if r.net == "k" and r.kind is RefKind.TAG)
    assert [e.page for e in tag.ends] == [1, 3]
    markers = marked_of(
        _net_across_three_pages(),
        core_options(
            marker=MARKER,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert [m.page for m in markers if m.net == "k"] == [1, 3]
