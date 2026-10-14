"""Stage 9, geometric lint: one page's records, grouped (geometric.py)."""

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, LayoutError, translate
from fransys_layout.stages.content import content_box
from fransys_layout.stages.lookups import placed_keepout

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages import (
        Handle,
        LinkMarker,
        PlacedFunction,
        PlacedLabel,
        Route,
        SheetFormat,
    )
    from fransys_layout.stages.types import PlacedOutline

    from ._harness import HarnessInk, PageInk

_MIN_POINTS = 2  # a route is at least its two ends, even `[p, p]`


@dataclass(frozen=True, slots=True)
class _Page:
    """Everything of one `(drawing_set, page)`; `placed` is in handle order."""

    placed: tuple[PlacedFunction, ...]
    boxes: tuple[tuple[PlacedFunction, Box], ...]
    bodies: tuple[tuple[PlacedFunction, Box], ...]
    routes: tuple[Route, ...]
    labels: tuple[PlacedLabel, ...]
    markers: tuple[LinkMarker, ...]
    content: Box
    outlines: tuple[PlacedOutline, ...]
    ink: PageInk
    hidden: frozenset[tuple[Handle, int, int]]
    sheet: SheetFormat
    here: tuple[int, int]


@dataclass(frozen=True, slots=True)
class _ByPage:
    """The layout's records grouped by `(drawing_set, page)`, one pass each (layout-0086)."""

    placed: Mapping[tuple[int, int], tuple[PlacedFunction, ...]]
    routes: Mapping[tuple[int, int], tuple[Route, ...]]
    labels: Mapping[tuple[int, int], tuple[PlacedLabel, ...]]
    markers: Mapping[tuple[int, int], tuple[LinkMarker, ...]]
    outlines: Mapping[tuple[int, int], tuple[PlacedOutline, ...]]


def _make_page(
    here: tuple[int, int],
    on: _ByPage,
    seen: tuple[SheetFormat, HarnessInk, PageInk],
) -> _Page:
    """The `_Page` of one `(drawing set, page)` from the layout's records by page."""
    sheet, ink, page_ink = seen
    placed = tuple(sorted(on.placed.get(here, ()), key=lambda one: one.function))
    if any(one.function == other.function for one, other in pairwise(placed)):
        msg = "one function is placed twice on one page"
        raise LayoutError(msg)
    routes = tuple(on.routes.get(here, ()))
    if any(len(route.points) < _MIN_POINTS for route in routes):
        msg = "a route has fewer than two points"
        raise LayoutError(msg)
    return _Page(
        placed=placed,
        boxes=tuple((one, placed_keepout(one)) for one in placed),
        bodies=tuple(
            (one, translate(one.geometry.body, dx=one.at.x, dy=one.at.y)) for one in placed
        ),
        routes=routes,
        labels=tuple(on.labels.get(here, ())),
        markers=tuple(on.markers.get(here, ())),
        content=content_box(sheet),
        outlines=on.outlines.get(here, ()),
        ink=page_ink,
        hidden=ink.hidden,
        sheet=sheet,
        here=here,
    )
