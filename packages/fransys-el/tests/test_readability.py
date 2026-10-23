"""`fransys_el.readability` on hand-built Drawings: one known answer per count (el-0043)."""

from fransys_el import readability

from electrical_symbols import MARKER_TURNED, marker_symbol
from fransys_layout.core import Box, Size
from fransys_layout.drawing import Drawing, DrawnMarker, DrawnSymbol, DrawnText, DrawnWire
from fransys_model.kernel import make_id
from fransys_model.layout import Page
from fransys_model.vocab import Unit

_UNIT = make_id(Unit, ("u", "cab"))


def _page(name: str):
    return make_id(Page, ("p", name))


def _drawing(*, symbols=(), wires=(), markers=(), texts=()) -> Drawing:
    return Drawing(Size(100, 100), symbols, wires, markers, texts, (), "t")


def _wire(name: str, *points: tuple[int, int]) -> DrawnWire:
    return DrawnWire(id=name, points=points, style="w")


def _text(x: int, y: int, w: int = 10, h: int = 4, text: str = "T") -> DrawnText:
    return DrawnText(text=text, box=Box(x, y, w, h), kind="k", anchor="NW")


def _one(drawing: Drawing):
    page = _page("a")
    (row,) = readability({page: drawing}, {page: _UNIT}).pages
    assert row.page == page
    return row


def test_empty_drawing_gives_the_zero_report():
    row = _one(_drawing())
    assert (row.symbols, row.markers, row.wire_crossings, row.wire_bends) == (0, 0, 0, 0)
    assert row.fill_percent == 0
    assert (row.wire_length_g, row.struck_labels, row.text_overlaps) == (0, 0, 0)
    assert readability({}, {}).pages == ()


def test_membership_counts_symbols_and_the_drawing_markers_field_is_not_read():
    symbol = DrawnSymbol(id="s", key="k", x=0, y=0, orient="R0")
    marker = DrawnMarker(id="m", key="k", x=0, y=0, side="N", texts=(), tint=None)
    row = _one(_drawing(symbols=(symbol, symbol), markers=(marker,)))
    assert (row.symbols, row.markers) == (2, 0)


def test_crossings_bends_and_length():
    wires = (_wire("a", (0, 50), (100, 50)), _wire("b", (50, 0), (50, 80), (70, 80)))
    row = _one(_drawing(wires=wires))
    assert (row.wire_crossings, row.wire_bends, row.wire_length_g) == (1, 1, 100 + 80 + 20)


def test_overlapping_text_gives_text_overlap_count():
    row = _one(_drawing(texts=(_text(0, 0), _text(5, 2), _text(50, 50))))
    assert row.text_overlaps == 1


def test_a_wire_through_a_text_strikes_it():
    row = _one(_drawing(wires=(_wire("a", (0, 2), (30, 2)),), texts=(_text(10, 0),)))
    assert row.struck_labels == 1


def test_pages_keep_the_order_given():
    first, second = _page("b"), _page("a")
    got = readability({first: _drawing(), second: _drawing()}, {}).pages
    assert tuple(row.page for row in got) == (first, second)


def test_markers_count_the_symbols_of_the_marker_keys_not_a_constant():
    cell = DrawnSymbol(id="c", key="relay", x=0, y=0, orient="R0")
    flag = DrawnSymbol(id="f", key=marker_symbol("tag"), x=0, y=0, orient="R0")
    turned = DrawnSymbol(id="t", key=MARKER_TURNED, x=0, y=0, orient="R0")
    row = _one(_drawing(symbols=(cell, flag, turned, flag)))
    assert (row.symbols, row.markers) == (4, 3)


def test_fill_percent_and_unit_are_on_the_row():
    body = DrawnSymbol(id="s", key="k", x=0, y=0, orient="R0", outline=Box(0, 0, 50, 100))
    row = _one(_drawing(symbols=(body,)))
    assert (row.fill_percent, row.unit) == (50, _UNIT)
    page = _page("b")
    assert readability({page: _drawing()}, {}).pages[0].unit is None
