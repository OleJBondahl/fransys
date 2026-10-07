"""S18, S20: a cross-reference whose first candidate lies on a marker box.

Hand-made values, no model. Function 1, the through symbol, stands alone on its page at
(104, 96); its `tag` slot is on the E side at (16, 0), its slot box from y -4. Its
cross-reference goes through `finish_page`'s second slot call, whose `occupied` holds the
page's link markers' boxes (`PageState.markers`; a C21 run's box is one, S20). With no marker
the reference stands at its first candidate, one text height below the tag, at the slot's x.
No fixture of the layout or root suites has a marker box over a cross-reference's first
candidate (measured over every `finish_page` call), so this page is the test's own.
"""

from dataclasses import replace

from samples import NO_HINTS, PROFILE, SHEET, drawn, hid, placed

from fransys_layout.geometry import Box, Point, translate
from fransys_layout.stages import (
    LabelKind,
    LabelRequest,
    LinkMarker,
    MarkerSide,
    PlacedLabel,
)
from fransys_layout.stages.pagerun import PageInputs, PageState, finish_page

_REFERENCE = LabelRequest(
    kind=LabelKind.CROSS_REFERENCE, subject=hid("function", 1), slot="tag", text="p1:3A"
)
_INPUTS = PageInputs(
    functions=(),
    connections=(),
    net_groups=(),
    groups=(),
    locations=(),
    units=(),
    hints=NO_HINTS,
    profile=PROFILE,
    sheet=SHEET,
    top_headroom_lanes=0,
    bottom_headroom_lanes=0,
)


def _marker(box: Box) -> LinkMarker:
    """A marker whose box is `box`, its port at the box's west edge (a stub of no length)."""
    return LinkMarker(
        connection=hid("conductor", 9),
        port=hid("port", 11),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=box.x, y=box.y + box.height // 2),
        box=box,
        partner_page=0,
        star="off",
    )


def _reference(markers: tuple[LinkMarker, ...]) -> tuple[PlacedLabel, tuple[object, ...]]:
    """The page finished with `markers`: its one cross-reference and the findings."""
    _, labels, findings = finish_page(
        PageState((placed(1, x=104, y=96),), (), markers),
        (drawn(1),),
        _INPUTS,
        references=(_REFERENCE,),
    )
    (label,) = labels
    return label, findings


def test_a_cross_reference_whose_first_candidate_lies_on_a_marker_box_takes_the_next_one() -> None:
    """A marker's box over the first candidate sends the reference one step further down its
    side, the table's next candidate, which is free; no finding."""
    # UNDO: stages/pagerun.py `finish_page`: drop the `drawn_shapes(markers)` boxes from the
    #     second slot call's `occupied`: the reference stands on the marker's box
    first, found = _reference(())
    assert not first.unplaced
    assert found == ()
    assert (first.box.x, first.box.y) == (104 + 16, 96 - 4 + PROFILE.text_height)  # the premise
    label, findings = _reference((_marker(first.box),))
    assert not label.unplaced
    assert findings == ()
    assert label.box == translate(first.box, dx=0, dy=PROFILE.text_height)


def test_a_power_ends_undrawn_box_does_not_hold_the_reference_but_its_symbol_does() -> None:
    """layout-0138: the keep-out of the second slot call is the page's drawn ink, as the tables
    read it; a power end draws its symbol, never its marker box."""
    # UNDO: stages/pagerun.py `finish_page`: put the markers' boxes and every power symbol's
    #     body and lead back in `occupied` (a power end's undrawn box holds the reference again)
    first, _ = _reference(())
    far = Point(x=2000, y=2000)  # the symbol stands far from the reference
    undrawn = replace(_marker(first.box), at=far, symbol="ground", symbol_text="")
    label, findings = _reference((undrawn,))
    assert findings == ()
    assert label.box == first.box, "a box nobody draws holds nothing"
    drawn_end = replace(undrawn, symbol="", symbol_text="")
    assert _reference((drawn_end,))[0].box != first.box, "the same box drawn does hold it"
