"""The measured widths (D8): hand-made values, no model and no engine."""

from samples import PROFILE, drawn, hid, placed

from fransys_layout.geometry import Box, text_width
from fransys_layout.stages import ColumnWidth, LabelKind, LabelRequest
from fransys_layout.stages.sizing import grown, label_boxes, placed_widths

FUNCTION = hid("function", 1)


def _request(kind: LabelKind, subject, slot: str, text: str) -> LabelRequest:
    return LabelRequest(kind=kind, subject=subject, slot=slot, text=text)


def test_a_tag_and_a_marking_are_measured_at_their_slots_and_a_wire_label_is_not() -> None:
    """The tag goes by the function, the marking by the owner of its port; the wire is skipped.

    The through symbol's tag slot is E, so the box starts at the slot's anchor x (16) and is as
    wide as its text, one text height high.
    """
    # UNDO: stages/sizing.py:label_boxes, `owner.get(request.subject)` -> `request.subject`
    #     (the marking's port is taken for a function and finds no slot)
    requests = (
        _request(LabelKind.TAG, FUNCTION, "tag", "K1"),
        _request(LabelKind.MARKING, hid("port", 11), "marking.in", "13"),
        _request(LabelKind.WIRE, hid("conductor", 1), "", "W1"),
    )

    found = label_boxes((drawn(1),), requests, PROFILE)

    height = PROFILE.text_height
    assert found == {
        FUNCTION: [
            ("tag", Box(x=16, y=-4, width=text_width("K1", height=height), height=height)),
            ("marking.in", Box(x=16, y=-16, width=text_width("13", height=height), height=height)),
        ]
    }


def test_a_keep_out_grows_over_the_measured_box_of_a_long_tag() -> None:
    """A tag wider than the keep-out's right side (x 48) pushes the keep-out's right edge out."""
    # UNDO: stages/sizing.py:grown, `grow_keepout(one.geometry, [...])` -> `one.geometry`
    #     (no keep-out grows)
    text = "a long tag text"
    (one,) = grown((drawn(1),), (_request(LabelKind.TAG, FUNCTION, "tag", text),), PROFILE)

    keepout = one.geometry.keepout
    assert keepout.x + keepout.width == 16 + text_width(text, height=PROFILE.text_height)
    assert keepout.x + keepout.width > 48


def test_a_column_is_as_wide_as_its_placed_extent_plus_the_gap_when_that_is_more() -> None:
    """Column `a` has two placements (keep-out 56 wide at x -8) and a gap of 48; `b` has none."""
    # UNDO: stages/sizing.py:placed_widths, `max(one.width, actual.get(...))` -> `one.width`
    #     (the estimate always wins)
    narrow = ColumnWidth(column=("invented", "a"), width=10)
    wide = ColumnWidth(column=("invented", "b"), width=500)
    placements = (placed(1, x=104, y=0, name="a"), placed(2, x=112, y=48, name="a"))

    found = placed_widths((narrow, wide), placements, 48)

    # extent: from 104 - 8 = 96 to 112 - 8 + 56 = 160, so 64, plus the gap 48
    assert found == (ColumnWidth(column=("invented", "a"), width=112), wide)
