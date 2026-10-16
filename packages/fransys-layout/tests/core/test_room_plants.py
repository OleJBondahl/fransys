"""Stage 5 room plants: the y a step, a fan's trunk and a crossed trunk need.

Stage 5 owns the y figures; each plant states its input and exact figure.
"""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Options, PlacementProblem, Sym
from fransys_layout.core.intervals import levels
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import _spans
from fransys_layout.core.route import route_pages

from .conftest import MARKER_BOX
from .cut_fixtures import AREA, box_sym, elem
from .flow_builders import net, poles
from .pipeline_fixtures import cut_of, placed_from
from .place_fixtures import all_pins
from .route_fixtures import overlaps, reversing_pair, with_crossed

OPTIONS = Options(marker=MARKER_BOX)
G = OPTIONS.wiring_grid


def _pitched(name: str, pitch: int, shift: int) -> Sym:
    """A four-pole device whose pole k (both pins) sits at x = pitch * k + shift."""
    base = poles(name, 4)
    return replace(
        base, pins=tuple(replace(p, dx=pitch * int(p.id[1:]) + shift) for p in base.pins)
    )


def _stair(upper_pitch: int, lower_pitch: int, shift: int) -> PlacementProblem:
    """Upper U and lower L, four nets U.s<k> to L.n<k>: the pole pitches differ, so lanes jog."""
    syms = (_pitched("U", upper_pitch, 0), _pitched("L", lower_pitch, shift))
    nets = tuple(net(f"n{k}", f"U.s{k}", f"L.n{k}") for k in range(4))
    return PlacementProblem(AREA, syms, nets)


def _step(prob: PlacementProblem) -> int:
    """The y from L's pin n1 down to U's pin s1, as stage 5 places them."""
    placement = placed_from(cut_of(prob, OPTIONS), prob, OPTIONS)
    pins = all_pins(placement)
    return pins[("U", "s1")][1] - pins[("L", "n1")][1]


def test_three_overlapping_jogs_on_one_step_need_four_grid_steps() -> None:
    """Input: U pole pins at x 24k, L pole pins at x 80 (U.s<k> to L.n<k>, k 0..3): lanes 1..3 jog.
    Expected: the pin-to-pin y of that step is 4 * G, i.e. 32 with G = 8 (three levels).
    """
    assert _step(_stair(24, 0, 80)) == 4 * G


def test_three_disjoint_jogs_on_one_step_need_two_grid_steps() -> None:
    """Input: U pole pins at x 32k, L pole pins at x 24k (U.s<k> to L.n<k>, k 0..3): lanes 1..3 jog.
    Expected: the pin-to-pin y of that step is 2 * G, i.e. 16 with G = 8 (one level).
    """
    assert _step(_stair(32, 24, 0)) == 2 * G


def test_four_fan_trunks_with_overlapping_spans_take_four_y_lines() -> None:
    """Input: D, L and M (4 poles each), net k = D.s<k>, L.n<k>, M.n<k>: four fans, spans overlap.
    Expected: the four trunks lie on four y lines (56, 64, 72, 80) and no two runs are collinear.
    """
    syms = (poles("D", 4), poles("L", 4), poles("M", 4))
    nets = tuple(net(f"n{k}", f"D.s{k}", f"L.n{k}", f"M.n{k}") for k in range(4))
    prob = PlacementProblem(AREA, syms, nets)
    cut = cut_of(prob, OPTIONS)
    placement = placed_from(cut, prob, OPTIONS)
    assert sorted(t.y for pg in placement.pages for t in pg.trunks) == [56, 64, 72, 80]
    assert overlaps(route_pages(placement, cut, prob, OPTIONS)) == []


def test_crossed_fan_pins_hang_lanes_plus_levels_grid_steps_below_the_trunk() -> None:
    """Input: reversing_pair((2,1,0)), fan f:bL crossed as K2 (2,1,0): three lanes, two levels.
    Expected: the trunk line sits G * (3 + 2) = 40 above K2's pins (levels from intervals.levels).
    """
    perm = (2, 1, 0)
    prob = reversing_pair(perm)
    cut = with_crossed(cut_of(prob, OPTIONS), "f:bL", (("K2", perm),))
    placement = placed_from(cut, prob, OPTIONS)
    routes = route_pages(placement, cut, prob, OPTIONS)
    pins = all_pins(placement)
    xs = {lane: pins[("K2", f"n{perm[lane]}")][0] for lane in range(3)}
    moved = [j for j in range(3) if perm[j] != j]
    spans = [(min(xs[j], xs[perm[j]]), max(xs[j], xs[perm[j]])) for j in moved]
    n_levels = max(levels(spans, range(len(spans)))) + 1
    (trunk,) = [w for pg in routes.pages for w in pg.wires if w.kind == "trunk" and w.net == "f:bL"]
    clearance = min(pins[("K2", f"n{p}")][1] for p in perm) - trunk.points[0][1]
    assert clearance == G * (3 + n_levels)


def test_a_free_tall_column_inside_a_trunk_span_stands_below_the_trunk() -> None:
    """Input: net a = D.s0, L.n0, M.n0 (trunk over D..M); T (h 96) hangs from D.s1 inside its span.
    Expected: T's body starts wire_min (8) below the trunk line, not on it.
    """
    syms = (poles("D", 2), poles("L", 2), poles("M", 2), elem("T", 16, 96), elem("W", 16, 32))
    nets = (net("a", "D.s0", "L.n0", "M.n0"), net("b", "T.s", "W.n"), net("c", "D.s1", "T.n"))
    prob = PlacementProblem(AREA, syms, nets)
    placement = placed_from(cut_of(prob, OPTIONS), prob, OPTIONS)
    (page,) = placement.pages
    (trunk,) = [t for t in page.trunks if t.fan == "f:a"]
    (tall,) = [p for p in page.placed if p.sym == "T"]
    assert tall.body.y == trunk.y + OPTIONS.wire_min


def test_a_box_riser_is_a_span_of_its_fan_for_the_level_ordering() -> None:
    """Input: box A1 (pins p1, p2 south) right of L and M; net k = A1.p<k>, L.n<k-1>, M.n<k-1>.
    Expected: fan f:n1's span ends at the x of A1.p1 (1264), f:n2's at A1.p2 (1280).
    """
    syms = (box_sym(2), poles("L", 2), poles("M", 2))
    nets = (net("n1", "A1.p1", "L.n0", "M.n0"), net("n2", "A1.p2", "L.n1", "M.n1"))
    prob = PlacementProblem(AREA, syms, nets)
    (env,) = page_envs(cut_of(prob, OPTIONS), prob, OPTIONS)
    ends = {s.fan: s.x1 for s in _spans(env, place_x(env)[0])}
    assert ends == {"f:n1": 1264, "f:n2": 1280}
