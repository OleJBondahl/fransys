"""WP10 acceptance skeletons and unit tests: `stages.labels` (ROADMAP WP10, labels.md 6.7)."""

import dataclasses

import pytest
from samples import PROFILE, drawn, hid, placed

from fransys_layout.geometry import (
    Box,
    Facing,
    LayoutError,
    Orientation,
    Point,
    SlotGeometry,
    SymbolGeometry,
    overlaps,
)
from fransys_layout.stages import (
    LabelKind,
    LabelRequest,
    place_slot_labels,
)
from fransys_layout.stages.labels import SlotFrame
from fransys_layout.stages.texts.place_texts import LABEL_UNPLACED
from fransys_model.kernel import Severity

# A tag just wider than the 32 G tag slot (33 G): two of them still meet across a gap
WIDE = "-K123456"


def _tag(number: int, text: str) -> LabelRequest:
    return LabelRequest(kind=LabelKind.TAG, subject=hid("function", number), slot="tag", text=text)


def test_a_short_tag_sits_in_its_slot() -> None:
    """`-K1` is narrower than its 32 G slot: the label box is its measured text (13 G) from
    the slot's anchor, so the tag stands close to its symbol (designer's ruling)."""
    labels, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    (label,) = labels
    assert label.box == Box(x=120, y=92, width=13, height=8)
    assert (label.kind, label.slot, label.page) == (LabelKind.TAG, "tag", 1)
    assert findings == ()


