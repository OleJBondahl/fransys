"""`clear_of_stubs` and `shift_pages` read, per page, only that page's markers.

Can-fail, checked by hand (each mutation is undone by an edit):
- UNDO 1: `slices.page_of` keying every marker on page 1 (`item.drawing_set, 1`) fails the first
  and the third test; the second still passes (page 1 keeps its stub, page 2 has none to fear).
- UNDO 2: `slices.by_key`, `tuple(group)` -> `tuple(group[:1])` (a page reads its first marker
  only) fails the second and the third test; the first has one marker per page and passes.
"""

from samples import SHEET, hid, page_plan, placed

from fransys_layout.geometry import Box, Point
from fransys_layout.stages import LabelKind, LinkMarker, MarkerSide, PlacedLabel
from fransys_layout.stages.tidy import shift_pages


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


def test_a_shift_never_pushes_an_image_room_off_the_page() -> None:
    """A label 20 left of the content needs a 32 shift; the coil's room ends at x 1260."""
    # UNDO: stages/tidy.py:_need, drop the image room boxes from the extent
    plans = (page_plan(("a",)),)
    coil = placed(1, x=64, y=160)
    pages = [((coil,), (_tag(1, 1, Box(x=-20, y=150, width=48, height=8)),))]
    rooms = {(coil.column, coil.function): (0, 1148)}

    held, _, _ = shift_pages(plans, pages, (), SHEET, rooms)
    assert held == pages
    moved, _, _ = shift_pages(plans, pages, (), SHEET)
    assert moved[0][0][0].at.x == 64 + 32
