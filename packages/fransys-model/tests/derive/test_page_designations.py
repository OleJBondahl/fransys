"""A page with no `layout.membership` row and no old record draws no designation."""

from fransys_model.derive.page_titles import page_designations
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import DrawingSet, Page, PageRole


def test_a_page_with_no_membership_row_prints_no_designation() -> None:
    set_key = ("set", "1")
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, set_key), key=set_key, location=None, number=1, produced_by="test"
    )
    page_key = ("page", "p1")
    page = Page(
        id=make_id(Page, page_key),
        key=page_key,
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.POWER,
        sheet_format=None,
        groups=(),
        produced_by="test",
    )
    draft = Draft()
    draft.extend((drawing_set, page), origin=Origin(file="t.py", line=1, note="fixture"))
    assert page_designations(freeze(draft), page) == ()
