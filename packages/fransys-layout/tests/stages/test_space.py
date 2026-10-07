"""`stages.space`: `Space`, `Space.holds`, `lane` and D2's three edge predicates (layout-0083).

Every value is made by hand: one box, `_BOX`, at x 16..40, y 16..32 on the grid of 8, and
cells, lanes and runs beside it. Each test states its own UNDO, the one-line change to
`space.py` that must make it fail.
"""

import pytest
from samples import hid

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.stages import space
from fransys_layout.stages.space import (
    End,
    Lane,
    Obstacle,
    Run,
    Shape,
    Space,
    covers,
    crosses,
    crosses_unless_leaving,
    lane,
    obstacle_index,
    run_admitted,
    step_admitted,
)

_BOX = Box(x=16, y=16, width=24, height=16)
type _Cell = tuple[int, int]


def _admitted(
    first: _Cell,
    second: _Cell,
    obstacles: tuple[Obstacle, ...],
    ends: frozenset[_Cell] = frozenset(),
) -> bool:
    """P1 for a step, asserting that the step read in the other direction agrees."""
    index = obstacle_index(obstacles)
    forward = step_admitted(first, second, index, ends)
    assert step_admitted(second, first, index, ends) is forward
    return forward


def _in(extent: Box) -> Lane:
    """A lane with this extent: the router reads only the extent, so the end is a placeholder."""
    return Lane(end=End(at=Point(x=extent.x, y=extent.y), facing=Facing.N), extent=extent)


def _bare(box: Box = _BOX) -> tuple[Obstacle, ...]:
    """One obstacle with no lane."""
    return (Obstacle(box=box, lanes=()),)


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ((24, 20), (24, 28), False),
        ((8, 20), (8, 28), True),
        ((20, 24), (28, 24), False),
        ((20, 40), (28, 40), True),
    ],
)
def test_a_step_through_the_interior_is_refused_and_its_clear_twin_admitted(
    first: _Cell, second: _Cell, *, expected: bool
) -> None:
    """A step inside the box is refused; the same step clear of it is admitted.

    # UNDO: negate the `not` of the x-band test in `_touches`' vertical branch
    """
    assert _admitted(first, second, _bare()) is expected


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ((16, 20), (16, 28), False),
        ((8, 20), (8, 28), True),
        ((40, 20), (40, 28), False),
        ((48, 20), (48, 28), True),
        ((20, 16), (28, 16), False),
        ((20, 8), (28, 8), True),
        ((20, 32), (28, 32), False),
        ((20, 40), (28, 40), True),
    ],
)
def test_a_step_flush_along_an_edge_is_refused_and_one_unit_off_admitted(
    first: _Cell, second: _Cell, *, expected: bool
) -> None:
    """A step along any of the four edges is refused; one grid unit off the edge it is admitted.

    # UNDO: in `_touches`, `box.x <= first[0]` becomes `box.x < first[0]`
    """
    assert _admitted(first, second, _bare()) is expected


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ((16, 8), (16, 16), False),
        ((16, 0), (16, 8), True),
        ((8, 16), (16, 16), False),
        ((0, 16), (8, 16), True),
        ((40, 32), (40, 40), False),
        ((40, 40), (40, 48), True),
        ((40, 32), (48, 32), False),
        ((48, 32), (56, 32), True),
    ],
)
def test_a_step_ending_on_a_corner_is_refused_and_one_short_of_it_admitted(
    first: _Cell, second: _Cell, *, expected: bool
) -> None:
    """A step that only reaches a corner is refused; the step one unit short of it is admitted.

    # UNDO: in `_meets`, `low <= other` becomes `low < other`
    """
    assert _admitted(first, second, _bare()) is expected


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ((8, 16), (8, 24), True),
        ((48, 16), (48, 24), True),
        ((16, 8), (24, 8), True),
        ((16, 40), (24, 40), True),
        ((8, 0), (8, 48), True),
        ((16, 0), (16, 48), False),
    ],
)
def test_a_step_clear_of_the_box_by_one_grid_unit_is_admitted(
    first: _Cell, second: _Cell, *, expected: bool
) -> None:
    """One unit clear on each side is admitted, also for a long step; along the edge it is not.

    # UNDO: in `_touches`, `box.x <= first[0]` becomes `box.x - 8 <= first[0]`
    """
    assert _admitted(first, second, _bare()) is expected


@pytest.mark.parametrize(
    ("ends", "expected"),
    [
        (frozenset({(16, 16)}), True),
        (frozenset(), False),
        (frozenset({(16, 8)}), False),
        (frozenset({(28, 16)}), False),
    ],
)
def test_a_step_touching_the_box_only_at_its_own_end_cell_is_admitted(
    ends: frozenset[_Cell], *, expected: bool
) -> None:
    """The step (16, 8) to (16, 16) meets a corner at its end; that end is open only in `ends`.

    # UNDO: `step_admitted` passes `frozenset()` to `_touches` instead of `ends`
    """
    assert _admitted((16, 8), (16, 16), _bare(), ends) is expected


