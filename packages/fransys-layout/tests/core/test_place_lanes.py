"""Stage 5, x: a column of two lanes standing on two pins of its card stands on both."""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options
from turn_fixtures import marker_views, views_of

from fransys_layout.core import Box, Facts, Options, Pin, PinRef, PlacementProblem, Size, Sym
from fransys_layout.core.clearance import Keep
from fransys_layout.core.node_names import col_node, pin_node
from fransys_layout.core.pack import lane_pins
from fransys_layout.core.pack_row import RowSpec, solve_row
from fransys_layout.core.place_env import PageEnv, page_envs
from fransys_layout.core.place_lanes import Stand, _free, _standing, _walked, stand_of
from fransys_layout.core.place_x import place_x, row_specs
from fransys_layout.core.stand_fit import Limits, fit, may_cross

from .cut_fixtures import AREA, LABEL, box_sym, elem, net
from .pipeline_fixtures import cut_of
from .place_fixtures import WALK_KEY, WALK_OPTIONS, walk_stand


def dual() -> Sym:
    """A symbol with pins a and b in two nodes on its south side, 16 G apart."""
    box = Box(-16, -16, 32, 32)
    pins = (Pin("a", "S", -8, 16, 0), Pin("b", "S", 8, 16, 1))
    return Sym(
        "dual",
        None,
        "",
        LABEL,
        pins,
        (("a",), ("b",)),
        views=views_of(box, box, box, pins, ("R0", "R180")),
    )


def _problem() -> PlacementProblem:
    syms = (box_sym(4), dual(), elem("k", 84))
    nets = (net("na", "dual.a", "A1.p2"), net("nb", "dual.b", "A1.p1"), net("nk", "A1.p4", "k.n"))
    return PlacementProblem(AREA, syms, nets, facts=Facts())


def _env(options: Options) -> PageEnv:
    prob = _problem()
    return page_envs(cut_of(prob, options), prob, options)[0]


def _stands(spec: RowSpec, x: dict[str, int]) -> list[bool]:
    """Whether each of the dual column's two lanes stands on its card pin."""
    (box, first, off), (second, more) = spec.attach["c:dual"], spec.more_pins["c:dual"][0]
    return [
        x[col_node("c:dual")] + off == x[pin_node(box, first)],
        x[col_node("c:dual")] + more == x[pin_node(box, second)],
    ]


def test_a_two_lane_column_stands_on_both_its_card_pins() -> None:
    """Lane 0 stands on its pin and lane 1 on the second, 16 G on."""
    options = core_options(
        box_pin_pitch_min=16,
    )
    env = _env(options)
    spec = row_specs(env)[0]
    assert spec.pcs["c:dual"].offsets == (0, 16)
    assert lane_pins(tuple(c for c in env.flow.columns if c.id in spec.cols), env.blocks) == {"c:dual": (("p2", 16),)}
    assert _stands(spec, place_x(env)[0]) == [True, True]
    untied = solve_row(replace(spec, more_pins={}), AREA.w)[0]
    # without the tie the second pin drifts off its column (432, not 48)
    assert _stands(spec, untied) == [True, False]


@pytest.mark.rule("G06-WIRES")
def test_a_lane_end_crosses_a_foreign_riser_only_one_cell_clear_of_it() -> None:
    """Walking left over a riser, an end one cell past it stands; an end in the riser's cell stays where it was."""

    def stand(riser_x: int) -> Stand:
        return walk_stand(8, 100, (Keep("", Box(riser_x, 90, 0, 30), "wire", "other"),))

    assert _free(164, -1, WALK_KEY, stand(160), ("mine",)) == 152
    assert _free(154, -1, WALK_KEY, stand(150), ("mine",)) == 154


def test_a_lane_end_stays_when_a_horizontal_wire_hides_the_riser_from_the_walk() -> None:
    """R1333: the end cell is tested against every foreign wire, not only those the box hit; a horizontal wire may not pull the walk past a riser."""
    riser, line = Keep("", Box(100, 90, 0, 30), "wire", "other"), Keep("", Box(100, 104, 300, 0), "wire", "third")
    assert _free(200, -1, WALK_KEY, walk_stand(8, 100, (riser, line)), ("mine",)) == 200


def test_a_run_crosses_a_foreign_wire_of_either_orientation_and_ends_a_cell_clear_of_it() -> None:
    """R1333: a vertical run crosses a horizontal foreign wire as a horizontal run crosses a vertical one."""
    across = Keep("", Box(90, 100, 20, 0), "wire", "other")
    assert may_cross(Box(100, 80, 0, 40), (100, 120), (across,), ("mine",), 8)
    assert not may_cross(Box(100, 80, 0, 20), (100, 100), (across,), ("mine",), 8)  # it ends on the wire
    assert not may_cross(Box(100, 80, 0, 22), (100, 102), (across,), ("mine",), 8)  # it ends in the wire's cell
    assert may_cross(Box(80, 100, 40, 0), (80, 100), (Keep("", Box(100, 90, 0, 20), "wire", "other"),), ("mine",), 8)


