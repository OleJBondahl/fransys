"""The diagram placer's labels (BD5): a line's text sits above the middle of its longest run."""

from itertools import pairwise

from fransys_layout.engines.diagram.sizes import TEXT_LEAD
from fransys_layout.geometry import WIRING_GRID as G
lazy from fransys_layout.geometry import Point


def label_at(points: tuple[Point, ...], text_height: int) -> tuple[int, int]:
    """The label's centre: above the longest horizontal run (the first on a tie), on the grid."""
    runs = [(a, b) for a, b in pairwise(points) if a.y == b.y]
    a, b = max(runs, key=lambda r: abs(r[1].x - r[0].x), default=(points[0], points[0]))
    return (a.x + b.x) // 2 // G * G, (a.y - text_height // 2 - TEXT_LEAD) // G * G