def test_an_end_cell_does_not_excuse_a_step_that_goes_into_the_box() -> None:
    """An end cell on the far side is left out of the touch test; the interior still refuses.

    # UNDO: in `_meets`, `high > one` (an open low end) becomes `False`
    """
    ends = frozenset({(16, 24)})
    assert _admitted((16, 8), (16, 24), _bare(), ends) is False
    assert _admitted((16, 8), (16, 24), _bare(), frozenset({(16, 8)})) is False
    assert _admitted((16, 0), (16, 8), _bare(), ends) is True


@pytest.mark.parametrize(
    ("ends", "first", "second", "expected"),
    [
        (frozenset({(16, 8)}), (16, 8), (16, 16), False),
        (frozenset({(16, 16)}), (16, 8), (16, 16), True),
        (frozenset({(8, 16)}), (8, 16), (16, 16), False),
        (frozenset({(16, 16)}), (8, 16), (16, 16), True),
    ],
)
def test_a_step_read_in_either_direction_gives_the_same_answer(
    ends: frozenset[_Cell], first: _Cell, second: _Cell, *, expected: bool
) -> None:
    """Which end is open follows the cell, not the argument order (`_admitted` swaps and compares).

    # UNDO: in `_meets`, the `if one > other` swap does nothing (its body becomes `pass`)
    """
    assert _admitted(first, second, _bare(), ends) is expected


@pytest.mark.parametrize(
    ("lane_box", "first", "second"),
    [
        (Box(x=28, y=8, width=0, height=16), (28, 24), (28, 16)),
        (Box(x=28, y=8, width=0, height=16), (28, 16), (28, 8)),
        (Box(x=24, y=28, width=24, height=0), (24, 28), (32, 28)),
        (Box(x=24, y=28, width=24, height=0), (40, 28), (48, 28)),
    ],
)
def test_a_step_inside_the_obstacles_own_lane_is_admitted_and_bare_it_is_refused(
    lane_box: Box, first: _Cell, second: _Cell
) -> None:
    """A vertical and a horizontal lane exempt the steps in them; bare, the same step is refused.

    # UNDO: `step_admitted` never finds a lane (`any(contains(one, step) ...)` becomes `False`)
    """
    assert _admitted(first, second, (Obstacle(box=_BOX, lanes=(_in(lane_box),)),)) is True
    assert _admitted(first, second, _bare()) is False


def test_a_lane_exempts_only_its_own_obstacle() -> None:
    """The step in the lane of `_BOX` still touches a second box that has no lane, and is refused.

    # UNDO: `step_admitted` looks in every obstacle's lanes (`for one in` all `obstacles`)
    """
    own = Obstacle(box=_BOX, lanes=(_in(Box(x=28, y=8, width=0, height=16)),))
    foreign = Obstacle(box=Box(x=20, y=0, width=16, height=12), lanes=())
    assert _admitted((28, 16), (28, 8), (own,)) is True
    assert _admitted((28, 16), (28, 8), (own, foreign)) is False


@pytest.mark.parametrize(
    ("lane_box", "first", "second", "expected"),
    [
        (Box(x=28, y=16, width=0, height=8), (28, 16), (28, 24), True),
        (Box(x=28, y=16, width=0, height=8), (28, 24), (28, 32), False),
        (Box(x=28, y=8, width=0, height=16), (28, 16), (28, 8), True),
        (Box(x=28, y=8, width=0, height=16), (28, 16), (36, 16), False),
        (Box(x=28, y=8, width=0, height=16), (24, 16), (32, 16), False),
    ],
)
def test_a_step_that_leaves_the_lane_and_touches_the_box_is_refused(
    lane_box: Box, first: _Cell, second: _Cell, *, expected: bool
) -> None:
    """A step past the lane's far end, or sideways out of it, is refused; along it is admitted.

    The lanes are hand-made: y 16 to 24 for the first two rows, y 8 to 24 for the rest.

    # UNDO: `step_admitted` tests only the step's first cell against the lane
    """
    assert _admitted(first, second, (Obstacle(box=_BOX, lanes=(_in(lane_box),)),)) is expected


