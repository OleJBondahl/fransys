"""R2 and R4 (layout deep dive, designer's rulings), on invented pages.

R2: a tag a marker's stub runs through moves to the mirror side of its own symbol.
R4: one item tag per item per page, on its main view; a separately drawn function of the
same item on that page carries none.

Can-fail, checked by hand: with `clear_of_stubs` returning `pages` unchanged the first test
fails; with `one_item_tag` returning `requests` unchanged the third test fails.
"""

import dataclasses

from samples import SHEET, column, function_spec, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import (
    Cell,
    KindRoles,
    LabelKind,
    LabelRequest,
    LinkMarker,
    MarkerSide,
    PlacedLabel,
)
from fransys_layout.stages.tags import one_item_tag
from fransys_layout.stages.tidy import clear_of_stubs


def _tag(box: Box) -> PlacedLabel:
    return PlacedLabel(
        kind=LabelKind.TAG, subject=hid("function", 1), slot="tag", drawing_set=1, page=1, box=box
    )


def _stub(x: int) -> LinkMarker:
    """A marker at (x, 200) whose box sits above, so its stub runs up from y 200 to 112."""
    return LinkMarker(
        connection=hid("conductor", 9),
        port=hid("port", 92),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        at=Point(x=x, y=200),
        box=Box(x=x - 24, y=100, width=48, height=12),
        partner_page=0,
        star="off",
    )


def _tidied(label: PlacedLabel, stub_x: int) -> Box:
    pages = [((placed(1, x=64, y=160),), (label,))]
    ((_, (moved,)),) = clear_of_stubs((page_plan(("a",)),), pages, (_stub(stub_x),), SHEET)
    return moved.box


def test_a_tag_a_stub_runs_through_moves_to_the_mirror_side_of_its_symbol() -> None:
    # the symbol's body spans x 56..72; the tag E of it, 72..120, and the stub at x 96
    assert _tidied(_tag(Box(x=72, y=150, width=48, height=8)), 96) == Box(
        x=8, y=150, width=48, height=8
    )


def test_a_tag_no_stub_runs_through_stays() -> None:
    box = Box(x=72, y=150, width=48, height=8)
    assert _tidied(_tag(box), 160) == box


def test_a_channel_row_on_its_items_view_page_carries_no_item_tag() -> None:
    view = dataclasses.replace(function_spec(1), function=hid("item", 1))  # the item's box
    channel = function_spec(2)
    channel = dataclasses.replace(
        channel, item=hid("item", 1), kind="plc_channel", roles=KindRoles(plc_channel=True)
    )  # the same item's channel
    columns = (
        dataclasses.replace(column("a", ()), cells=(Cell(function=hid("item", 1), index=0),)),
        column("b", (2,)),
    )
    requests = tuple(
        LabelRequest(kind=LabelKind.TAG, subject=subject, slot="tag", text="=PLC+C1-DO1")
        for subject in (hid("item", 1), hid("function", 2))
    )
    kept = one_item_tag(columns, (view, channel), requests)
    assert [r.subject for r in kept] == [hid("item", 1)]


def test_a_contact_of_an_item_view_keeps_its_item_tag() -> None:
    """layout-0123: a contact stands apart from its box and prints the item tag like any contact."""
    view = dataclasses.replace(function_spec(1), function=hid("item", 1))
    contact = dataclasses.replace(function_spec(2), item=hid("item", 1))  # a contact_no
    columns = (
        dataclasses.replace(column("a", ()), cells=(Cell(function=hid("item", 1), index=0),)),
        column("b", (2,)),
    )
    requests = tuple(
        LabelRequest(kind=LabelKind.TAG, subject=subject, slot="tag", text="-M1")
        for subject in (hid("item", 1), hid("function", 2))
    )
    kept = one_item_tag(columns, (view, contact), requests)
    assert [r.subject for r in kept] == [hid("item", 1), hid("function", 2)]
