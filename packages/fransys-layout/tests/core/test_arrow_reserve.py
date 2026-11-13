"""The arrow reserve (layout-0301): a planned arrow at a row end keeps `Options.marker.w` free.

Plant: the box-riser problem of test_room_plants (one row, fans f:n1 and f:n2, f:n1's span ends at
x 1264). A synthetic arrow of f:n1 leaves the right end.
"""

from __future__ import annotations

import itertools
from dataclasses import replace

import pytest
from options_fixtures import core_options
from turn_fixtures import marker_views

from fransys_layout.core import Box, Facts, PinRef, PlacementProblem, Size
from fransys_layout.core import arrow_reserve as ar
from fransys_layout.core.arrow_reserve import lead_reserve, leg_depth, leg_feet, leg_line, leg_lines, leg_pins, leg_rows, leg_unit, reserve
from fransys_layout.core.band import arrow_box, arrow_hang, trunk_room
from fransys_layout.core.cut_end_rooms import arrow_ends, arrow_poles, arrow_room, cut_ends
from fransys_layout.core.errors import CoreError
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.geometry import marker_box_at, overlaps
from fransys_layout.core.outputs import Trunk
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_trunk import held_room
from fransys_layout.core.place_x import place_x, row_specs
from fransys_layout.core.place_y import _spans
from fransys_layout.core.values import PagePlan, Ref, RefEnd, RefKind, RowPlan, StandClass

from .conftest import MARKER, MARKER_BOX
from .cut_fixtures import AREA, box_sym
from .flow_builders import net, poles
from .pipeline_fixtures import cut_of


def _must(*args):

    line = leg_line(*args)
    assert line is not None
    return line


OPTIONS = core_options(
    marker=MARKER,
)
W = MARKER_BOX.w
ARROWED = {(1, "f", 0): ()}  # the trunk of these tests stands an arrow at its right end
ArrowMap = dict[tuple[int, str, int], tuple[tuple[int, tuple[PinRef, str]], ...]]


def _env():
    syms = (box_sym(2), poles("L", 2), poles("M", 2))
    nets = (net("n1", "A1.p1", "L.n0", "M.n0"), net("n2", "A1.p2", "L.n1", "M.n1"))
    prob = PlacementProblem(AREA, syms, nets, facts=Facts())
    (env,) = page_envs(cut_of(prob, OPTIONS), prob, OPTIONS)
    return env


def _plan(rows: int, columns: tuple[str, ...] = ()) -> PagePlan:
    return PagePlan(1, "u", tuple(RowPlan(columns if r == 0 else (), ()) for r in range(rows)), ())


def _bundle(column: str | None) -> tuple[Fan, Ref]:
    """A two-pole fan on `column` and the one stub that stands for both of its poles on page 1 (BUNDLE-PAIRS)."""
    pins = (PinRef("a", "p"), PinRef("a", "q"))
    legs = tuple(Attach(column, 0, 0, p, pole, net=f"n{pole}") for pole, p in enumerate(pins))
    stub = Ref("n0", RefKind.STUB, (RefEnd(1, None, pins[0], None, StandClass.TRUNK_END, pins[1:]),))
    return Fan("f", ("n0", "n1"), (), legs, None, 2, "below"), stub


def test_a_bundles_cross_document_stub_is_a_cut_end_at_the_right_of_the_first_row_of_its_fan() -> None:
    """R1338 G8, G10: the stub is returned with its (pin, kind) key, at the right, standing for the poles of every pin it lists."""
    fan, stub = _bundle("c1")
    (found,) = cut_ends((stub,), _plan(2, ("c1",)), (fan,), 0)
    assert (found.key, found.right, found.poles) == ((PinRef("a", "p"), "stub"), True, frozenset({0, 1}))
    assert cut_ends((stub,), _plan(2, ("c1",)), (fan,), 1) == ()


def test_a_stub_that_is_no_laned_bundles_is_no_cut_end() -> None:
    """A plain fan's stub and a bundle of box pins keep their own stand (R1338: plain fans unchanged)."""
    fan, stub = _bundle("c1")
    assert cut_ends((stub,), _plan(2, ("c1",)), (replace(fan, lanes=1),), 0) == ()
    boxed, box_stub = _bundle(None)
    assert cut_ends((box_stub,), _plan(2, ("c1",)), (boxed,), 0) == ()
    assert cut_ends((replace(stub, kind=RefKind.COPY),), _plan(2, ("c1",)), (fan,), 0) == ()


def test_a_single_lane_copy_at_the_trunk_end_is_a_right_cut_end() -> None:
    """KI-757: a copy standing at the trunk's end takes the room an arrow takes; a laned bundle's copy and a leg copy do not."""
    fan, stub = _bundle("c1")
    plain, copy = replace(fan, lanes=1), replace(stub, kind=RefKind.COPY)
    (found,) = cut_ends((copy,), _plan(2, ("c1",)), (plain,), 0)
    assert (found.key, found.right) == ((PinRef("a", "p"), "copy"), True)
    assert arrow_ends((copy,), _plan(2, ("c1",)), (plain,), 0) == (0, 1)
    leg = replace(copy, ends=(replace(copy.ends[0], stand=StandClass.LEG),))
    assert cut_ends((leg,), _plan(2, ("c1",)), (plain,), 0) == ()


