"""`stages.line_draw`: the fan-out and one line's pieces, on hand-built ends.

The grid is 8. A leaving line runs 6 grids, 48, straight out; a fan-out's split stands 4, 32.
"""

from dataclasses import replace

from samples import hid

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.stages.harness_route import Grid, _unspiked
from fransys_layout.stages.line_draw import EndOnPage, PinAt, Stub, fan_out, line_pieces
from fransys_layout.stages.line_side import faced
from fransys_layout.stages.space import End, Obstacle

_GRID = Grid(region=Box(x=0, y=0, width=1000, height=1000), obstacles=(), turn_penalty=8)
_C = [hid("conductor", n) for n in (1, 2, 3)]


def _pins(facing: Facing, y: int = 0) -> tuple[PinAt, ...]:
    return tuple(
        PinAt(conductor=_C[n], end=End(at=Point(x=16 * n, y=y), facing=facing)) for n in (2, 0, 1)
    )


def _plug(branch: int, x: int, y: int, *, interface: bool = False, leaving: bool = False):
    """A plug end whose box top edge middle is (x, y): it faces N."""
    box = Box(x=x - 16, y=y, width=32, height=16)
    return EndOnPage(branch=branch, interface=interface, leaving=leaving, box=box)


def test_a_fan_out_facing_s_splits_four_grids_below_its_row_with_legs_in_x_order() -> None:
    """Pins at x 0, 16, 32 give the split at (16, 32); each leg is split, knee, pin.

    UNDO: `FAN_GRIDS` is 3, and the split stands at y 24.
    """
    split, legs = fan_out(_pins(Facing.S))
    assert split == Point(x=16, y=32)
    assert [leg.conductor for leg in legs] == _C
    for n, leg in enumerate(legs):
        assert leg.points == (split, Point(x=16 * n, y=8), Point(x=16 * n, y=0))


def test_a_fan_out_facing_n_splits_above_its_row() -> None:
    """The same pins facing N at y 64 give the split at (16, 32), the knee a grid above.

    UNDO: `fan_out` takes `max` of the rows for N too, or a `+` step, and the split flips.
    """
    split, legs = fan_out(_pins(Facing.N, y=64))
    assert split == Point(x=16, y=32)
    assert legs[0].points == (split, Point(x=0, y=56), Point(x=0, y=64))


def test_two_plug_ends_are_one_path_keyed_by_the_interface_end_with_no_stub_or_fan() -> None:
    """The interface end is the root, though second, so its branch keys the path.

    UNDO: `line_pieces` roots at the first end, and the key is 1.
    """
    ends = (_plug(1, 0, 296), _plug(2, 200, 96, interface=True))
    pieces = line_pieces(ends, None, _GRID)
    assert [branch for branch, _ in pieces.paths] == [2]
    assert (pieces.stubs, pieces.fans) == ((), ())
    path = pieces.paths[0][1]
    assert (path[0], path[-1]) == (Point(x=200, y=96), Point(x=0, y=296))


def test_a_lone_end_with_the_other_absent_runs_48_out_to_one_stub() -> None:
    """End 1 faces N at (200, 200); the stub stands at the tip 48 up, and the path runs on
    one grid to its box's edge (layout-0158).

    UNDO: `LEAVE_GRIDS` is 5, and the tip stands at y 160.
    """
    pieces = line_pieces((_plug(1, 200, 200),), 2, _GRID)
    assert pieces.paths == ((1, (Point(x=200, y=200), Point(x=200, y=144))),)
    assert pieces.stubs == (Stub(near=1, far=2, end=End(at=Point(x=200, y=152), facing=Facing.N)),)
    assert pieces.fans == ()


def test_two_ends_and_an_absent_third_leave_by_the_roots_end_keyed_by_the_absent_branch() -> None:
    """Root 1 stands at (200, 200); the leaving leg is keyed 3 and ends on its box (200, 144).

    UNDO: `line_pieces` does not append the absent end as a goal, and the key 3 is gone.
    """
    ends = (_plug(1, 200, 200, interface=True), _plug(2, 400, 200))
    pieces = line_pieces(ends, 3, _GRID)
    paths = dict(pieces.paths)
    assert sorted(paths) == [1, 2, 3]
    assert paths[3][-1] == Point(x=200, y=144)
    assert pieces.stubs == (Stub(near=1, far=3, end=End(at=Point(x=200, y=152), facing=Facing.N)),)


