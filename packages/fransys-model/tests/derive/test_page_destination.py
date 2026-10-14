"""`derive.page_destination`: the named-destination label of a drawing page (OVERVIEW O21).

Hand-built drawing sets and pages: two sets that both hold a page 3 must get different labels.
"""

from fransys_model.derive import page_destination
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import DrawingSet, Page, PageRole

_ORIGIN = Origin(
    file="packages/fransys-model/tests/derive/test_page_destination.py", line=1, note="invented"
)


def _set(key: str, number: int) -> DrawingSet:
    return DrawingSet(
        id=make_id(DrawingSet, ("drawing_set", key)),
        key=("drawing_set", key),
        location=None,
        number=number,
        produced_by="test",
    )


def _page(key: str, drawing_set: DrawingSet, number: int) -> Page:
    return Page(
        id=make_id(Page, ("page", key)),
        key=("page", key),
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by="test",
    )


def test_pages_of_two_drawing_sets_get_their_own_set_and_page_labels():
    ds1, ds2 = _set("ds1", 1), _set("ds2", 2)
    p1, p2 = _page("p1", ds1, 3), _page("p2", ds2, 3)
    draft = Draft()
    draft.extend((ds1, ds2, p1, p2), origin=_ORIGIN)
    m = freeze(draft)
    assert page_destination(m, p1) == "p1.3"
    assert page_destination(m, p2) == "p2.3"
