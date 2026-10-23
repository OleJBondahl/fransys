"""`routing.space`: `lane` and D2's edge predicates (layout-0083).

Every value is made by hand: one box, `_BOX`, at x 16..40, y 16..32 on the grid of 8, and
cells, lanes and runs beside it. Each test states its own UNDO, the one-line change to
`space.py` that must make it fail.
"""

from typing import Any

import pytest

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.routing import space
from fransys_layout.routing.space import (
    End,
    Lane,
    Obstacle,
    Run,
    crosses,
    lane,
    obstacle_index,
    runs_along,
    step_admitted,
)
from fransys_model.kernel import Id

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


def hid(kind: str, number: int) -> Id[Any]:
    """An invented id of `kind`; equal `number`, equal id."""
    return Id(kind=kind, value=f"{number:032x}")


_F1 = hid("function", 1)
_F2 = hid("function", 2)
_P1 = hid("port", 1)
_REGION = Box(x=0, y=0, width=96, height=96)
_SECOND = Box(x=64, y=16, width=8, height=8)


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


# a port at (28, 24), inside `_BOX`, for each facing: the run out of it (on the ray, far past the
# box), the run out of it starting one unit behind the port, and the run entirely behind it
_LEAVING = [
    (Facing.N, Run(x=28, y=0, to_x=28, to_y=24), Run(x=28, y=0, to_x=28, to_y=25)),
    (Facing.S, Run(x=28, y=24, to_x=28, to_y=48), Run(x=28, y=23, to_x=28, to_y=48)),
    (Facing.W, Run(x=0, y=24, to_x=28, to_y=24), Run(x=0, y=24, to_x=29, to_y=24)),
    (Facing.E, Run(x=28, y=24, to_x=48, to_y=24), Run(x=27, y=24, to_x=48, to_y=24)),
]


# a port one step outside `_BOX`, facing it, for each facing: a run out of the port through the
# box and far past it, and a run of the same line that starts one unit behind the port
_OUTSIDE = [
    (Facing.E, (8, 24), Run(x=8, y=24, to_x=80, to_y=24), Run(x=7, y=24, to_x=80, to_y=24)),
    (Facing.W, (48, 24), Run(x=0, y=24, to_x=48, to_y=24), Run(x=0, y=24, to_x=49, to_y=24)),
    (Facing.S, (28, 8), Run(x=28, y=8, to_x=28, to_y=80), Run(x=28, y=7, to_x=28, to_y=80)),
    (Facing.N, (28, 40), Run(x=28, y=0, to_x=28, to_y=40), Run(x=28, y=0, to_x=28, to_y=41)),
]


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (Run(x=16, y=8, to_x=16, to_y=40), True),
        (Run(x=16, y=32, to_x=16, to_y=40), False),
        (Run(x=16, y=8, to_x=16, to_y=16), False),
        (Run(x=8, y=32, to_x=48, to_y=32), True),
        (Run(x=8, y=24, to_x=48, to_y=24), False),
        (Run(x=8, y=8, to_x=48, to_y=8), False),
    ],
)
def test_a_run_lies_along_a_box_only_on_a_side_for_a_positive_length(
    run: Run, *, expected: bool
) -> None:
    """A side shared for a positive length counts; a touch at a corner or a crossing does not.

    # UNDO: in `runs_along`, `min(run.to_y, bottom) > max(run.y, box.y)` becomes `>=`
    """
    assert runs_along(_BOX, run) is expected


_CONTENT = Box(x=16, y=16, width=24, height=24)


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


@pytest.mark.parametrize(
    ("run", "along"),
    [
        (Run(x=40, y=8, to_x=40, to_y=24), True),  # the right side, from above into it
        (Run(x=16, y=32, to_x=24, to_y=32), True),  # the bottom side
        (Run(x=40, y=0, to_x=40, to_y=16), False),  # meets the corner only
        (Run(x=8, y=24, to_x=48, to_y=24), False),  # crosses both sides
        (Run(x=48, y=16, to_x=48, to_y=32), False),  # beside the box, off its side
    ],
)
def test_runs_along_is_a_side_shared_for_a_length_and_never_a_crossing(
    run: Run, *, along: bool
) -> None:
    """BO6-SHRINK. UNDO: `runs_along`: `> max(run.y, box.y)` -> `>= max(run.y, box.y)`."""
    assert runs_along(_BOX, run) is along
