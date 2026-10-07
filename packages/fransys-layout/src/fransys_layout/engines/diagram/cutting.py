"""The diagram placer's cuts (BD5): a line crossing a sheet break is a stub and a marker per sheet.

Each half starts at its box and ends at the marker, on the grid inside the cut's zone.
"""

from fransys_layout.engines.diagram.route import Half, touch
from fransys_layout.engines.diagram.sizes import MARKER_W
from fransys_layout.geometry import Point
lazy from fransys_layout.engines.diagram.frame_values import FrameCut
lazy from fransys_layout.engines.diagram.route import Where


def stubs(first: Where, second: Where, cut: FrameCut) -> tuple[Half, Half]:
    """The halves of a line cut between `first` (left sheet) and `second` (right sheet)."""
    (s1, left, e1), (s2, _right, e2) = first, second
    free = left.x + left.width + cut.left_zone - MARKER_W
    near = Half(sheet=s1, points=(touch(first), Point(x=free, y=e1.y)), other=s2)
    far = Half(sheet=s2, points=(touch(second), Point(x=MARKER_W, y=e2.y)), other=s1)
    return near, far
