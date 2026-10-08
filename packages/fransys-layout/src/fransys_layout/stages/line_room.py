"""HL18 (layout-0158): the room a leaving line and its stub need beyond its pins' row.

A pin that ends a line's conductor may end a leaving line: its fan-out, the 48 G run and the
stub stand beyond the pin. The page's first rows keep that room above, the last rows below,
as they keep it for their texts (C14), so no line or stub crosses the frame.
"""

from typing import TYPE_CHECKING, Protocol

from fransys_layout.geometry import WIRING_GRID, Facing, snap_up

from .line_draw import FAN_GRIDS
from .line_trunk import LEAVE_GRIDS

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from fransys_layout.geometry import SymbolGeometry

    from .types import DrawnFunction, Handle, Profile


class Cell(Protocol):
    """A cell on its way to a place, as `place` stacks it: its function and its geometry."""

    function: Handle
    geometry: SymbolGeometry


def line_room(
    page: Sequence[Sequence[Sequence[Cell]]],
    drawn_of: Mapping[Handle, DrawnFunction],
    line_ends: AbstractSet[tuple[Handle, Handle]],
    profile: Profile,
) -> tuple[int, int]:
    """How far the first rows' line ends reach above their keep-outs, the last rows' below.

    `line_ends` holds each `(function, port)` a line's conductor lands on.
    """
    stub = WIRING_GRID + profile.text_height + 2 * profile.marker_padding
    reach = (FAN_GRIDS + LEAVE_GRIDS) * WIRING_GRID + stub
    lift = sink = 0
    for rows in page:
        if rows:
            lift = max(lift, _beyond(rows[0], drawn_of, line_ends, (Facing.N, reach)))
            sink = max(sink, _beyond(rows[-1], drawn_of, line_ends, (Facing.S, reach)))
    return snap_up(lift), snap_up(sink)


def _beyond(
    row: Sequence[Cell],
    drawn_of: Mapping[Handle, DrawnFunction],
    line_ends: AbstractSet[tuple[Handle, Handle]],
    toward: tuple[Facing, int],
) -> int:
    """How far past its keep-out a line end of `row` facing `toward[0]` reaches."""
    facing, reach = toward
    found = 0
    for cell in row:
        function, geometry = cell.function, cell.geometry
        drawn = drawn_of.get(function)
        names = (
            {p.symbol_port for p in drawn.ports if (function, p.port) in line_ends}
            if drawn
            else set()
        )
        keepout = geometry.keepout
        for port in geometry.ports:
            if port.name in names and port.facing is facing:
                if facing is Facing.N:
                    found = max(found, keepout.y - (port.at.y - reach))
                else:
                    found = max(found, port.at.y + reach - keepout.y - keepout.height)
    return found
