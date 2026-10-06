"""`stages.texts.place_texts`: D3's placer on hand-built `Space` and anchors, no pipeline.

One text size, 30 by 7, and one slot anchor, x 40..60, y 20..27, whose tag candidates are
the W home `_W` (x 10..40, y 20..27), a step down (y 27..34), a step up (y 13..20), and so
on, then the E side from x 60. Each test states the one Edit to the placer or the table that
makes it fail.
"""

import pytest
from samples import hid

from fransys_layout.geometry import Box, Facing, LayoutError, Point
from fransys_layout.stages.space import Run, Shape, Space
from fransys_layout.stages.texts.candidates import DEFAULT_TABLE, TextKind, stub_anchor
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
    """D3's core: W and E both free, the tag stands W, the table's first. UNDO: the TAG row's
    mirror side put before its own, and the tag stands E."""
    placed, findings = place_texts((_tag(),), _EMPTY, DEFAULT_TABLE)
    assert _boxes(placed) == [_W]
    assert findings == ()


def test_a_blocked_home_moves_the_tag_one_step_along_its_side_before_the_other_side() -> None:
    """D3: the nearest step first, then the opposite side. UNDO: the TAG row's own-side steps
    cut to the home step alone, so a blocked home falls to the mirror side before the step
    down, and the tag stands E."""
    blocker = Shape(owner=_G, box=Box(x=12, y=18, width=4, height=6))  # on _W, clear of _W_DOWN
    placed, _ = place_texts((_tag(),), Space(shapes=(blocker,)), DEFAULT_TABLE)
    assert _boxes(placed) == [_W_DOWN]


def test_with_nothing_free_the_first_candidate_stands_with_a_finding() -> None:
    """D3: none free, the first candidate stands, flagged, with `LABEL_UNPLACED`."""
    wall = Shape(owner=None, box=Box(x=-100, y=-100, width=300, height=300))
    placed, findings = place_texts((_tag(),), Space(shapes=(wall,)), DEFAULT_TABLE)
    assert placed == (PlacedText(kind=TextKind.TAG, handle=_F, slot="", box=_W, unplaced=True),)
    assert [(f.code, f.subjects, f.message) for f in findings] == [
        (LABEL_UNPLACED, (_F,), "no free place beside the slot")
    ]


def test_a_tag_whose_near_steps_are_all_blocked_takes_a_step_past_them() -> None:
    """S20 F3: a band across both sides' five near steps (y 6..41) leaves the tag its third
    step down on the home side, y 41, free and reported clean. UNDO: the TAG row cut back to its
    two near sides, and the tag stands on `_W`, flagged, with `LABEL_UNPLACED`."""
    band = Shape(owner=None, box=Box(x=-100, y=6, width=300, height=35))
    placed, findings = place_texts((_tag(),), Space(shapes=(band,)), DEFAULT_TABLE)
    assert _boxes(placed) == [Box(x=10, y=41, width=30, height=7)]
    assert not placed[0].unplaced
    assert findings == ()


def test_a_reference_is_placed_before_a_tag_that_would_take_its_one_place() -> None:
    """S15's kind order: the reference first, though the tag comes first in position and in
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
    placed, findings = place_texts((_tag(), reference), _EMPTY, DEFAULT_TABLE)
    assert [(one.kind, one.box) for one in placed] == [
        (TextKind.REFERENCE, Box(x=10, y=25, width=30, height=7)),
        (TextKind.TAG, _W_UP),
    ]
    assert findings == ()


def test_within_one_priority_the_owners_position_orders_the_texts() -> None:
    """D3's key: two tags on one slot, the owner further left first, whatever the handles."""
    left = _tag(function=_G, position=Point(x=0, y=50))
    right = _tag(function=_F, position=Point(x=8, y=0))
    placed, _ = place_texts((right, left), _EMPTY, DEFAULT_TABLE)
    assert [(one.handle, one.box) for one in placed] == [(_G, _W), (_F, _W_DOWN)]


