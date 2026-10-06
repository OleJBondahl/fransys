"""`lint._segments.runs_of`: one run per orthogonal leg, collinear legs not joined (step 2, F2)."""

from samples import hid

from fransys_layout.geometry import Point
from fransys_layout.lint._segments import runs_of
from fransys_layout.stages import Route, RoutePoint
from fransys_layout.stages.space import run_of


def _route(*points: tuple[int, int]) -> Route:
    return Route(
        connection=hid("conductor", 1),
        physical_net=hid("net", 1),
        drawing_set=1,
        page=1,
        a=hid("port", 12),
        b=hid("port", 21),
        points=tuple(RoutePoint(index=i, at=Point(x=x, y=y)) for i, (x, y) in enumerate(points)),
    )


def test_collinear_legs_stay_separate_runs() -> None:
    """Two legs on one line are two runs: the lint reads each leg, not each straight stretch."""
    runs = runs_of(_route((0, 0), (0, 8), (0, 16)))
    assert runs == (
        run_of(Point(x=0, y=0), Point(x=0, y=8)),
        run_of(Point(x=0, y=8), Point(x=0, y=16)),
    )


def test_a_repeat_and_a_diagonal_are_not_runs() -> None:
    """A repeated point and a slanted leg give no run; the corner leg after them does."""
    runs = runs_of(_route((0, 0), (0, 0), (8, 8), (8, 16)))
    assert runs == (run_of(Point(x=8, y=8), Point(x=8, y=16)),)
