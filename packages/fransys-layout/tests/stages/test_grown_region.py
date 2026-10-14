"""A region grows to hold boxes and the room a leaving line runs past them (layout-0230)."""

from fransys_layout.geometry import Box
from fransys_layout.stages.line_trunk import grown_region

REGION = Box(x=0, y=0, width=100, height=100)


def test_a_box_far_out_grows_the_region_by_the_leaving_room() -> None:
    """A point at x 200 grows the region to 200 plus six wiring grids of 8."""
    # UNDO: stages/line_trunk.py:grown_region, `LEAVE_GRIDS * WIRING_GRID` -> `0`
    assert grown_region(REGION, [Box(x=200, y=50, width=0, height=0)]).width == 248


def test_a_box_inside_leaves_the_region_alone() -> None:
    """A point inside the region changes nothing."""
    # UNDO: stages/line_trunk.py:grown_region, return `region` -> a region grown by the margin
    assert grown_region(REGION, [Box(x=50, y=50, width=0, height=0)]) == REGION