def test_a_text_may_stand_on_its_own_functions_keepout_and_not_on_anothers() -> None:
    """D2 and S11: Room grows the owner's keep-out over its text's first candidate, and that
    keep-out does not block it; another function's does. UNDO: `own` dropped from the
    placer's shape filter, and the first case moves too. The keep-out covers every candidate,
    the steps past a vertical marker box (S20 F3) included, so another's leaves none free."""
    keepout = Box(x=0, y=-50, width=100, height=200)
    own = place_texts((_tag(),), Space(shapes=(Shape(owner=_F, box=keepout),)), DEFAULT_TABLE)
    other = place_texts((_tag(),), Space(shapes=(Shape(owner=_G, box=keepout),)), DEFAULT_TABLE)
    assert [(one.box, one.unplaced) for one in own[0]] == [(_W, False)]
    assert other[0][0].unplaced


def test_another_owners_lane_blocks_a_text_and_its_own_does_not() -> None:
    """D1's Lanes: a closed cover of another port's lane is refused, an own lane is not."""
    lane = Shape(owner=_G_PORT, box=Box(x=20, y=0, width=0, height=22))  # meets _W, not _W_DOWN
    blocked, _ = place_texts((_tag(),), _EMPTY, DEFAULT_TABLE, lanes=(lane,))
    own, _ = place_texts((_tag(own=(_F, _G_PORT)),), _EMPTY, DEFAULT_TABLE, lanes=(lane,))
    assert _boxes(blocked) == [_W_DOWN]
    assert _boxes(own) == [_W]


def test_a_route_run_blocks_through_the_interior_and_not_flush() -> None:
    """D2 P2: a run along the box's bottom edge touches, one through it crosses."""
    flush, _ = place_texts((_tag(),), _EMPTY, DEFAULT_TABLE, runs=(Run(0, 27, 50, 27),))
    across, _ = place_texts((_tag(),), _EMPTY, DEFAULT_TABLE, runs=(Run(0, 24, 50, 24),))
    assert _boxes(flush) == [_W]
    assert _boxes(across) == [_W_DOWN]


def test_a_fallback_blocks_the_texts_placed_after_it() -> None:
    """Every placed box blocks the next, an unplaced one's too: the reference stands unplaced
    on x 10..40, y 25..32, so the tag cannot take its W home or the step down."""
    reference = TextToPlace(
        kind=TextKind.REFERENCE,
        handle=_G_PORT,
        position=Point(x=0, y=0),
        width=30,
        height=7,
        anchors=(Anchor(box=stub_anchor(Point(x=25, y=40)), facing=Facing.N),),
    )
    shape = Shape(owner=None, box=Box(x=10, y=30, width=30, height=5))  # on the reference only
    placed, findings = place_texts((reference, _tag()), Space(shapes=(shape,)), DEFAULT_TABLE)
    assert [(one.box, one.unplaced) for one in placed] == [
        (Box(x=10, y=25, width=30, height=7), True),
        (_W_UP, False),
    ]
    assert [f.subjects for f in findings] == [(_G_PORT,)]


def test_a_candidate_outside_the_content_box_is_not_free() -> None:
    """S18: `Space.holds` bounds every candidate to the page's content box, on top of the
    table's steps (S18, amended after 2b-6). With a content that holds `_E` but not `_W`, the
    tag skips its own W steps for the first free candidate inside, `_E`. With a content that
    holds none of its candidates, the first candidate (`_W`) stands unplaced, flagged with one
    `LABEL_UNPLACED`. UNDO: `Space.holds` returns True."""
    inside_e = Box(x=50, y=15, width=50, height=20)  # holds _E (x 60..90, y 20..27), not _W
    placed, findings = place_texts((_tag(),), Space(shapes=(), content=inside_e), DEFAULT_TABLE)
    assert _boxes(placed) == [_E]
    assert findings == ()

    nowhere = Box(x=200, y=200, width=10, height=10)  # holds none of the tag's candidates
    placed, findings = place_texts((_tag(),), Space(shapes=(), content=nowhere), DEFAULT_TABLE)
    assert placed == (PlacedText(kind=TextKind.TAG, handle=_F, slot="", box=_W, unplaced=True),)
    assert [(f.code, f.subjects, f.message) for f in findings] == [
        (LABEL_UNPLACED, (_F,), "no free place beside the slot")
    ]


def test_two_texts_with_one_kind_handle_and_slot_raise() -> None:
    """The key must order every text (D9); two with one key would fall back to input order."""
    with pytest.raises(LayoutError, match="share one kind, handle and slot"):
        place_texts((_tag(), _tag(position=Point(x=5, y=5))), _EMPTY, DEFAULT_TABLE)