def test_a_run_longer_than_the_lane_along_it_is_refused_whole_but_admitted_step_by_step() -> None:
    """A run longer than its lane: P1 is per step, never per run, so a caller walks a run in steps.

    The port is on the bottom edge and points N, so its lane runs y 32 to 8 through the box. The
    run (28, 24) to (28, 0) is longer than the lane: its first two steps are inside the lane and
    touch the box, the third is outside and clear. Each step alone is admitted. Given as ONE
    call, the whole run is refused, because no lane contains it.

    # UNDO: `step_admitted` tests `contains(one, step)` as a closed overlap of lane and step
    """
    port = End(at=Point(x=28, y=32), facing=Facing.N)
    obstacles = (Obstacle(box=_BOX, lanes=(lane(port, _BOX),)),)
    assert _admitted((28, 24), (28, 16), obstacles) is True
    assert _admitted((28, 16), (28, 8), obstacles) is True
    assert _admitted((28, 8), (28, 0), obstacles) is True
    assert _admitted((28, 24), (28, 8), obstacles) is True
    assert _admitted((28, 24), (28, 0), obstacles) is False


def _run(
    first: _Cell,
    second: _Cell,
    obstacles: tuple[Obstacle, ...],
    ends: frozenset[_Cell] = frozenset(),
) -> bool:
    """`run_admitted` for a run, asserting that the run read the other way round agrees."""
    forward = run_admitted(first, second, obstacles, ends)
    assert run_admitted(second, first, obstacles, ends) is forward
    return forward


def test_a_run_longer_than_the_lane_along_it_is_admitted_by_the_walker_and_refused_whole() -> None:
    """A run along the lane past its far end: the walker admits it, one whole-span call refuses.

    The same values as the per-step test above: the port on the bottom edge, pointing N, its lane
    y 32 to 8; the run (28, 24) to (28, 0) leaves the lane at its third step.

    # UNDO: `run_admitted` asks `step_admitted(first, second, ...)` once for the whole run
    """
    port = End(at=Point(x=28, y=32), facing=Facing.N)
    obstacles = (Obstacle(box=_BOX, lanes=(lane(port, _BOX),)),)
    assert _run((28, 24), (28, 0), obstacles) is True
    assert step_admitted((28, 24), (28, 0), obstacle_index(obstacles), frozenset()) is False


def test_a_run_whose_middle_step_touches_a_foreign_box_is_refused() -> None:
    """A thin foreign box on y 16 meets only the steps in the middle of a four-step run.

    The run (28, 0) to (28, 32) has its first step, y 0 to 8, and its last, y 24 to 32, clear
    of it. One column to the side the same run is admitted.

    # UNDO: `run_admitted` asks `step_admitted` for the first and the last step only
    """
    foreign = (Obstacle(box=Box(x=24, y=16, width=8, height=0), lanes=()),)
    assert _run((28, 0), (28, 32), foreign) is False
    assert _run((36, 0), (36, 32), foreign) is True


def test_a_run_that_is_not_a_multiple_of_the_grid_ends_on_a_shorter_last_step() -> None:
    """The last step is cut at the run's end: a box just past the end does not refuse the run.

    The box is y 14 to 18. The run to y 12 is 8 and then 4 long and stops short of it; the run to
    y 15 ends inside it, and is refused.

    # UNDO: in `run_admitted`, `min(WIRING_GRID, length - done)` becomes `WIRING_GRID`
    """
    beyond = (Obstacle(box=Box(x=24, y=14, width=8, height=4), lanes=()),)
    assert _run((28, 0), (28, 12), beyond) is True
    assert _run((28, 0), (28, 15), beyond) is False


def test_a_run_of_zero_length_has_no_step_and_is_admitted() -> None:
    """A point run stands in no step, even one inside a box.

    # UNDO: `run_admitted` walks `range(0, max(length, 1), WIRING_GRID)`
    """
    assert _run((28, 24), (28, 24), _bare()) is True


def test_a_run_read_from_its_other_end_gives_the_same_answer() -> None:
    """The walker follows the run's sign on each axis; `_run` swaps the ends and compares.

    # UNDO: in `run_admitted`, `dy` becomes `second[1] > first[1]` (an upward run does not move)
    """
    assert _run((28, 40), (28, 0), _bare()) is False
    assert _run((8, 24), (56, 24), _bare()) is False
    assert _run((8, 40), (56, 40), _bare()) is True
    assert _run((56, 8), (56, 40), _bare()) is True


@pytest.mark.parametrize(
    ("ends", "expected"),
    [(frozenset({(16, 32)}), True), (frozenset(), False)],
)
def test_a_step_leaving_the_box_from_an_end_cell_on_its_far_edge_is_admitted(
    ends: frozenset[_Cell], *, expected: bool
) -> None:
    """The step (16, 32) to (16, 40) starts on the box's bottom-left corner and leaves it.

    Only the step's own end cell, open in `ends`, keeps it clear of the box's far edge.

    # UNDO: in `_meets`, `high > one if one_open else high >= one` becomes `high >= one`
    """
    assert _admitted((16, 32), (16, 40), _bare(), ends) is expected