def test_a_leaving_end_draws_its_own_stub_and_the_line_goes_on_among_the_rest() -> None:
    """End 2 leaves; it draws 48 out with a stub, and 1 and 3 join in one path, 1's.

    UNDO: `line_pieces` skips the `one.leaving` branch, and end 2 has no stub.
    """
    ends = (_plug(1, 0, 200, interface=True), _plug(2, 200, 200, leaving=True), _plug(3, 400, 200))
    pieces = line_pieces(ends, None, _GRID)
    paths = dict(pieces.paths)
    assert paths[2] == (Point(x=200, y=200), Point(x=200, y=144))
    assert [(s.near, s.end.at) for s in pieces.stubs] == [(2, Point(x=200, y=152))]
    assert sorted(paths) == [1, 2]
    assert paths[1][-1] == Point(x=400, y=200)


def test_a_line_between_two_top_level_units_leaves_at_both_ends() -> None:
    """Condition 2: both ends leaving and nothing absent give two 48 paths and two stubs.

    UNDO: `line_pieces` treats a lone joint end as joined, and the second stub is missing.
    """
    ends = (_plug(1, 0, 200, leaving=True), _plug(2, 200, 200, leaving=True))
    pieces = line_pieces(ends, None, _GRID)
    assert [branch for branch, _ in pieces.paths] == [1, 2]
    assert [(s.near, s.far) for s in pieces.stubs] == [(1, 2), (2, 1)]
    assert [s.end.at for s in pieces.stubs] == [Point(x=0, y=152), Point(x=200, y=152)]


def test_a_fan_out_end_returns_its_fan_with_branch_and_legs() -> None:
    """An end in pins gives a Fan of its branch, split and three legs.

    UNDO: `line_pieces` returns no fans.
    """
    pins = EndOnPage(branch=2, pins=_pins(Facing.S))
    pieces = line_pieces((_plug(1, 16, 400, interface=True), pins), None, _GRID)
    (fan,) = pieces.fans
    assert (fan.branch, fan.at) == (2, Point(x=16, y=32))
    assert [leg.conductor for leg in fan.legs] == _C


def test_a_fan_out_split_keeps_its_bounds_so_its_stub_stays_on_the_page() -> None:
    """Defect 1 (layout-0158): pins at x 0 to 32 with bounds from 40 split at x 40, not 16."""
    split, legs = fan_out(_pins(Facing.N, y=64), (40, 960))
    assert split == Point(x=40, y=32)
    assert legs[0].points[-1] == Point(x=0, y=64)


def test_a_path_that_turns_back_on_itself_stops_on_its_end() -> None:
    """layout-0158: a search entering a joint from its facing side overshoots and comes back.

    `_unspiked` drops the run back, at the path's end and at its start, and keeps a clean one.
    """
    at = Point
    assert _unspiked((at(x=400, y=296), at(x=112, y=296), at(x=112, y=304), at(x=112, y=296))) == (
        at(x=400, y=296),
        at(x=112, y=296),
    )
    assert _unspiked((at(x=344, y=504), at(x=344, y=512), at(x=344, y=464), at(x=32, y=464))) == (
        at(x=344, y=504),
        at(x=344, y=464),
        at(x=32, y=464),
    )
    clean = (at(x=0, y=0), at(x=0, y=16), at(x=80, y=16))
    assert _unspiked(clean) == clean


def test_two_pin_rows_get_two_fans_and_the_line_runs_on_to_the_second() -> None:
    """Defect 4: pins in a row at y 200 and a row at y 0, all facing S, fan apart, each split
    32 out of its row; the line ends at the first and runs on to the second.

    UNDO: one fan for both rows (`_pin_rows` returns one row).
    """
    low = tuple(
        PinAt(conductor=_C[n], end=End(at=Point(x=16 * n, y=200), facing=Facing.S), row=(200, 216))
        for n in (0, 1)
    )
    high = (PinAt(conductor=_C[2], end=End(at=Point(x=64, y=0), facing=Facing.S), row=(-16, 0)),)
    pins = EndOnPage(branch=2, pins=(*low, *high))
    pieces = line_pieces((_plug(1, 400, 400, interface=True), pins), None, _GRID)
    (fan,) = pieces.fans
    starts = {leg.points[0] for leg in fan.legs}
    assert starts == {Point(x=8, y=232), Point(x=64, y=32)}
    ((_, path),) = pieces.paths
    assert set(path) >= starts