def _arrow(page: int, row: int) -> Ref:
    """An arrow of f:n1 leaving the right end of (page, row) and entering the next row's left."""
    return Ref("f:n1", RefKind.ARROW, (RefEnd(page, None, None, row), RefEnd(page, None, None, row + 1)))


def test_the_reserve_is_the_marker_width_for_an_arrow_and_zero_without() -> None:
    assert (reserve(0, OPTIONS), reserve(1, OPTIONS), reserve(3, OPTIONS)) == (0, W, W)
    refs, plan = (_arrow(1, 0),), _plan(2)
    f1, f2 = (Fan(f"f:n{i}", (f"n{i}",), (), (), None, 1, "below") for i in (1, 2))
    assert arrow_ends(refs, plan, (f1, f2), 0) == (0, 1)
    assert arrow_ends(refs, plan, (f1, f2), 1) == (1, 0)
    assert arrow_ends(refs, plan, (f2,), 0) == (0, 0)


def test_the_poles_of_an_arrows_ends_are_those_of_the_attachments_at_its_pins() -> None:
    legs = (Attach(None, 0, 0, PinRef("a", "p"), 0, net="n"), Attach(None, 0, 0, PinRef("b", "p"), 1, net="n"))
    fan = Fan("f:n1", ("n", "m"), (), legs, None, 2, "below")
    ref = Ref("f:n1", RefKind.ARROW, (RefEnd(1, None, PinRef("a", "p"), 0), RefEnd(1, None, PinRef("b", "p"), 1)))
    assert arrow_poles(fan, (ref,), _plan(2), 0) == (frozenset(), frozenset({0}))
    assert arrow_poles(fan, (ref,), _plan(2), 1) == (frozenset({1}), frozenset())
    assert arrow_poles(replace(fan, lanes=1), (ref,), _plan(2), 1) == (frozenset({0}), frozenset())


def test_a_row_end_arrow_sets_the_tail_reserve_to_the_marker_width_and_a_grid_step() -> None:
    """Expected: the tail keeps the marker width plus the grid step as the lead does (R1362); the lead stays 0."""
    env = _env()
    wide = replace(env, refs=(_arrow(env.plan.page, 0),))
    (before,), (after,) = row_specs(env), row_specs(wide)
    assert (before.tail_extra, after.tail_extra, after.lead_extra) == (0, W + env.options.wiring_grid, 0)


def test_a_left_arrow_row_keeps_the_marker_box_and_one_grid_step_before_its_first_column() -> None:
    """R1362: the left walk stands a grid step clear of the first footprint, so the box fits inside the margin."""
    env = replace(_env(), refs=(_arrow(_env().plan.page, -1),))
    (spec,) = row_specs(env)
    assert (spec.lead_extra, spec.tail_extra) == (W + env.options.wiring_grid, 0)


def test_the_lead_reserve_is_the_reserve_and_a_grid_step_only_when_an_arrow_leads() -> None:
    options = OPTIONS
    assert (lead_reserve(0, options), lead_reserve(1, options)) == (0, reserve(1, options) + options.wiring_grid)


def test_a_row_without_an_arrow_is_unchanged() -> None:
    env = _env()
    other = replace(env, refs=(_arrow(env.plan.page + 5, 0),))
    assert place_x(other) == place_x(env)
    assert [_spans(other, place_x(other)[0])] == [_spans(env, place_x(env)[0])]


def test_an_arrow_with_no_marker_box_is_refused_and_no_arrow_needs_none() -> None:
    assert (
        reserve(
            0,
            core_options(),
        )
        == 0
    )
    with pytest.raises(CoreError, match=r"Options\.marker is unset"):
        reserve(
            1,
            core_options(),
        )


def test_a_link_fit_box_sets_the_reserve_and_the_two_end_marker_boxes() -> None:
    """R350: the widest arrow's box is the reserve and the box of an arrow.

    A tag, star or stub keeps `Options.marker` (a stub's own fit is `marker_fit`'s)..
    """

    wide = replace(OPTIONS, link_fit=marker_views(Box(0, -8, 60, 16)))
    assert reserve(1, OPTIONS) == W
    assert reserve(1, wide) == 60
    pin = PinRef("s", "p")
    assert marker_box_at(0, 0, wide, "R0", (pin, "arrow")).w == 60
    assert marker_box_at(0, 0, wide, "R0", (pin, "stub")).w == W
    assert marker_box_at(0, 0, wide, "R0", (pin, "tag")).w == W


