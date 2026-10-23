"""`routing.space.run_of`: the run between two points that share one coordinate."""

from fransys_layout.geometry import Point
from fransys_layout.routing.space import Run, run_of


def test_run_spans_both_points_in_either_order() -> None:
    """The run's corners are the two points' min and max, whichever point comes first."""
    expected = Run(x=0, y=0, to_x=0, to_y=8)
    assert run_of(Point(x=0, y=0), Point(x=0, y=8)) == expected
    assert run_of(Point(x=0, y=8), Point(x=0, y=0)) == expected
