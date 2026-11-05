"""The room the placer packs for a symbol: its keep-out as measured, plus a coil's contact table.

Library boxes arrive as plain values. The tag slot is 48 G wide whatever the designation, so the
standalone footprint widens it to the measured tag; a strip row's shared tag is printed once.
"""

from typing import TYPE_CHECKING

from fransys_layout.core import Box, outline_hull
from fransys_layout.symbols import text_width_g
from fransys_model.derive import Extent, Footprints
from fransys_model.layout import Side

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library

__all__ = ["footprints"]

TAG = "tag"


def _extent(box: Box) -> Extent:
    """A core box as the model's `Extent`."""
    return Extent(x=box.x, y=box.y, width=box.w, height=box.h)


def _measured_tag(slot: Box, width: int, tag_side: Side) -> Box:
    """The tag `slot` widened to `width` if shorter, growing toward `tag_side`."""
    grown = max(slot.w, width)
    return Box(slot.x + slot.w - grown if tag_side is Side.W else slot.x, slot.y, grown, slot.h)


def footprints(  # noqa: PLR0913 - the fixed signature of the fact: texts and library values
    library: Library,
    *,
    body: Box,
    slots: Mapping[str, Box],
    tag: str,
    tag_side: Side,
    text_height: int,
    cells: tuple[tuple[str, ...], tuple[str, ...]],
    table_height: int,
    step: int,
    pad: int,
) -> Footprints:
    """A function's footprint alone and in a strip row, in G, in the frame of its symbol's body.

    Alone: body, slots (the tag slot as wide as the printed `tag`) and a coil's contact table
    below. In a strip row: body and the slots but the tag.
    """
    others = [slot for name, slot in slots.items() if name != TAG]
    in_row = outline_hull([body, *others], 0)
    tag_slot = slots.get(TAG)
    width = text_width_g(library.font, tag, height=text_height)
    tag_box = [] if tag_slot is None else [_measured_tag(tag_slot, width, tag_side)]
    alone = outline_hull([in_row, *tag_box], 0)
    no, nc = cells
    widest = [max((text_width_g(library.font, t, height=step) for t in col), default=0) for col in cells]
    table = Box(alone.x, alone.y + alone.h, sum(widest) + 3 * pad, table_height) if no or nc else None
    return Footprints(
        standalone=_extent(outline_hull([alone, table], 0) if table else alone),
        in_strip_row=_extent(in_row),
        alone=_extent(alone),
        no_cells=no,
        nc_cells=nc,
    )