@pytest.mark.parametrize(
    ("facing", "port", "expected"),
    [
        (Facing.N, (28, 24), Box(x=28, y=8, width=0, height=16)),
        (Facing.S, (28, 24), Box(x=28, y=24, width=0, height=16)),
        (Facing.W, (24, 24), Box(x=8, y=24, width=16, height=0)),
        (Facing.E, (24, 24), Box(x=24, y=24, width=24, height=0)),
        (Facing.N, (28, 16), Box(x=28, y=8, width=0, height=8)),
        (Facing.S, (28, 32), Box(x=28, y=32, width=0, height=8)),
        (Facing.W, (16, 24), Box(x=8, y=24, width=8, height=0)),
        (Facing.E, (40, 24), Box(x=40, y=24, width=8, height=0)),
    ],
)
def test_a_lane_runs_from_the_port_to_one_grid_step_past_the_far_edge(
    facing: Facing, port: _Cell, expected: Box
) -> None:
    """All four facings, for a port inside its box and for a port on the box's edge.

    # UNDO: in `FACING_STEP`, `Facing.N` steps `(0, WIRING_GRID)` instead of `(0, -WIRING_GRID)`
    """
    got = lane(End(at=Point(x=port[0], y=port[1]), facing=facing), _BOX)
    assert got.extent == expected
    assert got.end == End(at=Point(x=port[0], y=port[1]), facing=facing)


@pytest.mark.parametrize(
    ("facing", "port", "expected"),
    [
        (Facing.N, (28, 24), Run(x=28, y=8, to_x=28, to_y=24)),
        (Facing.S, (28, 24), Run(x=28, y=24, to_x=28, to_y=40)),
        (Facing.W, (24, 24), Run(x=8, y=24, to_x=24, to_y=24)),
        (Facing.E, (24, 24), Run(x=24, y=24, to_x=48, to_y=24)),
    ],
)
def test_a_lane_run_is_the_lane_as_a_run_with_ordered_ends(
    facing: Facing, port: _Cell, expected: Run
) -> None:
    """`Lane.run` is the extent read as a `Run`: the same span, `x <= to_x` and `y <= to_y`.

    # UNDO: `Lane.run` reads `to_x=one.x + one.width` as `to_x=one.x` (a vertical lane still
    # agrees, a horizontal one loses its length)
    """
    assert lane(End(at=Point(x=port[0], y=port[1]), facing=facing), _BOX).run == expected


_F1 = hid("function", 1)
_F2 = hid("function", 2)
_P1 = hid("port", 1)
_REGION = Box(x=0, y=0, width=96, height=96)
_SECOND = Box(x=64, y=16, width=8, height=8)


def test_a_box_the_region_does_not_reach_is_dropped_and_one_on_its_border_is_kept() -> None:
    """The reach is closed: a box touching the region's border stays, a box one unit beyond goes.

    # UNDO: in `_reaches`, `box.x <= region.x + region.width` becomes a strict `<`
    """
    boxes = (
        Box(x=16, y=16, width=8, height=8),
        Box(x=200, y=200, width=8, height=8),
        Box(x=96, y=0, width=8, height=8),
        Box(x=104, y=0, width=8, height=8),
        Box(x=-16, y=0, width=16, height=8),
        Box(x=0, y=-8, width=8, height=8),
        Box(x=0, y=-16, width=8, height=8),
    )
    got = Space(shapes=tuple(Shape(owner=_F1, box=box) for box in boxes)).obstacles({}, _REGION)
    assert got == tuple(Obstacle(box=boxes[i], lanes=()) for i in (0, 2, 4, 5))


def test_a_box_at_the_regions_high_y_border_is_kept_and_one_unit_beyond_it_dropped() -> None:
    """The reach is closed on the bottom border too: y 96 stays, y 104 goes.

    # UNDO: in `_reaches`, `box.y <= region.y + region.height` becomes a strict `<`
    """
    boxes = (Box(x=16, y=96, width=8, height=8), Box(x=16, y=104, width=8, height=8))
    got = Space(shapes=tuple(Shape(owner=_F1, box=box) for box in boxes)).obstacles({}, _REGION)
    assert got == (Obstacle(box=boxes[0], lanes=()),)


def test_the_lanes_of_a_shared_box_come_from_every_sharing_owner_in_shape_order() -> None:
    """Two owners share one `Box`: each obstacle carries the lanes of both owners' own ends.

    # UNDO: in `Space.obstacles`, `owners[shape.box]` becomes `(shape.owner,)`
    """
    e1 = End(at=Point(x=20, y=24), facing=Facing.N)
    e3 = End(at=Point(x=28, y=24), facing=Facing.S)
    e2 = End(at=Point(x=36, y=24), facing=Facing.S)
    own_ends = {_F1: (e1, e3), _P1: (e2,)}
    lanes = (lane(e1, _BOX), lane(e3, _BOX), lane(e2, _BOX))
    shapes = (Shape(owner=_F1, box=_BOX), Shape(owner=_P1, box=_BOX), Shape(owner=_F2, box=_SECOND))
    assert Space(shapes=shapes).obstacles(own_ends, _REGION) == (
        Obstacle(box=_BOX, lanes=lanes),
        Obstacle(box=_BOX, lanes=lanes),
        Obstacle(box=_SECOND, lanes=()),
    )
    flipped = Space(shapes=(shapes[1], shapes[0])).obstacles(own_ends, _REGION)
    assert flipped[0].lanes == (lanes[2], lanes[0], lanes[1])


