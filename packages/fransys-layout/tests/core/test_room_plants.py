"""Stage 5 room plants: the y a step, a fan's trunk and a crossed trunk need.

Stage 5 owns the y figures; each plant states its input and exact figure.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options
from turn_fixtures import refit

from fransys_layout.core import Facts, PlacementProblem, Sym
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import _spans
from fransys_layout.core.route import route_pages

from .conftest import MARKER
from .cut_fixtures import AREA, box_sym, elem
from .flow_builders import net, poles
from .pipeline_fixtures import cut_of, placed_from
from .place_fixtures import all_pins
from .route_fixtures import overlaps

OPTIONS = core_options(
    marker=MARKER,
)
G = OPTIONS.wiring_grid


def _pitched(name: str, pitch: int, shift: int) -> Sym:
    """A four-pole device whose pole k (both pins) sits at x = pitch * k + shift."""
    base = poles(name, 4)
    return refit(base, pins=tuple(replace(p, dx=pitch * int(p.id[1:]) + shift) for p in base.pins))


def _stair(upper_pitch: int, lower_pitch: int, shift: int) -> PlacementProblem:
    """Upper U and lower L, four nets U.s<k> to L.n<k>: the pole pitches differ, so lanes jog."""
    syms = (_pitched("U", upper_pitch, 0), _pitched("L", lower_pitch, shift))
    nets = tuple(net(f"n{k}", f"U.s{k}", f"L.n{k}") for k in range(4))
    return PlacementProblem(AREA, syms, nets, facts=Facts(far_ends=()))


def _step(prob: PlacementProblem) -> int:
    """The y from L's pin n1 down to U's pin s1, as stage 5 places them."""
    placement = placed_from(cut_of(prob, OPTIONS), prob, OPTIONS)
    pins = all_pins(placement)
    return pins[("U", "s1")][1] - pins[("L", "n1")][1]


@pytest.mark.parametrize(("args", "grid_steps"), [((24, 0, 80), 4), ((32, 24, 0), 2)])
def test_three_jogs_on_one_step_need_the_grid_steps_of_their_levels(args: tuple[int, int, int], grid_steps: int) -> None:
    """U.s<k> to L.n<k>, k 0..3: lanes 1..3 jog. Overlapping jogs take three levels (4 G), disjoint ones one level (2 G)."""
    assert _step(_stair(*args)) == grid_steps * G


def test_four_fan_trunks_with_overlapping_spans_take_four_y_lines() -> None:
    """Input: D, L and M (4 poles each), net k = D.s<k>, L.n<k>, M.n<k>: four fans, spans overlap.
    Expected: the four trunks lie on four y lines (64, 72, 80, 88) and no two runs are collinear.
    """
    syms = (poles("D", 4), poles("L", 4), poles("M", 4))
    nets = tuple(net(f"n{k}", f"D.s{k}", f"L.n{k}", f"M.n{k}") for k in range(4))
    prob = PlacementProblem(AREA, syms, nets, facts=Facts(far_ends=()))
    cut = cut_of(prob, OPTIONS)
    placement = placed_from(cut, prob, OPTIONS)
    assert sorted(t.y for pg in placement.pages for t in pg.trunks) == [64, 72, 80, 88]
    assert overlaps(route_pages(placement, cut, prob, OPTIONS)) == []


def test_a_free_tall_column_inside_a_trunk_span_stands_below_the_trunk() -> None:
    """Input: net a = D.s0, L.n0, M.n0 (trunk over D..M); T (h 96) hangs from D.s1 inside its span.
    Expected: T's body starts wire_min (8) below the trunk line, not on it.
    """
    syms = (poles("D", 2), poles("L", 2), poles("M", 2), elem("T", 16, 96), elem("W", 16, 32))
    nets = (net("a", "D.s0", "L.n0", "M.n0"), net("b", "T.s", "W.n"), net("c", "D.s1", "T.n"))
    prob = PlacementProblem(AREA, syms, nets, facts=Facts(far_ends=()))
    placement = placed_from(cut_of(prob, OPTIONS), prob, OPTIONS)
    (page,) = placement.pages
    (trunk,) = [t for t in page.trunks if t.fan == "f:a"]
    (tall,) = [p for p in page.placed if p.sym == "T"]
    assert tall.body.y == trunk.y + OPTIONS.wire_min


def test_a_box_riser_is_a_span_of_its_fan_for_the_level_ordering() -> None:
    """Input: box A1 (pins p1, p2 south) right of L and M; net k = A1.p<k>, L.n<k-1>, M.n<k-1>.
    Expected: fan f:n1's span ends at the x of A1.p1 (984), f:n2's at A1.p2 (1000).
    """
    syms = (box_sym(2), poles("L", 2), poles("M", 2))
    nets = (net("n1", "A1.p1", "L.n0", "M.n0"), net("n2", "A1.p2", "L.n1", "M.n1"))
    prob = PlacementProblem(AREA, syms, nets, facts=Facts(far_ends=()))
    (env,) = page_envs(cut_of(prob, OPTIONS), prob, OPTIONS)
    ends = {s.fan: s.x1 for s in _spans(env, place_x(env)[0])}
    assert ends == {"f:n1": 984, "f:n2": 1000}
