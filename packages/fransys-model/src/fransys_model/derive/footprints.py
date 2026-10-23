"""The room the placer packs for a symbol: its keep-out as measured, plus a coil's contact table.

Library boxes arrive as plain values. The tag slot is 48 G wide whatever the designation, so the
standalone footprint widens it to the measured tag; a strip row's shared tag is printed once.
"""

from itertools import zip_longest
lazy from collections.abc import Iterable, Mapping

from fransys_model.derive.contact_image import coil_image_cells, contact_marks
from fransys_model.derive.contact_rows import CONTACT_COLUMNS, table_geometry
from fransys_model.derive.contacts import owned_contacts
from fransys_model.derive.rows_footprints import Extent, Footprints
from fransys_model.derive.tag_text import tag_text
from fransys_model.derive.text_width import text_width
from fransys_model.layout import Side
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function

__all__ = ["coil_table_texts", "footprints"]

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


def _is_coil(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is a coil: the one place the footprints ask."""
    return functions(model)[function].kind is FunctionKind.COIL


def _cells(model: Model, function: Id[Function], place_text: str) -> tuple[list[str], list[str]]:
    """A coil's NO and NC cells, "{mark} {place_text}" each; both empty for a non-coil."""
    if not _is_coil(model, function):
        return [], []
    no, nc = _marks(model, function)
    return [f"{m} {place_text}" for m in no], [f"{m} {place_text}" for m in nc]


def coil_table_texts(model: Model, coil: Id[Function]) -> tuple[tuple[str, ...], ...]:
    """A coil's contact table as texts: the column titles, then a (NO, NC) cell pair per row.

    A column that ran out leaves an empty cell; a coil with no cells has none (an empty tuple).
    """
    if not _is_coil(model, coil):
        return ()
    no, nc = coil_image_cells(model, coil)
    rows = [(a, b) for a, b in zip_longest(no, nc, fillvalue="")]
    return (CONTACT_COLUMNS, *rows) if rows else ()


def _table_room(
    no: list[str], nc: list[str], below: Extent, *, step: int, pad: int
) -> Extent | None:
    """The room of the contact table of these cells below `below`, one table high, else `None`."""
    if not (no or nc):
        return None
    widest = [max((text_width(t, height=step) for t in column), default=0) for column in (no, nc)]
    height = table_geometry(max(len(no), len(nc)), step, pad, headed=False).height
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
    place_text: str = "/99.99",
) -> Footprints:
    """A function's footprint alone and in a strip row, in G, in the frame of its symbol's body.

    Alone: body and slots, the tag slot as wide as the tag text, plus a coil's contact table
    below (one table). In a strip row: body and the slots but the tag, which the strip prints once.
    """
    others = [slot for name, slot in slots.items() if name != TAG]
    in_row = _hull([body, *others])
    tag_slot = slots.get(TAG)
    tag = text_width(tag_text(model, function), height=text_height)
    tag_box = [] if tag_slot is None else [_measured_tag(tag_slot, tag, tag_side)]
    alone = _hull([in_row, *tag_box])
    no, nc = _cells(model, function, place_text)
    table = _table_room(no, nc, alone, step=step, pad=pad)
    return Footprints(
        standalone=_hull([alone, table]) if table else alone,
        in_strip_row=in_row,
        alone=alone,
        no_cells=tuple(no),
        nc_cells=tuple(nc),
    )
