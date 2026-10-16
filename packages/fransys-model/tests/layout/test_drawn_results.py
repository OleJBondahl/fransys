"""The drawn kinds: a symbol, a wire and a page freeze and read back, in a tuple of their own.

Can-fail: drop a record from `DRAWN_KINDS` (the tuple test), add one to `DERIVED_KINDS`
(the apart test), or drop a field (the read-back test).
"""

from typing import Any

from fransys_model.kernel import Draft, Model, Origin, freeze, make_id
from fransys_model.layout import (
    DERIVED_KINDS,
    DRAWN_KINDS,
    DrawingSet,
    DrawnPage,
    DrawnPoint,
    DrawnSymbol,
    DrawnWire,
    Orientation,
    Page,
    PageRole,
    derived_layout_ids,
    layout_of,
)

_ORIGIN = Origin(file="test_drawn_results.py", line=1, note="fixture")
_PAGE = make_id(Page, ("page", "p1"))


def _sheet_pages() -> tuple[DrawingSet, Page]:
    """The drawing set and the page `p1` the drawn records point at."""
    set_key = ("set", "1")
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, set_key),
        key=set_key,
        location=None,
        number=1,
        produced_by="test",
    )
    return drawing_set, Page(
        id=_PAGE,
        key=("page", "p1"),
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.POWER,
        sheet_format=None,
        groups=(),
        produced_by="test",
    )


def _symbol() -> DrawnSymbol:
    key = ("drawn", "symbol", "k1")
    return DrawnSymbol(
        id=make_id(DrawnSymbol, key),
        key=key,
        symbol="marker.turned",
        page=_PAGE,
        x=4,
        y=8,
        orient=Orientation.R90,
        produced_by="test",
        n=2,
        lengths=frozendict({"y": 6}),
        offsets=frozendict({"a": 3}),
        leads=("a",),
        slots=frozendict({"tag": "-K1"}),
        tint="red",
        owner="x1",
        muted=True,
    )


def _wire() -> DrawnWire:
    key = ("drawn", "wire", "w1")
    return DrawnWire(
        id=make_id(DrawnWire, key),
        key=key,
        style="trunk",
        page=_PAGE,
        points=(DrawnPoint(x=0, y=0), DrawnPoint(x=0, y=4), DrawnPoint(x=6, y=4)),
        produced_by="test",
        lanes=3,
    )


def _page() -> DrawnPage:
    key = ("drawn", "page", "p1")
    return DrawnPage(
        id=make_id(DrawnPage, key), key=key, page=_PAGE, kind=PageRole.POWER, produced_by="test"
    )


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_the_three_drawn_kinds_are_one_tuple_apart_from_the_derived_kinds() -> None:
    assert set(DRAWN_KINDS) == {DrawnSymbol, DrawnWire, DrawnPage}
    assert not set(DRAWN_KINDS) & set(DERIVED_KINDS)


def test_a_drawn_symbol_a_wire_and_a_page_read_back_unchanged() -> None:
    symbol, wire, page = _symbol(), _wire(), _page()
    model = _freeze(*_sheet_pages(), symbol, wire, page)
    assert layout_of(model, DrawnSymbol)[symbol.id] == symbol
    assert layout_of(model, DrawnWire)[wire.id] == wire
    assert layout_of(model, DrawnPage)[page.id] == page


def test_derived_ids_of_the_drawn_kinds_name_these_records_only() -> None:
    model = _freeze(*_sheet_pages(), _symbol(), _wire(), _page())
    expected = tuple(sorted((_symbol().id, _wire().id, _page().id)))
    assert derived_layout_ids(model, kinds=DRAWN_KINDS) == expected
    assert not set(expected) & set(derived_layout_ids(model))
