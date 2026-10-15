"""The bends and the length of the conductor lines drawn on each page, read once.

`fr.readability` and nothing else reports them (model-0254). The lines are the routed wires
(`layout.route`), the legs of a harness fan-out (`layout.harness_fan_out`) and the straight power
leads, which the caller measures. A harness or cable line is not one: it is a separate fact.
A line is a polyline in grid units; a bend is a change of direction along it.
"""

from collections import defaultdict
from collections.abc import Mapping  # noqa: TC003 -- signature tests resolve hints at runtime
from decimal import Decimal
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_model.kernel import Id, Model  # noqa: TC001 -- signature tests resolve hints at runtime
from fransys_model.layout import HarnessFanOut, Page, Route, layout_of, sheet_format_of

from .rows_readability import PageWires
from .text_width import G_PER_MODULE

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.layout import RoutePoint

__all__ = ["page_wires"]


def page_wires(model: Model, lead_grids: Mapping[Id[Page], int]) -> dict[Id[Page], PageWires]:
    """The bends and the length in mm of the conductor lines of each page of `model` with one.

    `lead_grids` is the total length in grid units of each page's straight power leads, which
    only layout knows; they add length and no bend.
    """
    pages = layout_of(model, Page)
    sums: defaultdict[Id[Page], tuple[int, Decimal]] = defaultdict(lambda: (0, Decimal(0)))
    lines = [(route.page, route.points) for route in layout_of(model, Route).values()]
    for fan in layout_of(model, HarnessFanOut).values():
        lines += [(fan.page, leg.points) for leg in fan.legs]
    for page, points in lines:
        bends, grid = _measure(points)
        sums[page] = (sums[page][0] + bends, sums[page][1] + grid)
    for page, grid in lead_grids.items():
        sums[page] = (sums[page][0], sums[page][1] + grid)
    return {
        page: PageWires(
            bends=bends,
            length_mm=grid
            * sheet_format_of(model, pages[page].sheet_format).module_mm
            / G_PER_MODULE,
        )
        for page, (bends, grid) in sums.items()
    }


def _measure(points: Iterable[RoutePoint]) -> tuple[int, Decimal]:
    """The direction changes of a polyline, and its length in grid units (a slant counts true)."""
    steps = [(b.x - a.x, b.y - a.y) for a, b in pairwise(points) if (a.x, a.y) != (b.x, b.y)]
    bends = sum(_sign(first) != _sign(second) for first, second in pairwise(steps))
    return bends, sum((Decimal(dx * dx + dy * dy).sqrt() for dx, dy in steps), Decimal(0))


def _sign(step: tuple[int, int]) -> tuple[bool, bool, bool, bool]:
    dx, dy = step
    return dx > 0, dx < 0, dy > 0, dy < 0
