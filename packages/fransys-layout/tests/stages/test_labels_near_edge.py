"""D14 (designer ruling 5): a label that is reflected keeps its near edge at a fixed offset.

The near edge is the one facing the symbol. A reflected label is mirrored to the opposite
side of the body, and the mirror of the slot's anchor is where its near edge lands, whatever
the text width: only the far edge moves with the text.
"""

import dataclasses

import pytest
from samples import PROFILE, drawn, hid, placed

from fransys_layout.geometry import (
    Box,
    Facing,
    Orientation,
    Point,
    SlotGeometry,
    SymbolGeometry,
)
from fransys_layout.stages import LabelKind, LabelRequest, place_slot_labels
from fransys_layout.stages.labels import SlotFrame

SHORT, LONG = "-K1", "-K1234567890"
AT_X, AT_Y = 104, 96
BODY = Box(x=-8, y=-16, width=16, height=32)
# The keep-out box: wide enough for the text to slide.
WIDE = Box(x=-48, y=-32, width=96, height=64)
E_TAG = SlotGeometry(
    slot="tag", at=Point(x=16, y=0), side=Facing.E, box=Box(x=16, y=-4, width=32, height=8)
)
W_TAG = SlotGeometry(
    slot="tag", at=Point(x=-16, y=0), side=Facing.W, box=Box(x=-48, y=-4, width=32, height=8)
)


def _symbol(slot: SlotGeometry) -> SymbolGeometry:
    """A 16 x 32 body at the origin with one slot, its keep-out box wide enough to slide in."""
    return SymbolGeometry(
        key="invented",
        poles=1,
        orientation=Orientation.R0,
        body=BODY,
        keepout=WIDE,
        through=None,
        ports=(),
        slots=(slot,),
    )


def _request(slot: str, kind: LabelKind, text: str) -> LabelRequest:
    return LabelRequest(kind=kind, subject=hid("function", 1), slot=slot, text=text)


# (slot, kind, own side filled, near edge of the reflected box, mirror of the anchor)
_CASES = {
    "E": (E_TAG, LabelKind.TAG, Box(x=112, y=0, width=400, height=300)),
    "W": (W_TAG, LabelKind.TAG, Box(x=-300, y=0, width=396, height=300)),
}


def _near_edge_of_the_reflection(side: str, text: str) -> tuple[int, int]:
    """(near edge, its distance from the body's centre line) of the label after reflection."""
    slot, kind, full = _CASES[side]
    symbol = dataclasses.replace(placed(1, x=AT_X, y=AT_Y), geometry=_symbol(slot))
    labels, findings = place_slot_labels(
        (_request(slot.slot, kind, text),),
        (symbol,),
        (drawn(1),),
        occupied=(full,),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert findings == ()
    box = labels[0].box
    body = Box(x=AT_X + BODY.x, y=AT_Y + BODY.y, width=BODY.width, height=BODY.height)
    if slot.side is Facing.E:  # reflected to the W side: the near edge is the right one
        return box.x + box.width, body.x + body.width // 2
    return box.x, body.x + body.width // 2  # W -> E: the near edge is the left one


@pytest.mark.parametrize("side", ["E", "W"])
def test_a_reflected_label_keeps_its_near_edge_whatever_the_text_width(side: str) -> None:
    """D14: a short and a long text in a reflected slot have the same near-edge coordinate,
    and it is the mirror of the slot's own anchor across the body's centre line."""
    # UNDO: stages/_labelling.py `_reflected`, vertical case: `x=box.x` instead of the
    # mirrored `x=2 * body.x + body.width - box.x - box.width` (the box then keeps its left
    # edge, so the near edge follows the text width).
    short = _near_edge_of_the_reflection(side, SHORT)
    long = _near_edge_of_the_reflection(side, LONG)
    assert short == long
    slot = _CASES[side][0]
    edge, centre = short
    assert edge == 2 * centre - (AT_X + slot.at.x)
