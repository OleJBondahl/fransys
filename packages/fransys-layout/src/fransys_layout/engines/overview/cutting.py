"""The diagram placer's cuts: a line crossing a sheet break is a stub and a marker per sheet.

Each half starts at its box and ends at the marker, on the grid inside the cut's zone.
"""

from fransys_layout.engines.overview.lanes.diagram_route import Half, touch
from fransys_layout.engines.overview.sizes import MARKER_W, stub_reach
from fransys_layout.geometry import Facing, Point
lazy from fransys_layout.engines.overview.lanes.diagram_route import Where
lazy from fransys_layout.engines.overview.lanes.frame_values import FrameCut


def stubs(first: Where, second: Where, cut: FrameCut) -> tuple[Half, Half]:
    """The halves of a line cut between `first` (left sheet) and `second` (right sheet)."""
    (s1, left, e1), (s2, _right, e2) = first, second
    free = left.x + left.width + cut.left_zone - MARKER_W
    near = Half(sheet=s1, points=(touch(first), Point(x=free, y=e1.y)), other=s2)
    far = Half(sheet=s2, points=(touch(second), Point(x=MARKER_W, y=e2.y)), other=s1)
    return near, far


def _stub(where: Where, other: int, label_width: int) -> Half:
    """A stub out of the end `where` that holds its label, ended by a marker for sheet `other`."""
    start = touch(where)
    reach = stub_reach(label_width) if where[2].side is Facing.E else -stub_reach(label_width)
    return Half(sheet=where[0], points=(start, Point(x=start.x + reach, y=start.y)), other=other)


def jump_stubs(first: Where, second: Where, label_width: int) -> tuple[Half, Half]:
    """The halves of a line that skips a column across a sheet start: a stub and a marker at each end."""
    return _stub(first, second[0], label_width), _stub(second, first[0], label_width)
