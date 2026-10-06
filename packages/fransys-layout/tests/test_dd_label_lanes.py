"""Golden-fix part 3: a slot label never stands in a neighbour's port column, and an unplaceable
label is no obstacle to the router.

Rule 1 (`stages/labels.py::place_slot_labels`): the outward lane of every OTHER function's port
(the stretch `space.lane` gives a route through that function's keep-out box, one step past it)
is a blocker for a slot label. Commit 178d126 made a strip terminal's point label `-X01:L2:1` 34
wide against a 32 terminal pitch, so it stood over the next terminal's column: that terminal's
wire detoured through the label's own column and its edge could not start (ROUTE_FAILED).
Rule 2 (`stages/pagerun.py::finish_page`): a label `place_slot_labels` flagged `unplaced` (it
fits nowhere and sits at its slot's home) is left out of the `reserved` boxes handed to `route`,
so a wire crossing it is a lint warning, never a ROUTE_FAILED error.
"""

from typing import TYPE_CHECKING

import pytest
from dd_chain_fixtures import TERMINAL, build, design
from samples import NO_HINTS, PROFILE, SHEET, drawn, hid, placed

from fransys_layout.geometry import Box, overlaps
from fransys_layout.stages import (
    LabelKind,
    LabelRequest,
    PlacedLabel,
    pagerun,
    place_slot_labels,
)
from fransys_layout.stages.labels import SlotFrame
from fransys_model.derive import drawing_text
from fransys_model.derive.designation import terminal_designation
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_layout.stages.route import PageRoom

# A tag just wider than the 32 G tag slot: it ends one unit past its own symbol's keep-out box
WIDE = "-K123456"