def test_an_owner_with_no_own_ends_and_a_label_box_have_no_lanes() -> None:
    """A function that is not an end of the edge, a `None` owner and an empty entry give `()`.

    # UNDO: in `Space.obstacles`, `own_ends.get(sharer, ())` becomes the first owner's ends
    """
    e1 = End(at=Point(x=28, y=24), facing=Facing.N)
    shapes = (
        Shape(owner=_F1, box=_BOX),
        Shape(owner=_F2, box=_SECOND),
        Shape(owner=None, box=Box(x=64, y=48, width=8, height=8)),
    )
    got = Space(shapes=shapes).obstacles({_F1: (e1,), _P1: ()}, _REGION)
    assert [one.lanes for one in got] == [(lane(e1, _BOX),), (), ()]
    assert Space(shapes=shapes[1:2]).obstacles({_F2: ()}, _REGION) == (
        Obstacle(box=_SECOND, lanes=()),
    )


def test_the_obstacles_follow_the_order_of_the_shapes() -> None:
    """The result is in shape order, not sorted by position.

    # UNDO: in `Space.obstacles`, iterate `sorted(self.shapes, key=...)` by `box.x`
    """
    boxes = (
        Box(x=64, y=16, width=8, height=8),
        Box(x=16, y=16, width=8, height=8),
        Box(x=40, y=16, width=8, height=8),
    )
    got = Space(shapes=tuple(Shape(owner=_F1, box=box) for box in boxes)).obstacles({}, _REGION)
    assert [one.box for one in got] == list(boxes)


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (Run(x=28, y=8, to_x=28, to_y=40), True),
        (Run(x=8, y=8, to_x=8, to_y=40), False),
        (Run(x=8, y=24, to_x=48, to_y=24), True),
        (Run(x=8, y=40, to_x=48, to_y=40), False),
        (Run(x=20, y=20, to_x=20, to_y=28), True),
        (Run(x=20, y=20, to_x=36, to_y=20), True),
        (Run(x=24, y=24, to_x=24, to_y=40), True),
    ],
)
def test_a_run_through_or_inside_the_box_crosses_and_one_clear_of_it_does_not(
    run: Run, *, expected: bool
) -> None:
    """Through the interior, on either axis, or wholly inside, is a crossing; clear is not.

    # UNDO: in `crosses`, `box.x < run.to_x` becomes `box.x > run.to_x`
    """
    assert crosses(_BOX, run) is expected


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (Run(x=16, y=8, to_x=16, to_y=40), False),
        (Run(x=24, y=8, to_x=24, to_y=40), True),
        (Run(x=40, y=8, to_x=40, to_y=40), False),
        (Run(x=8, y=16, to_x=48, to_y=16), False),
        (Run(x=8, y=32, to_x=48, to_y=32), False),
        (Run(x=8, y=24, to_x=48, to_y=24), True),
    ],
)
def test_a_run_flush_along_an_edge_does_not_cross(run: Run, *, expected: bool) -> None:
    """Touching is allowed: a run along any of the four edges is no crossing, one inside it is.

    # UNDO: in `crosses`, `run.y < box.y + box.height` becomes `run.y <= box.y + box.height`
    """
    assert crosses(_BOX, run) is expected


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (Run(x=28, y=8, to_x=28, to_y=16), False),
        (Run(x=28, y=8, to_x=28, to_y=24), True),
        (Run(x=28, y=32, to_x=28, to_y=48), False),
        (Run(x=28, y=24, to_x=28, to_y=48), True),
        (Run(x=8, y=24, to_x=16, to_y=24), False),
        (Run(x=8, y=24, to_x=24, to_y=24), True),
        (Run(x=40, y=24, to_x=56, to_y=24), False),
        (Run(x=32, y=24, to_x=56, to_y=24), True),
    ],
)
def test_a_run_resting_with_one_end_on_the_border_does_not_cross(
    run: Run, *, expected: bool
) -> None:
    """A run that only reaches the border from outside is no crossing; one that enters is.

    # UNDO: in `crosses`, `box.y < run.to_y` becomes `box.y <= run.to_y`
    """
    assert crosses(_BOX, run) is expected


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (Run(x=8, y=16, to_x=16, to_y=16), False),
        (Run(x=16, y=8, to_x=16, to_y=16), False),
        (Run(x=40, y=32, to_x=48, to_y=32), False),
        (Run(x=40, y=32, to_x=40, to_y=40), False),
        (Run(x=8, y=24, to_x=24, to_y=24), True),
        (Run(x=32, y=24, to_x=48, to_y=24), True),
    ],
)
def test_a_run_ending_in_a_corner_does_not_cross(run: Run, *, expected: bool) -> None:
    """A run that reaches or leaves a corner is no crossing.

    # UNDO: `crosses` returns `covers(box, run)`
    """
    assert crosses(_BOX, run) is expected


@pytest.mark.parametrize(
    ("at", "expected"),
    [
        ((28, 24), True),
        ((16, 24), False),
        ((40, 24), False),
        ((28, 16), False),
        ((28, 32), False),
        ((40, 32), False),
        ((8, 24), False),
    ],
)
def test_a_zero_length_run_crosses_only_from_the_interior(at: _Cell, *, expected: bool) -> None:
    """A stub of zero length (a marker on its box's edge) is a point: only the inside crosses.

    # UNDO: in `crosses`, `run.x < box.x + box.width` becomes `run.x <= box.x + box.width`
    """
    assert crosses(_BOX, Run(x=at[0], y=at[1], to_x=at[0], to_y=at[1])) is expected


# a port at (28, 24), inside `_BOX`, for each facing: the run out of it (on the ray, far past the
# box), the run out of it starting one unit behind the port, and the run entirely behind it
_LEAVING = [
    (Facing.N, Run(x=28, y=0, to_x=28, to_y=24), Run(x=28, y=0, to_x=28, to_y=25)),
    (Facing.S, Run(x=28, y=24, to_x=28, to_y=48), Run(x=28, y=23, to_x=28, to_y=48)),
    (Facing.W, Run(x=0, y=24, to_x=28, to_y=24), Run(x=0, y=24, to_x=29, to_y=24)),
    (Facing.E, Run(x=28, y=24, to_x=48, to_y=24), Run(x=27, y=24, to_x=48, to_y=24)),
]


@pytest.mark.parametrize(("facing", "leaving", "_"), _LEAVING)
def test_a_run_wholly_on_the_outward_ray_of_its_own_port_is_exempt_and_bare_it_crosses(
    facing: Facing, leaving: Run, _: Run
) -> None:
    """A run on the lane leaves the port and runs on far past the box. The twin: no lane.

    # UNDO: in `_on_lane`, the north test `run.to_y <= at.y` becomes `run.to_y < at.y`
    #       (fails the north case)
    """
    own = (lane(End(at=Point(x=28, y=24), facing=facing), _BOX),)
    assert crosses(_BOX, leaving)
    assert not crosses_unless_leaving(_BOX, leaving, own)
    assert crosses_unless_leaving(_BOX, leaving, ())


@pytest.mark.parametrize(("facing", "_", "behind"), _LEAVING)
def test_a_run_that_starts_one_unit_behind_its_port_is_not_exempt(
    facing: Facing, _: Run, behind: Run
) -> None:
    """The exemption is for a run on the lane, directed: one unit behind the port and it crosses.

    # UNDO: in `_on_lane`, the south test `run.y >= at.y` becomes `run.y >= at.y - 8`
    #       (fails the south case)
    """
    own = (lane(End(at=Point(x=28, y=24), facing=facing), _BOX),)
    assert crosses_unless_leaving(_BOX, behind, own)


@pytest.mark.parametrize(
    ("run", "ends", "expected"),
    [
        pytest.param(
            Run(x=29, y=0, to_x=29, to_y=24), [(28, 24, Facing.N)], True, id="beside the ray"
        ),
        pytest.param(
            Run(x=8, y=24, to_x=28, to_y=24), [(28, 24, Facing.N)], True, id="across the ray"
        ),
        pytest.param(
            Run(x=28, y=0, to_x=28, to_y=24), [(12, 24, Facing.N)], True, id="another port's ray"
        ),
        pytest.param(
            Run(x=28, y=0, to_x=28, to_y=24),
            [(12, 24, Facing.N), (28, 24, Facing.N)],
            False,
            id="one of two ends",
        ),
        pytest.param(
            Run(x=28, y=0, to_x=28, to_y=24), [(28, 24, Facing.S)], True, id="the other facing"
        ),
    ],
)
def test_only_a_run_on_one_of_the_given_lanes_is_exempt(
    run: Run, ends: list[tuple[int, int, Facing]], *, expected: bool
) -> None:
    """A run beside or across a port's line, on another port's, or a lane facing away, is not.

    # UNDO: `crosses_unless_leaving` tests `any(...)` as `all(...)` (fails "one of two ends")
    """
    given = tuple(lane(End(at=Point(x=x, y=y), facing=facing), _BOX) for x, y, facing in ends)
    assert crosses_unless_leaving(_BOX, run, given) is expected


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        pytest.param(
            Run(x=28, y=8, to_x=28, to_y=48), False, id="out of the port, through the box"
        ),
        pytest.param(Run(x=28, y=4, to_x=28, to_y=48), True, id="from behind the port"),
    ],
)
def test_a_port_outside_its_box_facing_it_frees_the_run_that_starts_at_the_port(
    run: Run, *, expected: bool
) -> None:
    """A marker's port stands outside the marker's box and faces it: the ray runs through the box.

    # UNDO: in `_on_lane`, the south test `run.y >= at.y` becomes `run.y >= at.y - 8`
    #       (fails "from behind the port")
    """
    own = (lane(End(at=Point(x=28, y=8), facing=Facing.S), _BOX),)
    assert crosses_unless_leaving(_BOX, run, own) is expected


