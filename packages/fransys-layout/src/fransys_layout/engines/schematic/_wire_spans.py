"""Layout-0172, round 5: each routed wire's runs as spans, which a stub's box is kept off.

Layout-0246: a marker's stub is a wire too; a line's fan split never stands on it.
"""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import Point
from fransys_layout.stages.space import span

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.geometry import Box
    from fransys_layout.stages.types import LinkMarker, Route


def route_spans(
    routes: Sequence[Route], markers: Sequence[LinkMarker] = ()
) -> dict[tuple[int, int], tuple[Box, ...]]:
    """Each page's routed wires' and marker stubs' runs as spans: a stub's box is kept off them."""
    found: dict[tuple[int, int], list[Box]] = defaultdict(list)
    for route in routes:
        found[route.drawing_set, route.page] += (
            span(first.at, second.at) for first, second in pairwise(route.points)
        )
    for marker in markers:
        found[marker.drawing_set, marker.page].append(span(marker.at, _stub_tip(marker)))
    return {page: tuple(boxes) for page, boxes in found.items()}


def _stub_tip(marker: LinkMarker) -> Point:
    """Where a marker's stub meets its box: the port's nearest point of the box."""
    box = marker.box
    return Point(
        x=min(max(marker.at.x, box.x), box.x + box.width),
        y=min(max(marker.at.y, box.y), box.y + box.height),
    )
