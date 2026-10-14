"""Open cores in the cable placer: a landing at the pin and a stub, or two stubs (CC6).

An open core crosses the cable box as a core does. A landed end stands at its pin; every other
end is a stub, a blank end one grid unit long.
"""

from typing import Any
lazy from collections.abc import Mapping

from fransys_layout.engines.cable.place_frame import box_room
from fransys_layout.engines.cable.values import BlockFacts, CoreFacts, PlacedEnd
from fransys_layout.geometry import WIRING_GRID
lazy from fransys_model.kernel import Id

STUB = WIRING_GRID  # the stub of an open end

type Landing = tuple[bool, tuple[int, PlacedEnd], tuple[int, PlacedEnd]]
type Where = Mapping[tuple[Id[Any], Id[Any]], tuple[int, PlacedEnd]]


def _stub(end: PlacedEnd, y: int, *, top: bool) -> PlacedEnd:
    """A blank end of no size at height `y`, where an open core's stub ends."""
    return PlacedEnd(
        item=end.item,
        top=top,
        dashed=False,
        blank=True,
        x=end.x,
        y=y,
        width=0,
        height=0,
        cells=(),
    )


def open_landing(facts: BlockFacts, core: CoreFacts, where: Where, box_y: int) -> Landing:
    """An open core's top and bottom ends as (x, end); the stubs stand at `box_y`'s box edges.

    A core's places are its landing and, in the top row, where its stub stands (`DrawnOpen`).
    """
    here = [place for (c, _), place in where.items() if c == core.conductor]
    tops = [place for place in here if place[1].top]
    below = [place for place in here if not place[1].top]
    x, end = (tops or below)[0]
    landed_above = core.landed and not below  # landed in the top row: the pin is its top
    top = tops[0] if landed_above else (x, _stub(end, box_y - STUB, top=True))
    bottom_y = box_y + box_room(facts)[0] + STUB
    bottom = below[0] if below and core.landed else (top[0], _stub(end, bottom_y, top=False))
    return True, top, bottom