def test_a_run_that_does_not_cross_the_box_is_not_a_crossing_with_or_without_ends() -> None:
    """The exemption only removes crossings: a run clear of the box stays clear.

    # UNDO: `crosses_unless_leaving` returns `not any(...)` without the `crosses` term
    """
    clear = Run(x=8, y=0, to_x=8, to_y=48)
    assert not crosses_unless_leaving(_BOX, clear, ())
    own = (lane(End(at=Point(x=28, y=24), facing=Facing.N), _BOX),)
    assert not crosses_unless_leaving(_BOX, clear, own)


# a port one step outside `_BOX`, facing it, for each facing: a run out of the port through the
# box and far past it, and a run of the same line that starts one unit behind the port
_OUTSIDE = [
    (Facing.E, (8, 24), Run(x=8, y=24, to_x=80, to_y=24), Run(x=7, y=24, to_x=80, to_y=24)),
    (Facing.W, (48, 24), Run(x=0, y=24, to_x=48, to_y=24), Run(x=0, y=24, to_x=49, to_y=24)),
    (Facing.S, (28, 8), Run(x=28, y=8, to_x=28, to_y=80), Run(x=28, y=7, to_x=28, to_y=80)),
    (Facing.N, (28, 40), Run(x=28, y=0, to_x=28, to_y=40), Run(x=28, y=0, to_x=28, to_y=41)),
]


@pytest.mark.parametrize(("facing", "port", "along", "behind"), _OUTSIDE)
def test_a_lane_frees_the_run_that_starts_at_its_port_and_not_one_from_behind(
    facing: Facing, port: _Cell, along: Run, behind: Run
) -> None:
    """The 3,474 class, each facing: the run from the port is exempt, one from behind it is not.

    A run that starts one unit behind the port crosses the box the same way, but the unbounded
    ray of a bare box would let it in; the lane keeps the port's end, so it is directed. The run
    that starts beyond the port is exempt too, and a run that starts at the port and stops
    inside the box is.

    # UNDO: in `_on_lane`, the east test `run.x >= at.x` becomes `True` (fails the east case);
    # likewise the west, south and north tests (fails that case)
    """
    own = (lane(End(at=Point(x=port[0], y=port[1]), facing=facing), _BOX),)
    assert crosses(_BOX, along)
    assert crosses(_BOX, behind)
    assert not crosses_unless_leaving(_BOX, along, own)
    assert crosses_unless_leaving(_BOX, behind, own)
    assert crosses_unless_leaving(_BOX, along, ())


