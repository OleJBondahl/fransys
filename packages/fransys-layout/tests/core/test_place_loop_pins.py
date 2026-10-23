"""Stage 5, x: a one-lane column whose head and foot both end on its card keeps two pin points."""

from __future__ import annotations

from itertools import combinations, pairwise

import pytest
from options_fixtures import core_options

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.node_names import pin_node
from fransys_layout.core.pack import lane_pins
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_x import place_x, row_specs

from .cut_fixtures import AREA, box_sym, elem, net
from .pipeline_fixtures import cut_of, routed_of


@pytest.mark.rule("ROUTING")
def test_a_loop_column_on_two_card_pins_never_puts_two_nets_on_one_point() -> None:
    """Element k leaves on A1.p2 and returns on A1.p3: two nets, so the pins stay a pitch apart."""
    for justify in (True, False):
        options = core_options(
            justify=justify,
            box_pin_pitch_min=16,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        )
        nets = (net("go", "A1.p2", "k.n"), net("back", "k.s", "A1.p3"))
        prob = PlacementProblem(AREA, (box_sym(4), elem("k")), nets, facts=Facts())
        env = page_envs(cut_of(prob, options), prob, options)[0]
        spec = row_specs(env)[0]
        cols = tuple(c for c in env.flow.columns if c.id in spec.cols)
        assert [(e.pin.pin if e.pin else None) for c in cols for e in (*c.heads, *c.feet)] == [
            "p2",
            "p3",
        ]
        assert lane_pins(cols, env.blocks) == {}
        x = place_x(env)[0]
        assert x[pin_node("A1", "p3")] - x[pin_node("A1", "p2")] >= 16


def _on(p: tuple[int, int], a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Point p lies on the axis-parallel segment a-b, ends included."""
    xs, ys = sorted((a[0], b[0])), sorted((a[1], b[1]))
    return xs[0] <= p[0] <= xs[1] and ys[0] <= p[1] <= ys[1]


def _touch(u: tuple[tuple[int, int], ...], v: tuple[tuple[int, int], ...]) -> bool:
    """An end or corner of one polyline lies on the other (a crossing alone never does)."""
    return any(_on(p, a, b) for p in u for a, b in pairwise(v)) or any(
        _on(p, a, b) for p in v for a, b in pairwise(u)
    )


def test_a_loop_column_on_two_card_pins_routes_with_no_two_nets_touching() -> None:
    """Routed, the go and back wires of the loop touch no wire of the other net."""
    nets = (net("go", "A1.p2", "k.n"), net("back", "k.s", "A1.p3"))
    prob = PlacementProblem(AREA, (box_sym(4), elem("k")), nets, facts=Facts())
    wires = [w for page in routed_of(prob).pages for w in page.wires]
    assert {w.net for w in wires} == {"go", "back"}
    assert not [
        (u.points, v.points)
        for u, v in combinations(wires, 2)
        if u.net != v.net and _touch(u.points, v.points)
    ]
