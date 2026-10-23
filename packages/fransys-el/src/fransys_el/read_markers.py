"""A `layout.link_marker` record read into the marker symbol it is drawn as (CORE-TEXTS C)."""

from typing import TYPE_CHECKING, Literal, cast

from electrical_symbols import (
    MARKER_FACING,
    MARKER_SLOT,
    MARKER_TURN_FACING,
    MARKER_TURNED,
    marker_symbol,
)
from fransys_layout.core import Box
from fransys_layout.drawing import DrawnSymbol
from fransys_layout.symbols import library_symbol, stretched_body
from fransys_model.derive.drawing_text import marker_text, reference_slot
from fransys_model.kernel import render_id

from .drawn_identity import net_text
from .ref_tints import REF_TINTS

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_layout.core import Orientation
    from fransys_model.kernel import Model
    from fransys_model.layout import LinkMarker

__all__ = ["drawn_marker"]


def drawn_marker(model: Model, record: LinkMarker, library: Library) -> DrawnSymbol:
    """The marker symbol of `record`'s kind, turned to its facing, with its derive text."""
    kind = record.key[3]
    slot = reference_slot(model, record)
    assert record.facing is not None  # noqa: S101 -- a link marker always stores its facing
    side = record.facing.name
    along = (
        side in MARKER_TURN_FACING
    )  # over or under a pin: the turned symbol, text along the wire
    key = MARKER_TURNED if along else marker_symbol(kind)
    orient = cast("Orientation", (MARKER_TURN_FACING if along else MARKER_FACING)[side])
    stretch: tuple[Literal["x", "y"], int] = ("y", record.height) if along else ("x", record.width)
    body = stretched_body(library_symbol(library, key), orient, *stretch, library)
    return DrawnSymbol(
        id=render_id(record.id),
        key=key,
        x=record.x,
        y=record.y,
        orient=orient,
        slots=((MARKER_SLOT, marker_text(model, record)),),
        stretch=(stretch,),
        tint=None if slot is None else REF_TINTS[slot],
        outline=Box(record.x + body.x, record.y + body.y, body.w, body.h),
        ports=(record.port.value,),
        net=net_text(model, record.port),
    )