def _leg_plant():
    """A fan of three nets whose lanes 0 and 1 end at the cut x 508 and 308; poles 0 and 1 stand legs (ONE-SIDED-PIN)."""

    pins = [PinRef("a", "out"), PinRef("b", "out"), PinRef("c", "out")]
    drivers = tuple(Attach("c", 0, 0, p, i, net=f"n{i}") for i, p in enumerate(pins))
    fan = Fan("f", ("n0", "n1", "n2"), drivers, (), "H", 3, "S")
    trunk = Trunk("f", 1, 100, 40, 500, 3, 0, ((40, 508), (80, 308), (120, 208)))
    refs = [Ref(f"n{i}", RefKind.STUB, (RefEnd(1, "c", pins[i], 0, StandClass.LEG),)) for i in (0, 1)]
    refs.append(Ref("n2", RefKind.STUB, (RefEnd(2, "c", pins[2], 0),)))  # another page: no leg here
    return fan, trunk, pins, refs


def test_the_legs_of_a_fan_are_the_one_sided_pins_that_stand_on_its_page_in_its_row() -> None:

    fan, _, pins, refs = _leg_plant()
    rows = leg_rows(refs, 1)
    assert rows == {pins[0]: 0, pins[1]: 0}
    assert leg_pins(fan, rows, 0) == ((0, pins[0]), (1, pins[1]))
    assert leg_pins(fan, rows, 1) == ()


def _stands(ends: tuple[int, ...]) -> list[int]:
    """The x of every leg's drop of a three-lane fan whose lanes end at `ends`, as the page places them together."""

    fan, _, _, refs = _leg_plant()
    rows = leg_rows(refs, 1)
    trunk = Trunk("f", 1, 100, 40, 500, 3, 0, tuple((40, e) for e in ends))
    placed = leg_lines([trunk], {"f": fan}, rows, OPTIONS, ((), {}, None))
    return [placed["f", 0, pin][1][0] for _, pin in leg_pins(fan, rows, 0)]


def test_each_leg_leaves_its_own_lane_and_stands_below_the_bundle_past_one_cut_x() -> None:

    fan, trunk, _, refs = _leg_plant()
    legs = leg_pins(fan, leg_rows(refs, 1), 0)
    grid = OPTIONS.wiring_grid
    width = MARKER_BOX.h + grid  # a marker turned to R90 is its height wide, and one grid clear of the next
    below = 100 + 3 * grid - grid  # the lowest lane line is lane 2: offset 2 * grid, then one grid down
    first = _must(trunk, 0, legs, OPTIONS)
    second = _must(trunk, 1, legs, OPTIONS)
    assert first[:2] == ((508, 100), (508 + width, 100))
    assert second[:2] == ((308, 100 + grid), (508 + 2 * width, 100 + grid))  # the cut x is the largest lane end, not lane 1's own
    assert first[2] == (508 + width, below + grid)
    assert second[2] == (508 + 2 * width, below + grid)


