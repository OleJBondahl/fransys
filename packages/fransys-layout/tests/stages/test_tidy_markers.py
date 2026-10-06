"""D10: `clear_of_stubs` and `shift_pages` read, per page, only that page's markers.

Can-fail, checked by hand (each mutation is undone by an edit):
- UNDO 1: `slices.page_of` keying every marker on page 1 (`item.drawing_set, 1`) fails the first
  and the third test; the second still passes (page 1 keeps its stub, page 2 has none to fear).
- UNDO 2: `slices.by_key`, `tuple(group)` -> `tuple(group[:1])` (a page reads its first marker
  only) fails the second and the third test; the first has one marker per page and passes.
"""

from samples import SHEET, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LabelKind, LinkMarker, MarkerSide, PlacedLabel
from fransys_layout.stages.tidy import clear_of_stubs, shift_pages


def _tag(function: int, page: int, box: Box) -> PlacedLabel:
    return PlacedLabel(
        kind=LabelKind.TAG,
        subject=hid("function", function),
        slot="tag",
        drawing_set=1,
        page=page,
        box=box,
    )


def _marker(page: int, x: int) -> LinkMarker:
    """A marker at (x, 200) on `page`, its box above: a stub runs up from y 200 to 112."""
    return LinkMarker(
        connection=hid("conductor", 9),
        port=hid("port", 92),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=page,
        at=Point(x=x, y=200),
        box=Box(x=x - 24, y=100, width=48, height=12),
        partner_page=0,
        star="off",
    )


TAG_BOX = Box(x=72, y=150, width=48, height=8)


def test_a_stub_on_page_two_moves_no_tag_on_page_one() -> None:
    # the stub at x 96 runs through the tag E of the symbol (72..120) on page 2 only
    plans = (page_plan(("a",)), page_plan(("a",), number=2))
    pages = [
        ((placed(1, x=64, y=160),), (_tag(1, 1, TAG_BOX),)),
        ((placed(2, x=64, y=160, page=2),), (_tag(2, 2, TAG_BOX),)),
    ]
    found = clear_of_stubs(plans, pages, (_marker(2, 96),), SHEET)
    assert [labels[0].box for _, labels in found] == [TAG_BOX, Box(x=8, y=150, width=48, height=8)]


def test_a_page_reads_all_its_own_markers_wherever_they_stand_among_the_runs() -> None:
    # page 1's stub at x 96 (its second marker, after page 2's) crosses its tag; page 2's marker
    # at x 500 crosses nothing; the result cannot depend on the order of the markers, only on
    # which ones the page is given
    plans = (page_plan(("a",)), page_plan(("a",), number=2))
    pages = [
        ((placed(1, x=64, y=160),), (_tag(1, 1, TAG_BOX),)),
        ((placed(2, x=64, y=160, page=2),), (_tag(2, 2, TAG_BOX),)),
    ]
    markers = (_marker(1, 300), _marker(2, 500), _marker(1, 96))
    found = clear_of_stubs(plans, pages, markers, SHEET)
    assert [labels[0].box for _, labels in found] == [Box(x=8, y=150, width=48, height=8), TAG_BOX]


def test_a_shift_of_page_one_moves_only_page_ones_markers() -> None:
    # page 1's label pokes 20 left of the content box: the page moves right by whole grids
    plans = (page_plan(("a",)), page_plan(("a",), number=2))
    pages = [
        ((placed(1, x=64, y=160),), (_tag(1, 1, Box(x=-20, y=150, width=48, height=8)),)),
        ((placed(2, x=64, y=160, page=2),), (_tag(2, 2, TAG_BOX),)),
    ]
    first, other, second = _marker(1, 300), _marker(2, 500), _marker(1, 96)
    moved_pages, _, markers = shift_pages(plans, pages, (first, other, second), SHEET)
    dx = moved_pages[0][1][0].box.x + 20
    assert dx > 0
    assert moved_pages[1] == pages[1]
    assert [m.at.x for m in markers] == [300 + dx, 500, 96 + dx]
    assert markers[1] == other


HOUSE_TEXT_GAP = 8  # one wiring grid, written out so a probe on the constant bites


def _shifted_tag_x(x: int) -> int:
    plans = (page_plan(("a",)),)
    pages = [((placed(1, x=64, y=160),), (_tag(1, 1, Box(x=x, y=150, width=48, height=8)),))]
    moved, _, _ = shift_pages(plans, pages, (), SHEET)
    return moved[0][1][0].box.x


def test_a_text_flush_at_the_frame_is_moved_to_the_text_gap() -> None:
    # layout-0104 frame gap: a text inside the content box but touching its edge is a defect
    assert _shifted_tag_x(0) >= HOUSE_TEXT_GAP
    assert _shifted_tag_x(3) >= HOUSE_TEXT_GAP


def test_a_text_already_a_gap_from_the_frame_stays() -> None:
    assert _shifted_tag_x(HOUSE_TEXT_GAP) == HOUSE_TEXT_GAP
