"""A column's extent, the one rule packing and the lint both read (layout-0175).

A column's extent is the hull of every box it draws: its symbols' keep-outs, its labels' and its
link markers' boxes, each measured by real text width. Packing reads it from the first placing's
preferred boxes (`drawn_boxes`); the lint reads it from the final ones.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, hull

from .labels import request_boxes
from .onepage import page_wiring
from .texts.markers import link_markers, placed_world

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any

    from .pagerun import PageInputs
    from .references.types import MarkerDecision, References
    from .types import (
        Column,
        DrawnFunction,
        Handle,
        LabelRequest,
        LinkMarker,
        PlacedFunction,
        Profile,
    )

type Extras = dict[tuple[int, int, Handle], list[Box]]


def column_extent(boxes: Iterable[Box]) -> Box:
    """The smallest box over everything one column draws."""
    return hull(boxes)


def drawn_boxes(
    pages: Iterable[
        tuple[tuple[LabelRequest, ...], tuple[PlacedFunction, ...], tuple[DrawnFunction, ...]]
    ],
    profile: Profile,
) -> Extras:
    """Per (set, page, function), the preferred boxes of the labels its page asks for."""
    found: Extras = defaultdict(list)
    for requests, placed, drawn in pages:
        if not placed:
            continue
        here = placed[0]
        for function, box in request_boxes(requests, placed, drawn, profile):
            found[here.drawing_set, here.page, function].append(box)
    return found


def marker_boxes(
    decisions: Sequence[MarkerDecision], markers: Sequence[LinkMarker], found: Extras
) -> Extras:
    """`found` with each marker's box added to the function its decision names."""
    for one, marker in zip(decisions, markers, strict=True):
        found.setdefault((one.drawing_set, one.page, one.function), []).append(marker.box)
    return found


def page_extras(
    inputs: PageInputs,
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    pages: Sequence[Any],
    references: References,
) -> Extras:
    """The label and marker boxes of the placed `pages` (placed, first call), by function."""
    profile = inputs.profile
    found = drawn_boxes([(first.requests, placed, first.drawn) for placed, first in pages], profile)
    placed = tuple(one for page, _ in pages for one in page)
    _, _, wired = page_wiring(references.connections, columns, placed, references.net_groups)
    markers = link_markers(
        references.markers,
        placed_world(placed, drawn),
        wired=wired,
        sheet=inputs.sheet,
        profile=profile,
    )
    return marker_boxes(references.markers, markers, found)
