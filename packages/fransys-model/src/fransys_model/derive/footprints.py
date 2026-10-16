"""The room the placer packs for a symbol: its keep-out as measured, plus a coil's table tiers.

Library boxes arrive as plain values. The tag slot is 48 G wide whatever the designation, so the
standalone footprint widens it to the measured tag; a strip row's shared tag is printed once.
"""

lazy from collections.abc import Iterable, Mapping

from fransys_model.derive.contact_image import contact_marks
from fransys_model.derive.contact_rows import table_geometry
from fransys_model.derive.contacts import owned_contacts
from fransys_model.derive.rows_footprints import Extent, Footprints
from fransys_model.derive.tag_text import tag_text
from fransys_model.derive.text_width import text_width
from fransys_model.layout import Side
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

__all__ = ["footprints"]

TAG = "tag"


def _hull(boxes: Iterable[Extent]) -> Extent:
    """The smallest box holding every box in `boxes`."""
    found = tuple(boxes)
    left, top = min(b.x for b in found), min(b.y for b in found)
    right, bottom = max(b.x + b.width for b in found), max(b.y + b.height for b in found)
    return Extent(x=left, y=top, width=right - left, height=bottom - top)


def _measured_tag(slot: Extent, width: int, tag_side: Side) -> Extent:
    """The tag `slot` widened to `width` if shorter, growing toward `tag_side`."""
    grown = max(slot.width, width)
    x = slot.x + slot.width - grown if tag_side is Side.W else slot.x
    return Extent(x=x, y=slot.y, width=grown, height=slot.height)


def _marks(model: Model, function: Id[Function]) -> tuple[list[str], list[str]]:
    """The NO and NC marks of every contact the coil's item owns."""
    no, nc = list[str](), list[str]()
    for contact in owned_contacts(model, functions(model)[function].item):
        contact_no, contact_nc = contact_marks(model, contact)
        no.extend(contact_no)
        nc.extend(contact_nc)
    return no, nc


def _table_room(  # noqa: PLR0913 - the footprints arguments passed on, no more
    model: Model,
    function: Id[Function],
    below: Extent,
    *,
    step: int,
    pad: int,
    tiers: int,
    place_text: str,
) -> Extent | None:
    """The room of a coil's contact table below `below`, `tiers` tables high, else `None`."""
    record: Function = functions(model)[function]
    if record.kind is not FunctionKind.COIL:
        return None
    no, nc = _marks(model, function)
    if not (no or nc):
        return None
    widest = [
        max((text_width(f"{m} {place_text}", height=step) for m in c), default=0) for c in (no, nc)
    ]
    rows = max(len(no), len(nc))
    height = tiers * table_geometry(rows, step, pad, headed=False).height
    return Extent(x=below.x, y=below.y + below.height, width=sum(widest) + 3 * pad, height=height)


def footprints(  # noqa: PLR0913 - the fixed signature of the fact: library values, profile values
    model: Model,
    function: Id[Function],
    *,
    body: Extent,
    slots: Mapping[str, Extent],
    tag_side: Side,
    text_height: int,
    step: int,
    pad: int,
    tiers: int = 2,
    place_text: str = "/99.99",
) -> Footprints:
    """A function's footprint alone and in a strip row, in G, in the frame of its symbol's body.

    Alone: body and slots, the tag slot as wide as the tag text, plus a coil's contact table
    tiers below. In a strip row: body and the slots but the tag, which the strip prints once.
    """
    others = [slot for name, slot in slots.items() if name != TAG]
    in_row = _hull([body, *others])
    tag_slot = slots.get(TAG)
    tag = text_width(tag_text(model, function), height=text_height)
    tag_box = [] if tag_slot is None else [_measured_tag(tag_slot, tag, tag_side)]
    alone = _hull([in_row, *tag_box])
    table = _table_room(
        model, function, alone, step=step, pad=pad, tiers=tiers, place_text=place_text
    )
    return Footprints(standalone=_hull([alone, table]) if table else alone, in_strip_row=in_row)
