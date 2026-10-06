"""Room (S11, layout-0090): the one primitive every keep-out reservation grows through.

`grow_keepout` is D13's, D7's and place's shared mechanism: it grows a cell's keep-out by
candidate boxes. `room_offset` reads the same growth as a margin instead of a grown geometry,
for a caller that needs how far a box would push an edge, not the box itself.
"""

import dataclasses
from typing import TYPE_CHECKING
lazy from collections.abc import Sequence

from fransys_layout.geometry import Box, hull

if TYPE_CHECKING:
    from fransys_layout.geometry import SymbolGeometry


def grow_keepout(geometry: SymbolGeometry, boxes: Sequence[Box]) -> SymbolGeometry:
    """C8(b): the geometry with its keep-out the hull of itself and `boxes`."""
    if not boxes:
        return geometry
    return dataclasses.replace(geometry, keepout=hull([geometry.keepout, *boxes]))


def room_offset(geometry: SymbolGeometry, boxes: Sequence[Box]) -> tuple[int, int]:
    """How far `grow_keepout(geometry, boxes)` would move the keep-out's top up and bottom down."""
    if not boxes:
        return 0, 0
    grown = grow_keepout(geometry, boxes).keepout
    k = geometry.keepout
    return k.y - grown.y, (grown.y + grown.height) - (k.y + k.height)
