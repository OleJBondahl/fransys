"""Acceptance skeletons and unit tests: `stages.labels`."""

import dataclasses

from samples import PROFILE, drawn, hid, placed

from fransys_layout.geometry import (
    Box,
    Facing,
    Orientation,
    Point,
    SlotGeometry,
    SymbolGeometry,
)
from fransys_layout.stages import (
    LabelKind,
    LabelRequest,
    place_slot_labels,
)
from fransys_layout.stages.labels import SlotFrame

# A tag just wider than the 32 G tag slot (33 G): two of them still meet across a gap
WIDE = "-K123456"


def _tag(number: int, text: str) -> LabelRequest:
    return LabelRequest(kind=LabelKind.TAG, subject=hid("function", number), slot="tag", text=text)


# --- helpers for the unit tests ------------------------------------------------------

BODY = Box(x=-8, y=-16, width=16, height=32)
E_TAG = SlotGeometry(
    slot="tag", at=Point(x=16, y=0), side=Facing.E, box=Box(x=16, y=-4, width=32, height=8)
)
W_TAG = SlotGeometry(
    slot="tag", at=Point(x=-16, y=0), side=Facing.W, box=Box(x=-48, y=-4, width=32, height=8)
)


def _symbol(*slots: SlotGeometry, keepout: Box = BODY) -> SymbolGeometry:
    """A 16 x 32 body at the origin with `slots`; `keepout` is what bounds a label's moves."""
    return SymbolGeometry(
        key="invented",
        poles=1,
        orientation=Orientation.R0,
        body=BODY,
        keepout=keepout,
        through=None,
        ports=(),
        slots=slots,
    )


def _at(number: int, geometry: SymbolGeometry, *, x: int, y: int):
    """Function `number` placed at `(x, y)` with `geometry` instead of the sample symbol."""
    return dataclasses.replace(placed(number, x=x, y=y), geometry=geometry)


def _value(number: int, text: str) -> LabelRequest:
    return LabelRequest(
        kind=LabelKind.MARKING, subject=hid("function", number), slot="value", text=text
    )


def _reference(number: int, text: str) -> LabelRequest:
    return LabelRequest(
        kind=LabelKind.CROSS_REFERENCE, subject=hid("function", number), slot="tag", text=text
    )


# --- the box of a slot ---------------------------------------------------------------


# --- moving along the side, then to the opposite one ---------------------------------


def test_a_blocked_label_moves_one_text_height_down_first() -> None:
    """The nearest offset wins, and the positive one comes before the negative one."""
    labels, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=120, y=92, width=32, height=8),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=120, y=100, width=13, height=8)
    assert findings == ()


def test_a_label_reflects_to_the_opposite_side_when_its_own_side_is_full() -> None:
    """Every offset on the E side is taken, so the box mirrors across the body's centre line."""
    labels, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=120, y=80, width=80, height=32),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=75, y=92, width=13, height=8)
    assert findings == ()


# --- what `place_slot_labels` raises --------------------------------------------------


# --- wire labels ---------------------------------------------------------------------


# --- order ---------------------------------------------------------------------------


# --- what the mutation sweep asked for -----------------------------------------------


def test_the_box_height_is_the_profiles_text_height_whatever_the_slot_box_says() -> None:
    """A tall slot box does not make a tall label: text height never changes."""
    tall = SlotGeometry(
        slot="tag", at=Point(x=16, y=0), side=Facing.E, box=Box(x=16, y=-4, width=32, height=24)
    )
    labels, _ = place_slot_labels(
        (_tag(1, "-K1"),),
        (_at(1, _symbol(tall), x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=120, y=92, width=13, height=8)


def test_a_short_and_a_long_tag_keep_one_near_edge() -> None:
    """Owner: every text's near edge, the one facing what it is attached to, sits at a fixed
    offset from it and the text grows away. An E-slot tag keeps its left edge, a W-slot tag
    its right edge, for a 2- and a 12-character text alike. Can-fail, checked by hand: with
    `slot_box` centring the text on its slot this fails."""
    for geometry, near in ((E_TAG, lambda b: b.x), (W_TAG, lambda b: b.x + b.width)):
        edges = set()
        for text in ("K1", "-K1234567890"):
            labels, _ = place_slot_labels(
                (_tag(1, text),),
                (_at(1, _symbol(geometry), x=200, y=96),),
                (drawn(1),),
                frame=SlotFrame(content=None, profile=PROFILE),
            )
            edges.add(near(labels[0].box))
        assert len(edges) == 1
