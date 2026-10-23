"""Stage 8b: the obstacle grid of one page for its designations (layout-0304).

It holds every placed body, every wire (a trunk is a wire per lane), every marker box and every
table box, on the wiring grid; the labels are marked into it by the pass, one by one.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

from .geometry import marker_box
from .occupancy import Occupancy

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .outputs import Anchored, Marker, PagePlacement, Table, Wire
    from .values import Box, Options, Size


def page_obstacles(
    page: PagePlacement,
    markers: Sequence[Marker],
    tables: Sequence[Table],
    options: Options,
    anchored: Sequence[Anchored] = (),
) -> list[Box]:
    """The marker boxes and table boxes of this page."""
    boxes = [marker_box(m, options) for m in markers if m.page == page.page]
    boxes += [t.box for t in tables if t.page == page.page]
    return boxes + [a.outline for a in anchored if a.page == page.page]


def page_grid(
    page: PagePlacement,
    wires: Sequence[Wire],
    obstacles: Sequence[Box],
    area: Size,
    options: Options,
) -> Occupancy:
    """The page's grid with bodies, wires and the other boxes marked, no label."""
    step = options.wiring_grid
    grid = Occupancy(
        area.w // step + options.spare_cells, area.h // step + options.spare_cells, step
    )
    for placed in page.placed:
        grid.mark_box(placed.body)
    for wire in wires:
        for a, b in pairwise(wire.points):
            grid.mark_wire(wire.net, (a, b))
    for box in obstacles:
        grid.mark_box(box)
    return grid