def test_a_run_never_crosses_a_marker_even_one_hung_at_a_pin_of_its_own_symbol() -> None:
    """R1790: `own` frees a symbol's footprint and wires, not its placed markers (owner 2026-10-29: no marker is crossed, even by its own fan)."""
    tag = Keep("", Box(116, 90, 12, 66), "marker", "mine")
    assert not may_cross(Box(100, 100, 40, 0), (140, 100), (tag,), ("mine",), 8)
    assert may_cross(Box(100, 100, 10, 0), (110, 100), (tag,), ("mine",), 8)  # a run that stops short of it
    assert may_cross(Box(100, 100, 40, 0), (140, 100), (tag._replace(kind="footprint"),), ("mine",), 8)  # the symbol's own footprint stays free


def test_a_lane_end_has_no_stand_when_its_marker_would_leave_the_page() -> None:
    """R1333: the page is a hard limit of the walk; None is the answer `Trunk.stood` records (layout-0507)."""
    foot = Keep("", Box(40, 90, 20, 20), "footprint", "other")
    assert _free(60, 1, WALK_KEY, walk_stand(8, 100, (foot,), limits=Limits(Size(64, 200))), ("other",)) is None
    assert _free(60, 1, WALK_KEY, walk_stand(8, 100, (foot,), limits=Limits(Size(200, 200))), ("other",)) == 64


def test_a_marker_box_left_of_the_margin_has_no_stand() -> None:
    """R1362: the content box has four sides; a box at the margin fits, one 8 left of it does not."""
    limits = Limits(Size(200, 200), margin=(16, 16))
    assert fit(Box(16, 100, 24, 8), (), (), limits) == ()
    assert fit(Box(8, 100, 24, 8), (), (), limits) is None


def test_a_lane_end_walks_past_another_fans_trunk_line_its_marker_would_touch() -> None:
    """R1331: the stand holds every other fan's trunk line, so the walk ends past it (KI-306 G4)."""
    from fransys_layout.core.flow_values import Attach

    att = Attach(None, 0, 0, PinRef("a", "p"), net="n")
    env = _env(core_options(flip_turn="R180", driver_first=True, arrow_sides=("E", "W")))
    stand = stand_of(env, (100, None), (), {}, [("g", 102, ((att, 150, None), (att, 250, None)))])
    assert any(k.box == Box(150, 102, 100, 0) and k.kind == "wire" for k in stand.keeps)
    assert _free(148, 1, WALK_KEY, walk_stand(8, 100, tuple(k for k in stand.keeps)), ("mine",)) == 256


def test_a_walked_end_with_no_stand_stays_at_its_hull_and_records_it() -> None:
    """layout-0507: the right end's box leaves the page, so it stays at 60 and `stood` says so; the left end has no arrow and stands."""
    foot = Keep("", Box(40, 90, 20, 20), "footprint", "other")
    stand = walk_stand(8, 100, (foot,), poles=(frozenset[int](), frozenset({0})), limits=Limits(Size(64, 200)))
    assert _walked((0, (20, 60), (20, 60)), 100, stand, ("other",)) == ((20, 60), (True, False))


def test_an_end_whose_walk_out_leaves_the_content_box_stands_back_toward_the_page_down_to_its_hull() -> None:
    """R1488: +1 steps run out of the box, then -1 steps (the marker stays on the end's own side) down to the hull end; none clear: no stand."""
    foot = Keep("", Box(60, 90, 20, 20), "footprint", "other")
    stand = walk_stand(8, 100, (foot,), limits=Limits(Size(64, 200)))
    lane = stand._replace(y=100)
    assert _free(60, 1, WALK_KEY, stand, ("other",)) is None
    assert _standing((60, 0), 1, lane, ("other",), 44) == 44
    assert _standing((60, 0), 1, lane, ("other",), 52) is None


def test_a_walked_end_with_no_stand_stays_at_its_hull_not_at_its_bare_end() -> None:
    """R1488: the right end stepped out to 68 finds no stand, so the lane ends at its hull 60."""
    foot = Keep("", Box(60, 90, 20, 20), "footprint", "other")
    stand = walk_stand(8, 100, (foot,), poles=(frozenset[int](), frozenset({0})), limits=Limits(Size(64, 200)))
    assert _walked((0, (20, 68), (20, 60)), 100, stand, ("other",)) == ((20, 60), (True, False))


@pytest.mark.rule("BUNDLE-LANE-END")
def test_a_keyed_arrow_is_walked_to_where_its_drawn_box_fits_not_its_generic_one() -> None:
    """layout-0524: the walk tests the arrow's drawn box (the key's offsets), the box the marker stage stands it in."""
    foot = Keep("", Box(4, 102, 8, 8), "footprint", "other")  # below the lane: meets the generic box (y 96..104), not the offset one (y 80..88)
    drawn = replace(WALK_OPTIONS, marker_fit={WALK_KEY: marker_views(Box(0, -20, 8, 8))})
    assert _free(0, 1, WALK_KEY, walk_stand(8, 100, (foot,)), ("mine",)) == 16
    assert _free(0, 1, WALK_KEY, walk_stand(8, 100, (foot,), options=drawn), ("mine",)) == 0