def _coil_end(branch: int, x: int) -> EndOnPage:
    """A coil's two pins, one facing N and one S, its keep-out 40 wide around x, 80 high."""
    return EndOnPage(
        branch=branch,
        pins=(
            PinAt(
                _C[0],
                End(at=Point(x=x, y=100), facing=Facing.N),
                row=(100, 180),
                across=(x - 20, x + 20),
            ),
            PinAt(
                _C[1],
                End(at=Point(x=x, y=180), facing=Facing.S),
                row=(100, 180),
                across=(x - 20, x + 20),
            ),
        ),
    )


def test_pins_facing_apart_fan_once_to_the_side_of_the_other_end() -> None:
    """Layout-0172: a coil's N and S pins fan to the east when the other end lies east, to the
    west when it lies west; one split level with the coil, past its keep-out, no row run.

    UNDO: `faced` returns its pins as given, and there are two fans' rows and a run round the coil.
    """
    east = line_pieces((_coil_end(1, 100), _coil_end(2, 400)), None, _GRID)
    west = line_pieces((_coil_end(1, 400), _coil_end(2, 100)), None, _GRID)
    (one, two) = east.fans
    assert (one.at, one.facing, one.rows) == (Point(x=152, y=136), Facing.E, ())
    assert (two.at, two.facing, two.rows) == (Point(x=344, y=136), Facing.W, ())
    assert {fan.at: fan.facing for fan in west.fans} == {
        Point(x=344, y=136): Facing.W,
        Point(x=152, y=136): Facing.E,
    }
    assert [len(points) for _, points in east.paths] == [2]


def test_two_coinciding_splits_leave_the_line_fanned_as_before() -> None:
    """Layout-0172: coils whose side splits meet at one point leave no bundle: the pins fan N and S
    as before (the probe's one-point polyline crashed `longest_run`).

    UNDO: `_all_drawn` keeps the side fans, and the line is one point.
    """
    pieces = line_pieces((_coil_end(1, 100), _coil_end(2, 204)), None, _GRID)
    assert {fan.facing for fan in pieces.fans} == {Facing.N}
    ((_, path),) = pieces.paths
    assert len(path) > 1


def test_pins_spread_along_their_line_keep_their_rows() -> None:
    """Layout-0172: a motor's pins along its top and bottom would be reached through its body by a
    side fan, so they fan N and S as before (the website example's cable).

    UNDO: `faced` drops `_one_line`, and the fan faces east.
    """
    spread = (
        PinAt(_C[0], End(at=Point(x=100, y=100), facing=Facing.N), (100, 180), (80, 120)),
        PinAt(_C[1], End(at=Point(x=116, y=180), facing=Facing.S), (100, 180), (80, 120)),
    )
    assert faced(spread, Point(x=400, y=140)) == spread
    assert faced(_coil_end(1, 100).pins, Point(x=400, y=140)) != _coil_end(1, 100).pins


def test_a_line_with_an_end_off_the_page_keeps_its_pins_rows() -> None:
    """Layout-0172: with the far end absent the line aims nowhere, and N and S pins fan apart.

    UNDO: `aim` ignores `absent`, and the fan faces east.
    """
    pieces = line_pieces((_coil_end(1, 100), _coil_end(2, 400)), 3, _GRID)
    assert {fan.facing for fan in pieces.fans} == {Facing.N}
    assert all(fan.rows for fan in pieces.fans)


_TRUNK = (Facing.S, (40, 16))


def test_a_line_with_its_root_off_the_page_leaves_its_bar_south_by_the_middle() -> None:
    """layout-0167: root 3 is elsewhere; the trunk (keyed 3) runs from the bar's middle.

    UNDO: `line_pieces` ignores `trunk`, or `_branches` keeps one polyline: branch 2 has no path.
    """
    ends = (_plug(1, 200, 200, interface=True), _plug(2, 400, 200))
    pieces = line_pieces(ends, 3, _GRID, trunk=_TRUNK)
    paths = dict(pieces.paths)
    assert sorted(paths) == [1, 2, 3]
    assert paths[3] == (Point(x=296, y=192), Point(x=296, y=248))
    assert paths[1][-1] == paths[2][-1] == Point(x=296, y=192)  # each end keeps its own branch
    assert pieces.stubs == (Stub(near=1, far=3, end=End(at=Point(x=296, y=240), facing=Facing.S)),)


def test_a_trunk_never_runs_through_a_box_the_search_must_avoid() -> None:
    """A box covers the point under the bar's middle; the trunk leaves elsewhere, clear of it.

    UNDO: `_free` skips the obstacle test, and the trunk runs through the box.
    """
    ends = (_plug(1, 200, 200, interface=True), _plug(2, 400, 200))
    block = Obstacle(box=Box(x=280, y=200, width=32, height=100), lanes=())
    pieces = line_pieces(ends, 3, replace(_GRID, obstacles=(block,)), trunk=_TRUNK)
    run = dict(pieces.paths)[3]
    assert run[0].x not in range(272, 321)
    assert Point(x=296, y=248) not in run