def test_a_slot_label_is_kept_out_of_another_functions_port_column() -> None:
    """Function 1's tag would end past x = 104, the column of function 2's `in` port (facing N,
    keep-out top at y = 80): the lane runs from y = 80 to y = 72, and the label moves off it."""
    # UNDO: stages/labels.py, `place_slot_labels`: the `lanes` tuple built from `_lanes(one)`
    # (the label then stands at its slot's home, over the column, and this test fails)
    neighbour = placed(2, x=104, y=96, name="b")
    first = placed(1, x=64, y=72, name="a")
    request = LabelRequest(kind=LabelKind.TAG, subject=hid("function", 1), slot="tag", text=WIDE)
    labels, _ = place_slot_labels(
        (request,),
        (first, neighbour),
        (drawn(1), drawn(2)),
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    (label,) = labels
    lane = Box(x=103, y=71, width=2, height=10)  # port (104, 80) N, one step past the keep-out top
    assert not overlaps(label.box, lane)
    home = Box(x=80, y=68, width=33, height=8)  # the tag slot's home: it does cover the lane
    assert overlaps(home, lane)


def test_a_slot_label_may_stand_in_its_own_functions_port_column() -> None:
    """Only OTHER functions' lanes block: function 1's label is not moved by function 1's own."""
    only = placed(1, x=104, y=96, name="a")
    request = LabelRequest(kind=LabelKind.TAG, subject=hid("function", 1), slot="tag", text="-K1")
    (label,), findings = place_slot_labels(
        (request,), (only,), (drawn(1),), frame=SlotFrame(content=None, profile=PROFILE)
    )
    assert label.box == Box(x=120, y=92, width=13, height=8)
    assert findings == ()


def test_a_label_the_stage_found_no_place_for_is_flagged_and_still_placed() -> None:
    """`unplaced` marks the label a `LABEL_UNPLACED` finding names; a placed one is not marked."""
    # UNDO: stages/labels.py, `place_slot_labels`: `unplaced=one.unplaced` in the
    # `PlacedLabel(...)` call
    only = placed(1, x=104, y=96, name="a")
    request = LabelRequest(kind=LabelKind.TAG, subject=hid("function", 1), slot="tag", text="-K1")
    everywhere = (Box(x=0, y=0, width=1000, height=1000),)
    (free,), none = place_slot_labels(
        (request,), (only,), (drawn(1),), frame=SlotFrame(content=None, profile=PROFILE)
    )
    (stuck,), one = place_slot_labels(
        (request,),
        (only,),
        (drawn(1),),
        occupied=everywhere,
        frame=SlotFrame(content=None, profile=PROFILE),
    )
    assert none == ()
    assert not free.unplaced
    assert [f.code for f in one] == ["LABEL_UNPLACED"]
    assert stuck.unplaced
    assert stuck.box == free.box  # still placed, at the slot's home


def test_finish_page_leaves_an_unplaced_label_out_of_the_routers_reserved_boxes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`route` is given the placed label's box and not the unplaced one's."""
    # UNDO: stages/pagerun.py, `finish_page`: the `if not label.unplaced` filter of `held`
    seen: dict[str, tuple[Box, ...]] = {}

    def spy(
        _connections: object, _net_groups: object, _placed: object, _drawn: object, room: PageRoom
    ) -> tuple[tuple, tuple]:
        seen["reserved"] = room.reserved
        return (), ()

    monkeypatch.setattr(pagerun, "route", spy)
    good = PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", 1),
        slot="tag",
        drawing_set=1,
        page=1,
        box=Box(x=120, y=92, width=13, height=8),
    )
    stuck = PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", 2),
        slot="tag",
        drawing_set=1,
        page=1,
        box=Box(x=304, y=92, width=34, height=8),
        unplaced=True,
    )
    inputs = pagerun.PageInputs(
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
    pagerun.finish_page(
        pagerun.PageState((placed(1, x=104, y=96), placed(2, x=288, y=96)), (good, stuck), ()),
        (drawn(1), drawn(2)),
        inputs,
        references=(),
    )
    assert seen["reserved"] == (good.box,)


# Handle order follows the authoring keys, so whether the L3 wire reaches the strip before the L2
# label is placed depends on the strip's name: at 5c5badc these six names give ROUTE_FAILED and
# CONNECTION_NOT_DRAWN (the other six of X01..X12 route by luck of their order).
@pytest.mark.parametrize("strip", ["X02", "X04", "X05", "X07", "X09", "X12"])
def test_a_three_phase_feed_through_a_strip_routes_all_three_phases(
    strip: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q1 (3-pole contactor) feeds three terminals of strip `strip` (L1..L3, point 1) from its
    poles 2, 4 and 6; the point text is forced to the full form `-X..:L2:1`, wider than the
    terminal pitch (D12 amended prints the short "L2:1" in such a run, which needs no guard: this
    test keeps the guard exercised with a wide text). All three wires are drawn, whatever the
    strip is called."""
    monkeypatch.setattr(
        drawing_text,
        "run_point_text",
        lambda model, function: terminal_designation(model, functions(model)[function].item),
    )
    # UNDO: stages/pagerun.py, `finish_page`: the `if not label.unplaced` filter of `held`
    # (the lanes of `place_slot_labels` alone do not route this fixture: the label then
    # fits nowhere, is flagged and reserved; without the lanes this fixture still routes)
    parts, d = design()
    c1, g = d.location("C1", "Cabinet"), d.group("SUP", "Supply")
    q1 = d.item("DEMO-CTR-3P-24", tag="Q1", at=c1, group=g)
    feed_strip, strip_out = d.strip("X1", at=c1), d.strip(strip, at=c1)
    feed = [feed_strip.terminal(TERMINAL, ph, group=g) for ph in ("L1", "L2", "L3")]
    out = [strip_out.terminal(TERMINAL, ph, index=1, group=g) for ph in ("L1", "L2", "L3")]
    wire = d.wiring(colour="BK", gauge="2.5")
    main = q1.fn("main")
    for i in range(3):
        wire(feed[i].inner, main[str(2 * i + 1)])
        wire(main[str(2 * i + 2)], out[i].inner)
    codes = [f.code for f in build(parts, d).findings]
    assert "ROUTE_FAILED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes
