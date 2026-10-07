"""What every cable block must satisfy (CT5-3, spec acceptance 4, 18, 5): checks on runs and a box.

A run is a sequence of points with `.x` and `.y`, from a `PlacedWire` or a `CoreWire` alike.
"""

from itertools import combinations, pairwise

from fransys_layout.geometry import WIRING_GRID, Point
from fransys_layout.stages.grid_path import axes_of, cells_of, clean_crossing


def _points(run) -> tuple[Point, ...]:
    return tuple(Point(x=p.x, y=p.y) for p in run)


def assert_no_shared_stretch(runs) -> None:
    """Acceptance 4: two wires meet only across, one `h` against one `v`, never at a corner."""
    found = [_points(run) for run in runs]
    for one, other in combinations(found, 2):
        mine, theirs = axes_of(one), axes_of(other)
        for cell in cells_of(one) & cells_of(other):
            assert clean_crossing(mine[cell], theirs[cell]), (cell, one, other)


def assert_outside_the_box(runs, box: tuple[int, int, int, int]) -> None:
    """Acceptance 18: no segment of any run has a point strictly inside the cable box."""
    x, y, width, height = box
    for run in runs:
        for a, b in pairwise(_points(run)):
            inside = (
                min(a.x, b.x) < x + width
                and max(a.x, b.x) > x
                and min(a.y, b.y) < y + height
                and max(a.y, b.y) > y
            )
            assert not inside, (a, b, box)


def assert_on_the_grid(runs) -> None:
    """Acceptance 5: every point of every run lies on the wiring grid."""
    for run in runs:
        assert all(p.x % WIRING_GRID == 0 and p.y % WIRING_GRID == 0 for p in run), run