def test_no_free_point_leaves_the_stub_at_the_junction_as_before() -> None:
    """The whole page blocked, the root's end carries the stub facing N.

    UNDO: `_trunk` returns a trunk with no free point, or fails.
    """
    ends = (_plug(1, 200, 200, interface=True), _plug(2, 400, 200))
    wall = Obstacle(box=Box(x=0, y=0, width=1000, height=1000), lanes=())
    pieces = line_pieces(ends, 3, replace(_GRID, obstacles=(wall,)), trunk=_TRUNK)
    assert pieces == line_pieces(ends, 3, replace(_GRID, obstacles=(wall,)))


def test_a_side_fans_core_leaves_its_pin_along_the_pin_then_turns_at_the_keep_outs_edge() -> None:
    """Layout-0172 round 3: a re-faced pin's leg runs a grid out along its own pin, turns there
    and runs to the keep-out's edge; the leg never runs on the pin's row, the symbol's outline.

    UNDO: `_knees` returns the keep-out edge on the pin's row alone: the turn stands at y 100.
    """
    (fan, _) = line_pieces((_coil_end(1, 100), _coil_end(2, 400)), None, _GRID).fans
    split = fan.at
    assert [leg.points for leg in fan.legs] == [
        (split, Point(x=120, y=92), Point(x=100, y=92), Point(x=100, y=100)),
        (split, Point(x=120, y=188), Point(x=100, y=188), Point(x=100, y=180)),
    ]


def test_a_fan_split_stands_nearer_its_pins_when_it_would_stand_by_a_foreign_keepout() -> None:
    """Layout-0172 round 3: a box that holds none of the pins keeps the split `FAN_CLEAR` away.

    UNDO: `_foreign` returns no boxes, and the split stands at y 32 on the box.
    """
    foreign = Box(x=0, y=40, width=48, height=32)
    split, legs = fan_out(_pins(Facing.S), None, (foreign,))
    assert split.y <= foreign.y - 16
    assert split == Point(x=16, y=24)
    assert all(leg.points[0] == split for leg in legs)
    own = Box(x=-8, y=-8, width=64, height=48)
    assert fan_out(_pins(Facing.S), None, (own,))[0] == Point(x=16, y=32)


def test_a_fan_split_leaves_the_grid_where_its_bundle_arrives_clear_of_a_side_fans_symbol() -> None:
    """Layout-0172 round 4: the split clear of a box is not enough; the grid past it must be.

    The box's clearance starts at y 32: a split there stands clear, but the bundle line arrives
    at y 40, inside it, over that symbol's cores.

    UNDO: `_split` ignores `apart`, and the split stands at y 32.
    """
    foreign = Box(x=0, y=48, width=48, height=32)
    assert fan_out(_pins(Facing.S), None, (foreign,))[0] == Point(x=16, y=32)
    assert fan_out(_pins(Facing.S), None, (), (foreign,))[0] == Point(x=16, y=24)


def test_a_motors_pins_facing_apart_in_two_rows_fan_each_row_its_own_way() -> None:
    """Mixed-facing rows: pins at y 400 facing S and two at y 200 facing N, no side to aim at.

    The south pair splits 32 below its row, the north pair 32 above its own; the line runs on
    from the first split to the second.

    UNDO: `_meet` ignores facing, and one row of five pins fans south.
    """
    low = tuple(
        PinAt(conductor=_C[n], end=End(at=Point(x=16 * n, y=400), facing=Facing.S), row=(200, 416))
        for n in (0, 1)
    )
    high = tuple(
        PinAt(conductor=_C[2], end=End(at=Point(x=x, y=200), facing=Facing.N), row=(200, 416))
        for x in (64, 80)
    )
    pins = EndOnPage(branch=2, pins=(*low, *high))
    pieces = line_pieces((_plug(1, 700, 700, interface=True), pins), None, _GRID)
    (fan,) = pieces.fans
    assert (fan.at, fan.facing) == (Point(x=8, y=432), Facing.S)
    assert fan.rows == (End(at=Point(x=72, y=168), facing=Facing.N),)
    ((_, path),) = pieces.paths
    assert set(path) >= {fan.at, fan.rows[0].at}
