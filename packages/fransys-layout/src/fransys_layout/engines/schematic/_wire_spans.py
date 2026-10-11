"""Layout-0172, round 5: each routed wire's runs as spans, which a stub's box is kept off."""

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.stages.space import span

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.geometry import Box
    from fransys_layout.stages.types import Route


def route_spans(routes: Sequence[Route]) -> dict[tuple[int, int], tuple[Box, ...]]:
    """Each page's routed wires' runs as spans: a stub's box is kept off them (round 5)."""
    found: dict[tuple[int, int], list[Box]] = defaultdict(list)
    for route in routes:
        found[route.drawing_set, route.page] += (
            span(first.at, second.at) for first, second in pairwise(route.points)
        )
    return {page: tuple(boxes) for page, boxes in found.items()}