def test_a_long_tag_grows_away_from_the_symbol_not_over_it() -> None:
    """A tag wider than its slot is widened along the slot side and never covers the body."""
    labels, _ = place_slot_labels(
        (_tag(1, "-K1234567890"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    body = Box(x=96, y=80, width=16, height=32)
    assert labels[0].box.width > 32
    assert not overlaps(labels[0].box, body)


def test_a_label_that_fits_nowhere_is_reported_and_still_placed() -> None:
    """Symbols all round the tagged one leave no room on either side, nor at the steps past a
    vertical marker box (S20 F3): a finding, the text is not shrunk, and the label is still
    placed, marked unplaced."""
    around = [(x, y) for x in (80, 104, 128) for y in (32, 64, 96, 128, 160) if (x, y) != (104, 96)]
    functions = (
        placed(1, x=104, y=96),
        *(placed(n, x=x, y=y, name=f"n{n}") for n, (x, y) in enumerate(around, start=2)),
    )
    labels, findings = place_slot_labels(
        (_tag(1, "-K1234567890"),),
        functions,
        tuple(drawn(n) for n in range(1, len(functions) + 1)),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert len(labels) == 1
    assert labels[0].unplaced
    assert labels[0].box.width > 32
    assert [f.code for f in findings] == [LABEL_UNPLACED]
    assert findings[0].subjects == (hid("function", 1),)


def test_a_marking_label_uses_the_slot_of_its_symbol_port() -> None:
    """Model port 11 is drawn at `in`: its marking goes to slot `marking.in`, source the port."""
    request = LabelRequest(
        kind=LabelKind.MARKING, subject=hid("port", 11), slot="marking.in", text="13"
    )
    labels, findings = place_slot_labels(
        (request,),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    (label,) = labels
    assert (label.kind, label.subject, label.slot) == (
        LabelKind.MARKING,
        hid("port", 11),
        "marking.in",
    )
    assert label.box == Box(x=120, y=80, width=8, height=8)
    assert findings == ()


def test_a_cross_reference_label_sits_below_the_tag() -> None:
    """The second call gets the first call's boxes as `occupied` and stacks under the tag."""
    functions = (placed(1, x=104, y=96),)
    tags, _ = place_slot_labels(
        (_tag(1, "-K1"),), functions, (drawn(1),), frame=SlotFrame(content=None, profile=PROFILE)
    )
    request = LabelRequest(
        kind=LabelKind.CROSS_REFERENCE, subject=hid("function", 1), slot="tag", text="/2.5"
    )
    labels, findings = place_slot_labels(
        (request,),
        functions,
        (drawn(1),),
        occupied=tuple(label.box for label in tags),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    (label,) = labels
    assert label.kind is LabelKind.CROSS_REFERENCE
    assert (label.box.x, label.box.y) == (tags[0].box.x, tags[0].box.y + PROFILE.text_height)
    assert findings == ()


def test_a_label_in_its_own_symbols_keepout_box_is_not_an_overlap() -> None:
    """A slot lies inside its symbol's keep-out box by definition: no finding for that."""
    _, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert findings == ()


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


def test_a_west_slot_grows_to_the_left_so_it_never_covers_the_body() -> None:
    """The anchor edge of a W slot is its right edge: a wide text grows away from the symbol."""
    labels, _ = place_slot_labels(
        (_tag(1, "-K1234567890"),),
        (_at(1, _symbol(W_TAG), x=200, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    # 49 G of text, its right edge kept at the slot's anchor, 200 - 16.
    assert labels[0].box == Box(x=135, y=92, width=49, height=8)


def test_a_labels_page_is_the_page_its_function_is_placed_on() -> None:
    """A `PlacedLabel` takes the drawing set and page of the placement, never of the request."""
    labels, _ = place_slot_labels(
        (_tag(1, "-K1"),),
        (dataclasses.replace(placed(1, x=104, y=96), page=3),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert (labels[0].drawing_set, labels[0].page) == (1, 3)


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


def test_an_unblocked_label_does_not_move() -> None:
    """The twin of the move: an `occupied` box beside the slot changes nothing."""
    labels, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=120, y=104, width=32, height=8),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=120, y=92, width=13, height=8)
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


def test_a_west_slot_moves_down_and_reflects_to_the_east_side() -> None:
    """The same rule as the east slot, mirrored: the reflection lands right of the body."""
    moved, _ = place_slot_labels(
        (_tag(1, "-K1"),),
        (_at(1, _symbol(W_TAG), x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=56, y=92, width=32, height=8),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    reflected, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (_at(1, _symbol(W_TAG), x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=40, y=80, width=64, height=32),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert moved[0].box == Box(x=75, y=100, width=13, height=8)
    assert reflected[0].box == Box(x=120, y=92, width=13, height=8)
    assert findings == ()


def test_a_candidate_outside_the_own_keepout_box_is_dropped_not_clamped() -> None:
    """Free space below the symbol is not offered: the moves stay beside the symbol."""
    labels, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=0, y=64, width=400, height=64),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=120, y=92, width=13, height=8)
    assert [f.code for f in findings] == [LABEL_UNPLACED]
    # The code is stable and the severity is the one docs/design/labels.md 6.7 names.
    assert (findings[0].code, findings[0].severity) == ("LABEL_UNPLACED", Severity.WARNING)


def test_a_candidate_inside_the_own_keepout_box_is_offered() -> None:
    """The twin: the same band four grid units shorter leaves the first offset free."""
    labels, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=0, y=64, width=400, height=36),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=120, y=100, width=13, height=8)
    assert findings == ()


def test_a_label_placed_earlier_in_the_call_blocks_the_next_one() -> None:
    """Two symbols whose keep-out boxes clear each other, whose tags do not."""
    functions = (_at(1, _symbol(E_TAG), x=104, y=96), _at(2, _symbol(W_TAG), x=184, y=96))
    labels, findings = place_slot_labels(
        (_tag(1, WIDE), _tag(2, WIDE)),
        functions,
        (drawn(1), drawn(2)),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert [label.box for label in labels] == [
        Box(x=120, y=92, width=33, height=8),
        Box(x=135, y=100, width=33, height=8),
    ]
    assert findings == ()


def test_a_label_alone_in_the_call_keeps_its_slot() -> None:
    """The twin: without the first request the second label sits in its own slot."""
    functions = (_at(1, _symbol(E_TAG), x=104, y=96), _at(2, _symbol(W_TAG), x=184, y=96))
    labels, findings = place_slot_labels(
        (_tag(2, WIDE),),
        functions,
        (drawn(1), drawn(2)),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=135, y=92, width=33, height=8)
    assert findings == ()


# --- what `place_slot_labels` raises --------------------------------------------------


def test_placed_functions_of_two_pages_raise() -> None:
    """`place_slot_labels` runs per page, so a mixed set is the engine assembling it wrongly."""
    with pytest.raises(LayoutError, match="more than one page"):
        place_slot_labels(
            (_tag(1, "-K1"),),
            (placed(1, x=104, y=96), placed(2, x=200, y=96, page=2)),
            (drawn(1), drawn(2)),
            frame=SlotFrame(content=None, profile=PROFILE),
        )


def test_placed_functions_of_one_page_do_not_raise() -> None:
    """The twin: two functions of one page are the normal input."""
    labels, _ = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96), placed(2, x=200, y=96)),
        (drawn(1), drawn(2)),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert len(labels) == 1


def test_one_function_placed_twice_raises() -> None:
    """A page draws a function once; a terminal on two pages is two pages, not two boxes."""
    with pytest.raises(LayoutError, match="placed twice"):
        place_slot_labels(
            (_tag(1, "-K1"),),
            (placed(1, x=104, y=96), placed(1, x=200, y=96)),
            (drawn(1),),
            frame=SlotFrame(content=None, profile=PROFILE),
        )


def test_a_placed_function_that_is_not_drawn_raises() -> None:
    """Every placed function must be in `drawn`: that is where a marking finds its port."""
    with pytest.raises(LayoutError, match="not among the drawn functions"):
        place_slot_labels(
            (_tag(1, "-K1"),),
            (placed(1, x=104, y=96), placed(2, x=200, y=96)),
            (drawn(1),),
            frame=SlotFrame(content=None, profile=PROFILE),
        )


def test_a_subject_that_is_no_placed_function_and_no_port_raises() -> None:
    """A request for a function this page does not draw is an assembly fault, not a finding."""
    with pytest.raises(LayoutError, match="neither a placed function nor a port"):
        place_slot_labels(
            (_tag(9, "-K9"),),
            (placed(1, x=104, y=96),),
            (drawn(1),),
            frame=SlotFrame(content=None, profile=PROFILE),
        )


def test_a_marking_subject_that_is_a_port_of_a_placed_function_does_not_raise() -> None:
    """The twin: the same lookup, through the `DrawnPort`s of the placed function."""
    request = LabelRequest(
        kind=LabelKind.MARKING, subject=hid("port", 11), slot="marking.in", text="13"
    )
    labels, _ = place_slot_labels(
        (request,),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].subject == hid("port", 11)


def test_a_slot_the_symbol_does_not_define_raises() -> None:
    """No slot, no preferred box: there is nothing to fall back to and nothing to guess."""
    with pytest.raises(LayoutError, match="does not define"):
        place_slot_labels(
            (_value(1, "4 mm2"),),
            (placed(1, x=104, y=96),),
            (drawn(1),),
            frame=SlotFrame(content=None, profile=PROFILE),
        )


def test_a_wire_request_given_to_place_slot_labels_raises() -> None:
    """A wire label names no slot, so it is the same fault: the symbol defines no such slot."""
    wire = LabelRequest(kind=LabelKind.WIRE, subject=hid("function", 1), slot="", text="BK 1.5")
    with pytest.raises(LayoutError, match="does not define"):
        place_slot_labels(
            (wire,),
            (placed(1, x=104, y=96),),
            (drawn(1),),
            frame=SlotFrame(content=None, profile=PROFILE),
        )


def test_a_slot_the_symbol_defines_does_not_raise() -> None:
    """The twin: the sample symbol defines `tag`."""
    labels, _ = place_slot_labels(
        (_tag(1, "-K1"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].slot == "tag"


def test_two_requests_with_one_subject_slot_and_kind_raise() -> None:
    """Two labels of one source would collide by construction and give one derived key."""
    # the placer raises it (`place_texts`), in its own words: one kind, handle and slot
    with pytest.raises(LayoutError, match="share one kind, handle and slot"):
        place_slot_labels(
            (_tag(1, "-K1"), _tag(1, "-K1 again")),
            (placed(1, x=104, y=96),),
            (drawn(1),),
            frame=SlotFrame(content=None, profile=PROFILE),
        )


def test_two_requests_of_one_subject_and_slot_with_different_kinds_do_not_raise() -> None:
    """The twin: a tag and its cross-reference share a subject and a slot, not a kind."""
    labels, _ = place_slot_labels(
        (_tag(1, "-K1"), _reference(1, "/2.5")),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert [label.kind for label in labels] == [LabelKind.CROSS_REFERENCE, LabelKind.TAG]


# --- wire labels ---------------------------------------------------------------------


# --- order ---------------------------------------------------------------------------


def test_slot_labels_do_not_depend_on_the_input_order() -> None:
    """Requests, placed, drawn and `occupied` are all shuffled: the result is equal.

    The boxes `reserve_slots` pinned here (its keep-out-bounded move order) went with it; the
    order contract stays, on D3's placer.
    """
    requests = (_tag(1, WIDE), _tag(2, WIDE), _tag(3, WIDE))
    functions = (placed(1, x=104, y=96), placed(2, x=240, y=96), placed(3, x=376, y=96))
    drawings = (drawn(1), drawn(2), drawn(3))
    occupied = (Box(x=120, y=92, width=32, height=8), Box(x=256, y=84, width=32, height=24))
    first = place_slot_labels(
        requests,
        functions,
        drawings,
        occupied=occupied,
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    second = place_slot_labels(
        requests[::-1],
        functions[::-1],
        drawings[::-1],
        occupied=occupied[::-1],
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert first == second
    assert first[1] == ()  # every tag found a free place ...
    # ... and tag 1's home (x=120, y=92), under the first `occupied` box, is not one of them
    assert Box(x=120, y=92, width=33, height=8) not in [label.box for label in first[0]]


# --- what the mutation sweep asked for -----------------------------------------------


def test_two_slots_of_one_subject_are_placed_in_slot_order() -> None:
    """`tag` before `value`, whatever order the requests came in: the first takes the box."""
    both = _symbol(
        SlotGeometry(
            slot="tag", at=Point(x=16, y=0), side=Facing.E, box=Box(x=16, y=-4, width=32, height=8)
        ),
        SlotGeometry(
            slot="value",
            at=Point(x=16, y=0),
            side=Facing.E,
            box=Box(x=16, y=-4, width=32, height=8),
        ),
        keepout=Box(x=-8, y=-16, width=56, height=32),
    )
    labels, findings = place_slot_labels(
        (_value(1, "4"), _tag(1, "-K1")),
        (_at(1, both, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert [(label.slot, label.box) for label in labels] == [
        ("tag", Box(x=120, y=92, width=13, height=8)),
        ("value", Box(x=120, y=100, width=4, height=8)),
    ]
    assert findings == ()


def test_a_cross_reference_with_nothing_occupied_still_sits_below_the_slot() -> None:
    """The offset is the slot's own, not a way around the tag box."""
    labels, findings = place_slot_labels(
        (_reference(1, "/2.5"),),
        (placed(1, x=104, y=96),),
        (drawn(1),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=120, y=100, width=13, height=8)
    assert findings == ()


def test_a_move_that_ends_flush_with_the_keepout_edge_is_offered() -> None:
    """The bound is inclusive: a box whose edge meets the keep-out edge is still inside."""
    edge = _symbol(E_TAG, keepout=Box(x=-8, y=-12, width=56, height=32))
    labels, findings = place_slot_labels(
        (_tag(1, "-K1"),),
        (_at(1, edge, x=104, y=96),),
        (drawn(1),),
        occupied=(Box(x=120, y=92, width=32, height=16),),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert labels[0].box == Box(x=120, y=84, width=13, height=8)
    assert findings == ()


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