def test_a_run_that_starts_beyond_the_port_or_ends_inside_the_box_is_on_the_lane() -> None:
    """An E port at (8, 24): (12, 24) to (80, 24) starts beyond it, (8, 24) to (24, 24) ends inside.

    The twin from behind the port, (0, 24) to (24, 24), is a finding; so is a run of the other
    line that crosses the box, and a run beside the port's line.

    # UNDO: in `_on_lane`, the east test `run.x >= at.x` becomes `run.x >= at.x - 8`
    """
    own = (lane(End(at=Point(x=8, y=24), facing=Facing.E), _BOX),)
    assert not crosses_unless_leaving(_BOX, Run(x=12, y=24, to_x=80, to_y=24), own)
    assert not crosses_unless_leaving(_BOX, Run(x=8, y=24, to_x=24, to_y=24), own)
    assert crosses_unless_leaving(_BOX, Run(x=0, y=24, to_x=24, to_y=24), own)
    assert crosses_unless_leaving(_BOX, Run(x=8, y=20, to_x=24, to_y=20), own)
    assert crosses_unless_leaving(_BOX, Run(x=28, y=0, to_x=28, to_y=48), own)


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (Run(x=16, y=8, to_x=16, to_y=40), True),
        (Run(x=8, y=8, to_x=8, to_y=40), False),
        (Run(x=40, y=8, to_x=40, to_y=40), True),
        (Run(x=48, y=8, to_x=48, to_y=40), False),
        (Run(x=8, y=16, to_x=48, to_y=16), True),
        (Run(x=8, y=8, to_x=48, to_y=8), False),
        (Run(x=8, y=32, to_x=48, to_y=32), True),
        (Run(x=8, y=40, to_x=48, to_y=40), False),
    ],
)
def test_a_run_on_an_edge_is_covered_far_edges_included_and_one_unit_off_is_not(
    run: Run, *, expected: bool
) -> None:
    """The cover is closed: all four edges cover, one grid unit away does not.

    # UNDO: in `covers`, `run.x <= box.x + box.width` becomes `run.x < box.x + box.width`
    """
    assert covers(_BOX, run) is expected


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (Run(x=8, y=16, to_x=16, to_y=16), True),
        (Run(x=0, y=16, to_x=8, to_y=16), False),
        (Run(x=16, y=8, to_x=16, to_y=16), True),
        (Run(x=40, y=32, to_x=48, to_y=32), True),
        (Run(x=40, y=40, to_x=48, to_y=40), False),
        (Run(x=40, y=32, to_x=40, to_y=40), True),
    ],
)
def test_a_run_touching_a_corner_is_covered_and_one_unit_short_of_it_is_not(
    run: Run, *, expected: bool
) -> None:
    """A run that only reaches a corner is covered; one unit short of the corner it is not.

    # UNDO: in `covers`, `box.y <= run.to_y` becomes `box.y < run.to_y`
    """
    assert covers(_BOX, run) is expected


@pytest.mark.parametrize(
    ("at", "expected"),
    [
        ((16, 24), True),
        ((40, 24), True),
        ((28, 32), True),
        ((28, 24), True),
        ((8, 24), False),
        ((28, 40), False),
        ((28, 8), False),
    ],
)
def test_a_point_is_covered_on_an_edge_and_inside_but_not_outside(
    at: _Cell, *, expected: bool
) -> None:
    """A run of zero length, a stub's x or a lane's end: on the edge or inside covers, outside not.

    # UNDO: in `covers`, `box.x <= run.to_x` becomes `box.x < run.to_x`
    """
    assert covers(_BOX, Run(x=at[0], y=at[1], to_x=at[0], to_y=at[1])) is expected


_CONTENT = Box(x=16, y=16, width=24, height=24)


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        (Box(x=16, y=16, width=24, height=24), True),
        (Box(x=16, y=16, width=8, height=8), True),
        (Box(x=32, y=32, width=8, height=8), True),
        (Box(x=24, y=24, width=0, height=0), True),
        (Box(x=40, y=40, width=0, height=0), True),
        (Box(x=15, y=16, width=8, height=8), False),
        (Box(x=33, y=16, width=8, height=8), False),
        (Box(x=16, y=15, width=8, height=8), False),
        (Box(x=16, y=33, width=8, height=8), False),
        (Box(x=16, y=16, width=25, height=24), False),
        (Box(x=41, y=40, width=0, height=0), False),
        (Box(x=500, y=500, width=8, height=8), False),
    ],
)
def test_a_space_holds_a_box_inside_its_content_flush_edges_included_and_one_unit_past_is_not(
    box: Box, *, expected: bool
) -> None:
    """P3's containment in the page's content box is closed: flush is inside, one unit past is not.

    # UNDO: in `Space.holds`, `contains(self.content, box)` becomes a strict-inside test
    """
    assert Space(shapes=(), content=_CONTENT).holds(box) is expected


def test_a_space_with_no_content_holds_every_box() -> None:
    """`content=None` bounds nothing, as for a space that only routes or finds.

    # UNDO: in `Space.holds`, `self.content is None or` is dropped (it then raises on None)
    """
    assert Space(shapes=()).holds(Box(x=-500, y=500, width=8, height=8)) is True


def _touches_for_a_step(far: int, monkeypatch: pytest.MonkeyPatch) -> int:
    """The `_touches` calls of one step beside `_BOX` on a page with `far` far-away obstacles."""
    calls = []
    original = space._touches
    monkeypatch.setattr(space, "_touches", lambda *args: calls.append(1) or original(*args))
    far_boxes = tuple(
        Obstacle(box=Box(x=800 + 24 * n, y=0, width=16, height=16), lanes=()) for n in range(far)
    )
    step_admitted((24, 8), (24, 16), obstacle_index((*far_boxes, *_bare())), frozenset())
    return len(calls)


def test_a_step_tests_only_the_obstacles_in_its_cells(monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact `_touches` count of a step does not grow with the obstacles far from it."""
    # UNDO: `CellIndex.meeting` returns every item (the count then follows the page)
    assert _touches_for_a_step(5, monkeypatch) == 1
    assert _touches_for_a_step(50, monkeypatch) == 1
