"""`stages.texts.place_texts`: the placer on hand-built `Space` and anchors, no pipeline.

One text size, 30 by 7, and one slot anchor, x 40..60, y 20..27, whose tag candidates are
the W home `_W` (x 10..40, y 20..27), a step down (y 27..34), a step up (y 13..20), and so
on, then the E side from x 60. Each test states the one Edit to the placer or the table that
makes it fail.
"""

import pytest
from fransys_el import TEXTS
from samples import hid

from fransys_layout.geometry import Box, Facing, LayoutError, Point
from fransys_layout.stages.space import Run, Shape, Space
from fransys_layout.stages.texts.candidates import TextKind, stub_anchor
from fransys_layout.stages.texts.place_texts import (
    LABEL_UNPLACED,
    Anchor,
    PlacedText,
    TextToPlace,
    place_texts,
)

_SLOT = Anchor(box=Box(x=40, y=20, width=20, height=7), facing=Facing.W)
_W = Box(x=10, y=20, width=30, height=7)
_W_DOWN = Box(x=10, y=27, width=30, height=7)
_W_UP = Box(x=10, y=13, width=30, height=7)
_E = Box(x=60, y=20, width=30, height=7)
_F, _G = hid("function", 1), hid("function", 2)
_G_PORT = hid("port", 21)
_EMPTY = Space(shapes=())
_ORIGIN = Point(x=0, y=0)


def _tag(
    function=_F, position=_ORIGIN, own=None, anchors=(_SLOT,), kind=TextKind.TAG
) -> TextToPlace:
    return TextToPlace(
        kind=kind,
        handle=function,
        position=position,
        width=30,
        height=7,
        anchors=anchors,
        own=(function,) if own is None else own,
    )


def _boxes(placed: tuple[PlacedText, ...]) -> list[Box]:
    return [one.box for one in placed]


def test_with_both_sides_free_the_tag_takes_the_tables_first_candidate() -> None:
    """The core case: W and E both free, the tag stands W, the table's first. UNDO: the TAG row's
    mirror side put before its own, and the tag stands E."""
    placed, findings = place_texts((_tag(),), _EMPTY, TEXTS)
    assert _boxes(placed) == [_W]
    assert findings == ()


def test_a_blocked_home_moves_the_tag_one_step_along_its_side_before_the_other_side() -> None:
    """The nearest step first, then the opposite side. UNDO: the TAG row's own-side steps
    cut to the home step alone, so a blocked home falls to the mirror side before the step
    down, and the tag stands E."""
    blocker = Shape(owner=_G, box=Box(x=12, y=18, width=4, height=6))  # on _W, clear of _W_DOWN
    placed, _ = place_texts((_tag(),), Space(shapes=(blocker,)), TEXTS)
    assert _boxes(placed) == [_W_DOWN]


def test_with_nothing_free_the_first_candidate_stands_with_a_finding() -> None:
    """None free, the first candidate stands, flagged, with `LABEL_UNPLACED`."""
    wall = Shape(owner=None, box=Box(x=-100, y=-100, width=300, height=300))
    placed, findings = place_texts((_tag(),), Space(shapes=(wall,)), TEXTS)
    assert placed == (PlacedText(kind=TextKind.TAG, handle=_F, slot="", box=_W, unplaced=True),)
    assert [(f.code, f.subjects, f.message) for f in findings] == [
        (LABEL_UNPLACED, (_F,), "no free place beside the slot")
    ]


def test_a_reference_is_placed_before_a_tag_that_would_take_its_one_place() -> None:
    """The kind order: the reference first, though the tag comes first in position and in
    the input. Its one candidate (x 10..40, y 25..32) is on the tag's W home and a step down,
    so the tag steps up. UNDO: the tag's priority set to the reference's, and the reference
    stands unplaced under the tag."""
    reference = TextToPlace(
        kind=TextKind.REFERENCE,
        handle=_G_PORT,
        position=Point(x=100, y=100),
        width=30,
        height=7,
        anchors=(Anchor(box=stub_anchor(Point(x=25, y=40)), facing=Facing.N),),
        own=(_G, _G_PORT),
    )
    placed, findings = place_texts((_tag(), reference), _EMPTY, TEXTS)
    assert [(one.kind, one.box) for one in placed] == [
        (TextKind.REFERENCE, Box(x=10, y=25, width=30, height=7)),
        (TextKind.TAG, _W_UP),
    ]
    assert findings == ()


def test_a_route_run_blocks_through_the_interior_and_not_flush() -> None:
    """A run along the box's bottom edge touches, one through it crosses."""
    flush, _ = place_texts((_tag(),), _EMPTY, TEXTS, runs=(Run(0, 27, 50, 27),))
    across, _ = place_texts((_tag(),), _EMPTY, TEXTS, runs=(Run(0, 24, 50, 24),))
    assert _boxes(flush) == [_W]
    assert _boxes(across) == [_W_DOWN]


def test_two_texts_with_one_kind_handle_and_slot_raise() -> None:
    """The key must order every text; two with one key would fall back to input order."""
    with pytest.raises(LayoutError, match="share one kind, handle and slot"):
        place_texts((_tag(), _tag(position=Point(x=5, y=5))), _EMPTY, TEXTS)