@pytest.mark.rule("BUNDLE-LEGS")
def test_no_two_legs_of_one_trunk_end_share_a_stand_whatever_the_lane_ends() -> None:
    unit = MARKER_BOX.h + OPTIONS.wiring_grid
    base = 200
    mark = marker_box_at(0, 0, OPTIONS, "R90", (PinRef("c", "p"), str(RefKind.STUB)))
    grid = [base + k * unit + d for k in range(4) for d in (0, 1, unit // 2)]
    for a, b, c in itertools.product(grid, repeat=3):
        xs = _stands((a, b, c))
        assert len(set(xs)) == len(xs), (a, b, c, xs)
        boxes = [Box(x + mark.x, 0, mark.w, mark.h) for x in xs]
        assert not any(overlaps(p, q) for p, q in itertools.combinations(boxes, 2)), (a, b, c, xs)


def test_the_leg_of_a_one_lane_bundle_drops_at_the_arrow_one_marker_width_back_from_the_stepped_out_end() -> None:

    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    grid = OPTIONS.wiring_grid
    legs = ((0, PinRef("a", "out")),)
    assert leg_line(trunk, 0, legs, OPTIONS, ((), (), ARROWED, (), None)) == (
        (468, 100),
        (500 - grid, 100 + 0),
        (500 - grid, 100 + grid),
    )  # the leg starts at the last tap (468), BUNDLE
    pushed = Box(500 - grid - 20, 100 + grid, 60, 60)  # a footprint pushes the arrowed leg past the trunk end: it still starts at the last tap
    line = _must(trunk, 0, legs, OPTIONS, ([pushed], (), ARROWED, (), None))
    assert line[1][0] > 500
    assert line[0] == (500, 100)
    past = 500 + MARKER_BOX.h + grid  # no arrow: the legs start at the trunk end
    assert leg_line(trunk, 0, legs, OPTIONS) == ((500, 100), (past, 100), (past, 100 + grid))


def test_a_leg_standing_at_or_past_its_trunk_end_starts_at_the_trunk_end() -> None:
    """R1861: a leg never starts inside its own trunk's run, so a stand past the end draws no undotted overlap."""

    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    legs = ((0, PinRef("a", "out")),)
    pushed = Box(500 - OPTIONS.wiring_grid - 20, 100 + OPTIONS.wiring_grid, 60, 60)  # a footprint pushes the arrowed leg's stand past the end
    start, stand, _ = _must(trunk, 0, legs, OPTIONS, ([pushed], (), ARROWED, (), None))
    assert stand[0] > trunk.x1
    assert start == (trunk.x1, 100)


def test_a_leg_starts_at_its_lanes_end_so_it_draws_no_run_over_a_lane_that_runs_on() -> None:
    """R1679 point 2: a lane that runs past the leg's drop carries the leg; the leg is only the drop, no second run along the lane."""

    legs = ((1, PinRef("a", "out")),)
    short = _must(Trunk("f", 1, 100, 40, 500, 2, 0, ((40, 500), (40, 500 + OPTIONS.wiring_grid))), 0, legs, OPTIONS)
    drop = short[1][0]
    long = _must(Trunk("f", 1, 100, 40, 500, 2, 0, ((40, 500), (40, drop + 40))), 0, legs, OPTIONS)
    assert long[1:] == short[1:]
    assert short[0][0] < drop
    assert long[0][0] == drop  # the lane runs on past the drop: the leg starts at its x, with no run


def test_a_leg_steps_out_from_its_slot_until_its_marker_box_hits_no_footprint() -> None:

    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    legs = ((0, PinRef("a", "out")),)
    x = 500 - OPTIONS.wiring_grid
    near = Box(x + MARKER_BOX.h // 2 - 2, 100 + OPTIONS.wiring_grid, 20, 60)  # starts two short of the marker box's far edge
    assert _must(trunk, 0, legs, OPTIONS, ([near], (), ARROWED, (), None))[1][0] > x
    wide = Box(470, 100 + OPTIONS.wiring_grid, 200, 60)
    assert _must(trunk, 0, legs, OPTIONS, ([wide], (), ARROWED, (), None))[1][0] - 8 == 670  # out to the footprint's far edge


def test_a_leg_clears_the_legs_already_placed_and_the_page_edge_else_has_no_place() -> None:
    """MARKER-FREE-SIDE (L2, L3): a placed leg's marker box and run are obstacles, the marker box stays inside the page, and no clear x is no leg."""

    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    legs = ((0, PinRef("a", "out")),)
    own = leg_line(trunk, 0, legs, OPTIONS)
    assert own is not None
    x = own[1][0]
    placed = Box(x - 2, 100, MARKER_BOX.h, MARKER_BOX.w)  # another fan's marker box on the leg's own x
    moved = leg_line(trunk, 0, legs, OPTIONS, ([], [placed], {}, (), None))
    assert moved is not None
    assert moved[1][0] != x
    assert leg_line(trunk, 0, legs, OPTIONS, ([], (), {}, (), Size(2000, 400))) == own
    assert leg_line(trunk, 0, legs, OPTIONS, ([], (), {}, (), Size(x - 100, 400))) is None  # the page ends before any clear x
    assert leg_line(trunk, 0, legs, OPTIONS, ([], (), {}, (), Size(x + 1, 400))) is None  # the x is on the page, its marker box is not (A3)


def test_a_leg_stands_past_another_fans_trunk_it_would_end_on() -> None:
    """R1299: a sibling trunk below the lane is an obstacle: the leg steps out past it and always reaches its full length."""

    grid = OPTIONS.wiring_grid
    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    legs = ((0, PinRef("a", "out")),)
    free = _must(trunk, 0, legs, OPTIONS)
    on = Trunk("g", 1, 100 + grid, 0, 900, 1, 0, ((0, 900),))
    far = Trunk("g", 1, 100 + 4 * grid, 0, 900, 1, 0, ((0, 900),))
    beside = Trunk("g", 1, 100 + grid, 0, 100, 1, 0, ((0, 100),))
    assert free[2][1] == 100 + grid
    past = _must(trunk, 0, legs, OPTIONS, ((), (), {}, [on], None))
    assert past[2][1] == free[2][1]
    assert past[1][0] > on.x1
    assert leg_line(trunk, 0, legs, OPTIONS, ((), (), {}, [far, beside], None)) == free
    assert leg_line(trunk, 0, legs, OPTIONS, ((), (), {}, [replace(on, fan="f")], None)) == free


@pytest.mark.rule("MARKER-FREE-SIDE")
@pytest.mark.parametrize("ahead", [0, 1, 3])
def test_a_legs_run_never_lies_along_a_foreign_pin_tip(ahead: int) -> None:
    """ONE-SIDED-PIN (R1816, R1818): a footprint pin tip on the leg's run blocks it (no leg); a collinear placed run too; a crossing is none."""

    grid = OPTIONS.wiring_grid
    page = Size(4000, 400)
    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    legs = ((0, PinRef("a", "out")),)
    free = _must(trunk, 0, legs, OPTIONS, ((), (), {}, (), page))
    lane = free[0][1]
    inside = Box(free[0][0] + 1 + ahead, lane, grid, 2)  # between the trunk end and the stand: on the run
    assert leg_line(trunk, 0, legs, OPTIONS, ([inside], (), {}, (), page)) is None
    past = Box(free[1][0] + 40 + ahead, lane, grid, 2)  # beyond the stand: off the run
    assert leg_line(trunk, 0, legs, OPTIONS, ([past], (), {}, (), page)) == free
    run = Box(inside.x, lane - 1, grid, 1)  # a placed leg run as `_stand` records it, collinear on the lane
    assert leg_line(trunk, 0, legs, OPTIONS, ([], [run], {}, (), page)) is None  # refused at gap -1: it has a true extent
    hung = Box(inside.x, lane - 1, grid, 2)  # a hanging at a pin is a foot like a footprint: same refusal
    assert leg_line(trunk, 0, legs, OPTIONS, ([hung], (), {}, (), page)) is None


@pytest.mark.timeout(20)
def test_a_run_blocked_on_a_page_of_no_edge_ends_the_search_with_no_leg() -> None:
    """ONE-SIDED-PIN: a footprint's pin tip on the run blocks every farther stand, so the search ends: no leg, never a loop."""

    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    legs = ((0, PinRef("a", "out")),)
    assert leg_line(trunk, 0, legs, OPTIONS, ([Box(501, 99, 8, 2)], (), {}, (), None)) is None


def test_legs_of_two_fans_that_would_stand_on_one_x_take_two_xs() -> None:
    """ONE-SIDED-PIN: a leg that meets an earlier leg's span steps out past it, so two markers never coincide."""

    grid = OPTIONS.wiring_grid
    pins = [PinRef("a", "in"), PinRef("b", "in")]
    fans = {f"f{i}": Fan(f"f{i}", (f"n{i}",), (Attach("c", 0, 0, pins[i], 0, net=f"n{i}"),), (), "H", 1, "S") for i in (0, 1)}
    trunks = [Trunk(f"f{i}", 1, 100 + i * grid, 40, 500, 1, 0, ((40, 500),)) for i in (0, 1)]
    rows = {pins[0]: 0, pins[1]: 0}
    lines = leg_lines(trunks, fans, rows, OPTIONS, ((), {}, None))
    assert lines["f0", 0, pins[0]][1][0] != lines["f1", 0, pins[1]][1][0]


def test_a_leg_never_drops_into_another_fans_arrow_box_at_its_trunk_end() -> None:
    """R1381: an arrowed trunk's end holds its arrow's box; another fan's leg run and drop stand clear of it."""

    pin = PinRef("a", "in")
    fans = {"f0": Fan("f0", ("n0",), (Attach("c", 0, 0, pin, 0, net="n0"),), (), "H", 1, "S")}
    trunks = [Trunk("f0", 1, 100, 40, 480, 1, 0, ((40, 480),)), Trunk("f1", 1, 104, 40, 500, 1, 0, ((40, 500),))]
    box = MARKER_BOX
    walls = Box(500 + box.x, 104 + box.y, box.w, box.h)

    def line(arrowed: ArrowMap):
        return leg_lines(trunks, fans, {pin: 0}, OPTIONS, ((), arrowed, Size(2000, 400))).get(("f0", 0, pin))

    free, held = line({}), line({(1, "f1", 0): ((0, (PinRef("b", "q"), "arrow")),)})
    assert free is not None
    assert walls.x <= free[1][0] < walls.x + walls.w
    assert held is None  # it cannot cross the box to the right, and every x before it is taken


@pytest.mark.rule("BUNDLE-LEGS")
def test_a_leg_never_drops_into_the_arrow_standing_at_the_lane_end_of_a_three_lane_trunk() -> None:
    """R1514: the arrow of a bundle stands at its lane's end, past the trunk's x1; a leg stand clears that box, not one at x1."""

    pin = PinRef("a", "in")
    fans = {"f0": Fan("f0", ("n0",), (Attach("c", 0, 0, pin, 0, net="n0"),), (), "H", 1, "S")}
    trunks = [Trunk("f0", 1, 100, 40, 540, 1, 0, ((40, 540),)), Trunk("f1", 1, 104, 40, 500, 3, 0, ((40, 500), (40, 560), (40, 520)))]
    box = MARKER_BOX
    arrow = Box(560 + box.x, 104 + OPTIONS.wiring_grid + box.y, box.w, box.h)  # lane 1: its end 560, one grid below the trunk line
    stub = marker_box_at(0, 0, OPTIONS, "R90", (pin, str(RefKind.STUB)))

    def foot(arrowed: ArrowMap):
        x = leg_lines(trunks, fans, {pin: 0}, OPTIONS, ((), arrowed, Size(2000, 400)))["f0", 0, pin][2]
        return Box(x[0] + stub.x, x[1], stub.w, stub.h)

    held = foot({(1, "f1", 0): ((1, (PinRef("b", "q"), "arrow")),)})
    assert overlaps(foot({}), arrow)  # without the arrow the leg stands on it
    assert not overlaps(held, arrow)
    assert held.x >= arrow.x + arrow.w  # it steps out past the arrow's right edge


def test_two_pins_on_one_pole_stand_two_legs_at_two_x() -> None:
    """R1235: a leg is one a pin, so two pins of a fan on one pole each take a slot and never share a leg x."""

    pins = [PinRef("a", "out"), PinRef("b", "out")]
    fan = Fan("f", ("n0",), tuple(Attach("c", 0, 0, p, 0, net="n0") for p in pins), (), "H", 1, "S")
    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    legs = leg_pins(fan, dict.fromkeys(pins, 0), 0)
    assert legs == ((0, pins[0]), (0, pins[1]))
    first, second = (_must(trunk, i, legs, OPTIONS)[1][0] for i in (0, 1))
    assert second - first == leg_unit(legs, OPTIONS) // 2 > 0


def test_two_legs_of_one_pole_stand_in_the_fans_order_each_past_the_one_before() -> None:
    """R1237: a strict y gives no order between legs of one lane, so the tuple index does: the later leg stands past the earlier."""

    pins = [PinRef("a", "out"), PinRef("b", "out")]
    fan = Fan("f", ("n0",), tuple(Attach("c", 0, 0, p, 0, net="n0") for p in pins), (), "H", 1, "S")
    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    lines = leg_lines([trunk], {"f": fan}, dict.fromkeys(pins, 0), OPTIONS, ([Box(515, 110, 45, 60)], {}, None))
    assert lines["f", 0, pins[0]][1][0] < lines["f", 0, pins[1]][1][0]


def test_a_pin_with_no_clear_place_stands_no_leg_and_one_with_a_place_keeps_it() -> None:
    """MARKER-FREE-SIDE (L3): leg_lines omits a pin whose leg has no x inside the page; the other pin of the fan keeps its leg."""

    pins = [PinRef("a", "out"), PinRef("b", "out")]
    fan = Fan("f", ("n0",), tuple(Attach("c", 0, 0, p, 0, net="n0") for p in pins), (), "H", 1, "S")
    trunk = Trunk("f", 1, 100, 40, 500, 1, 0, ((40, 500),))
    rows = dict.fromkeys(pins, 0)
    whole = leg_lines([trunk], {"f": fan}, rows, OPTIONS, ([], {}, Size(2000, 400)))
    assert set(whole) == {("f", 0, p) for p in pins}
    edge = whole["f", 0, pins[0]][1][0] + MARKER_BOX.h  # the first leg fits, the second does not
    cut = leg_lines([trunk], {"f": fan}, rows, OPTIONS, ([], {}, Size(edge + 1, 400)))
    assert ("f", 0, pins[0]) in cut
    assert ("f", 0, pins[1]) not in cut


def test_a_leg_never_stands_on_a_drop_x_of_its_own_trunk() -> None:
    """MARKER-FREE-SIDE: a lane end x of the trunk is refused as a leg x, and so is one under its marker box."""

    fan, trunk, _, refs = _leg_plant()
    legs = leg_pins(fan, leg_rows(refs, 1), 0)
    free = _must(trunk, 1, legs, OPTIONS)[1][0]
    assert _must(replace(trunk, lane_ends=((40, 508), (80, 308), (120, free))), 1, legs, OPTIONS)[1][0] > free
    assert _must(replace(trunk, lane_ends=((40, 508), (80, 308), (120, free - 1))), 1, legs, OPTIONS)[1][0] > free


def test_a_lower_lanes_run_is_no_obstacle_to_the_leg_of_the_lane_above() -> None:
    """MARKER-FREE-SIDE (R887): the upper pole's leg drops across the run of the lower pole's leg and keeps its own slot."""

    fan, trunk, _, refs = _leg_plant()
    trunk = replace(trunk, lane_ends=((40, 308), (80, 300), (120, 208)))
    legs = leg_pins(fan, leg_rows(refs, 1), 0)
    lines = leg_lines([trunk], {"f": fan}, {p: 0 for _, p in legs}, OPTIONS, ((), {}, None))
    assert [lines["f", 0, p][1][0] for _, p in legs] == [_must(trunk, i, legs, OPTIONS)[1][0] for i in (0, 1)]
    assert lines["f", 0, legs[0][1]][1][0] < lines["f", 0, legs[1][1]][1][0]  # across the lower run, which starts left of it


def test_no_leg_foot_ends_on_another_fans_leg_run() -> None:
    """R1299: the foot of a leg one grid above another fan's lane never lands on that fan's leg run, which would end it on a wire."""

    grid = OPTIONS.wiring_grid
    pins = [PinRef("a", "in"), PinRef("b", "in")]
    fans = {f"f{i}": Fan(f"f{i}", (f"n{i}",), (Attach("c", 0, 0, pins[i], 0, net=f"n{i}"),), (), "H", 1, "S") for i in (0, 1)}
    trunks = [Trunk("f0", 1, 100, 40, 500, 1, 0, ((40, 500),)), Trunk("f1", 1, 100 + grid, 40, 700, 1, 0, ((40, 700),))]
    lines = leg_lines(trunks, fans, {pins[0]: 0, pins[1]: 0}, OPTIONS, ((), {}, None))
    (a_cut, a_y), (a_x, _), (_, a_foot) = lines["f0", 0, pins[0]]
    (b_cut, b_y), (b_x, _), (_, b_foot) = lines["f1", 0, pins[1]]
    assert not (b_cut <= a_x <= b_x and a_foot == b_y)
    assert not (a_cut <= b_x <= a_x and b_foot == a_y)


def test_the_row_estimate_and_the_placed_sum_read_the_one_leg_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """R1627: `row_legs` (the estimate) and `column_legs` (the sum `legs_x` adds) take their x from `leg_unit`, the unit `leg_line` steps by."""

    pin = PinRef("a", "out")
    fan = Fan("f", ("n0",), (Attach("c", 0, 0, pin, 0, net="n0"),), (), "H", 1, "S")
    plan = _plan(1)
    monkeypatch.setattr(ar, "leg_rows", lambda *_: {pin: 0})
    monkeypatch.setattr(ar, "arrow_ends", lambda *_: (0, 1))
    monkeypatch.setattr(ar, "leg_unit", lambda *_: 7777)
    assert ar.row_legs((), plan, [fan], 0, OPTIONS) == 7777 + OPTIONS.wiring_grid
    assert dict(ar.column_legs((), plan, [fan], (0, "c"), OPTIONS).legs) == {"f": 7777}


def test_a_row_reserves_the_y_of_its_tallest_stub_box_at_the_trunk_end() -> None:
    """R1634: `stub_room` is the box height `stub_views` gives the stub that stands at the row's trunk end, 0 for a row with none."""

    _, _, pins, refs = _leg_plant()
    fars = [PinRef("x", "1"), PinRef("y", "1")]
    ends = [RefEnd(1, "c", p, 0, StandClass.LEG, far=(f,)) for p, f in zip(pins, fars, strict=False)]
    refs = [Ref(f"n{i}", RefKind.STUB, (e,)) for i, e in enumerate(ends)]
    table = {(2, 1): {"R0": Box(0, -8, 71, 111)}, (2, 2): {"R0": Box(0, -8, 71, 222)}}
    lines = {(pins[0], fars[0]): (2,), (pins[1], fars[1]): (2, 2)}
    options = replace(OPTIONS, stub_lines=lines, stub_table=table)
    plan = _plan(2)
    assert ar.stub_room(refs, plan, [], 0, options) == 222
    assert ar.stub_room(refs, plan, [], 1, options) == 0


def test_two_plans_that_alternate_a_leg_reach_the_union_after_a_round_each_and_stay() -> None:
    """R1673: a column that stood a leg in any plan keeps it, so plans A, B, A, B end at the union within N+1 rounds."""

    a: dict[str | tuple[str, str], ar.RowReserve] = {("b", "c1"): ar.RowReserve(5, legs=(("f", 20),), tail=4)}
    b: dict[str | tuple[str, str], ar.RowReserve] = {
        ("b", "c1"): ar.RowReserve(0, legs=(("f", 10),), tail=8),
        ("b", "c2"): ar.RowReserve(legs=(("f", 20),), tail=4),
    }
    held: dict[str | tuple[str, str], ar.RowReserve] = {}
    seen = []
    for plan in (a, b, a, b, a, b):
        held = ar.keep_legs(held, plan)
        seen.append(held)
    legs = [{k: (r.legs, r.tail) for k, r in held.items()} for held in seen]
    assert legs[1] == legs[2] == legs[5] == {("b", "c1"): ((("f", 20),), 8), ("b", "c2"): ((("f", 20),), 4)}
    assert [seen[0]["b", "c1"].x, seen[1]["b", "c1"].x] == [5, 0]  # only the legs are kept; x follows the plan now


def test_a_row_reserves_the_arrow_room_under_its_lane_and_the_cuts_row_height_reads_it() -> None:
    """R1646: `arrow_room` is the arrow box's half height plus one grid for a keyed arrow end of the row, else 0; `RowReserve.y` takes it."""

    legs = (Attach(None, 0, 0, PinRef("a", "p"), 0, net="n"), Attach(None, 0, 0, PinRef("b", "p"), 1, net="n"))
    fan = Fan("f:n1", ("n", "m"), (), legs, None, 2, "below")
    ref = Ref("f:n1", RefKind.ARROW, (RefEnd(1, None, PinRef("a", "p"), 0), RefEnd(1, None, PinRef("b", "p"), 1)))
    options = replace(OPTIONS, arrow_sides=("E", "W"))
    ((pin, kind),) = (c.key for c in ar.cut_ends((ref,), _plan(2), (fan,), 0) if c.key[0] is not None)
    assert pin is not None
    want = arrow_box(options, "E", 0, 0, (pin, kind)).h // 2 + options.wiring_grid
    assert want > options.wiring_grid
    assert ar.arrow_room((ref,), _plan(2), (fan,), 0, options) == want
    assert ar.arrow_room((), _plan(2), (fan,), 0, options) == 0


def test_the_held_room_of_a_trunk_holds_the_arrow_room_of_its_row() -> None:
    """R1646, R1719: `held_room`, read by `Trunk.room` and `place_span._band`, takes the arrow room of the row, so a recut sees it."""

    env = _env()
    pin = PinRef("L", "n0")
    ref = Ref("f:n1", RefKind.ARROW, (RefEnd(env.plan.page, None, pin, 0), RefEnd(env.plan.page, None, pin, 1)))
    env = replace(env, refs=(ref,), options=replace(env.options, arrow_sides=("E", "W")))
    fan = next(f for f in env.flow.fans if f.id == "f:n1")
    grid = env.options.wiring_grid
    room = arrow_room(env.refs, env.plan, [fan], 0, env.options)
    assert room > 0
    assert held_room(fan, env, 0) == trunk_room(fan.lanes, grid, arrow_hang(fan.lanes, grid, room))
    assert held_room(fan, replace(env, refs=()), 0)[1] == fan.lanes * grid


def test_leg_depth_is_the_deeper_of_the_tallest_marker_and_the_arrow_hang_never_their_sum() -> None:
    """R1719: the arrow and the leg markers hang in the same space under the band, so `leg_depth` takes the max."""

    fan, _ = _bundle("c1")
    rows = dict.fromkeys((a.pin for a in fan.legs), 0)
    grid = OPTIONS.wiring_grid
    marker = leg_depth(fan, rows, 0, OPTIONS)
    assert marker > 0
    shallow, deep = grid + marker // 2, grid + 2 * marker  # arrow hang past the 2-lane band: marker // 2, then 2 * marker
    assert leg_depth(fan, rows, 0, OPTIONS, shallow) == marker
    assert leg_depth(fan, rows, 0, OPTIONS, deep) == 2 * marker
    assert leg_depth(fan, {}, 0, OPTIONS, deep) == 2 * marker


def test_a_leg_stands_clear_of_a_hanging_at_a_placed_pin_as_of_a_footprint() -> None:
    """layout-0547: a symbol's hangings are part of its footprint for the legs, so a leg never drops into a planned marker's box."""

    pin = PinRef("a", "in")
    fans = {"f0": Fan("f0", ("n0",), (Attach("c", 0, 0, pin, 0, net="n0"),), (), "H", 1, "S")}
    trunks = [Trunk("f0", 1, 100, 40, 480, 1, 0, ((40, 480),))]
    free = leg_lines(trunks, fans, {pin: 0}, OPTIONS, ((), {}, None))["f0", 0, pin]
    hung = {"card": (Box(free[1][0] - 6, 100 + OPTIONS.wiring_grid, 12, 40),)}  # a planned tag at a card pin, hanging over the free leg's drop
    held = leg_lines(trunks, fans, {pin: 0}, OPTIONS, (leg_feet((), hung), {}, None))["f0", 0, pin]
    assert held[1][0] >= free[1][0] + 6
    assert leg_feet((), hung) == hung["card"]


def test_a_tag_stood_at_a_pin_of_the_row_is_held_clear_under_its_trunk_and_other_rows_are_not() -> None:
    """CUT-CND, R1802: `arrow_room` is the tag box and one grid for a tag end with a pin on the row, else 0; `held_room` deepens the legs by it."""

    env = _env()
    pin = PinRef("L", "n0")
    tag = Ref("f:n1", RefKind.TAG, (RefEnd(env.plan.page, "c", pin, 0), RefEnd(env.plan.page + 1, "c", pin, 0)))
    env = replace(env, refs=(tag,))
    fan = next(f for f in env.flow.fans if f.id == "f:n1")
    grid = env.options.wiring_grid
    want = marker_box_at(0, 0, env.options, env.options.marker_facing["S"], (pin, str(RefKind.TAG))).h + grid
    assert arrow_room(env.refs, env.plan, [fan], 0, env.options) == want
    assert arrow_room(env.refs, env.plan, [fan], 1, env.options) == 0
    assert held_room(fan, env, 0)[1] == fan.lanes * grid + arrow_hang(fan.lanes, grid, want)
