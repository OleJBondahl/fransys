"""A `layout.link_marker` record read into the marker symbol it is drawn as (CORE-TEXTS C)."""

from typing import TYPE_CHECKING, cast

from electrical_symbols import (
    MARKER_FACING,
    MARKER_SLOT,
    MARKER_TURN_FACING,
    MARKER_TURNED,
    marker_symbol,
)
from fransys_layout.core import Box
from fransys_layout.drawing import DrawnSymbol
from fransys_layout.symbols import library_symbol, marker_rule
from fransys_model.derive.drawing_text import marker_text, reference_slot
from fransys_model.kernel import render_id

from .drawn_identity import net_text
from .placement_markers import LONE
from .placement_views import marker_boxes
from .ref_tints import REF_TINTS

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout.core import Orientation
    from fransys_model.kernel import Model
    from fransys_model.layout import LinkMarker, Side

__all__ = ["drawn_marker"]


def drawn_marker(model: Model, record: LinkMarker, library: Library) -> DrawnSymbol:
    """The marker symbol of `record`'s kind, turned to its facing, with its derive text."""
    slot = reference_slot(model, record)
    side = cast("Side", record.facing).name  # a link marker always stores its facing
    along = side in MARKER_TURN_FACING  # over or under a pin: the turned symbol, text along the wire
    key = MARKER_TURNED if along else marker_symbol(record.key[3])
    orient = cast("Orientation", (MARKER_TURN_FACING if along else MARKER_FACING)[side])
    text = marker_text(model, record)
    size = (record.width, record.height)  # the reserve; a stub or copy is already fitted by `stub_fit`
    if record.key[3] not in LONE:
        own = marker_boxes(library, text)[cast("Orientation", MARKER_FACING[side])]  # keyed by the record's core orientation
        size = (own.w, own.h)
    stretch, body = marker_rule(library_symbol(library, key), orient, size, library, along=along)
    return DrawnSymbol(
        id=render_id(record.id),
        key=key,
        x=record.x,
        y=record.y,
        orient=orient,
        slots=((MARKER_SLOT, text),),
        stretch=stretch,
        tint=None if slot is None else REF_TINTS[slot],
        outline=Box(record.x + body.x, record.y + body.y, body.w, body.h),
        ports=(record.port.value,),
        net=net_text(model, record.port),
    )
