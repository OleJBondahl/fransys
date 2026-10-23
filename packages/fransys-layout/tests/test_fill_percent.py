"""`fill_percent`: the share of a page's content box that its placed ink spans (el-0043 amended)."""

from fransys_layout.core import Box, Size
from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnText, DrawnWire, fill_percent

_AREA = Size(100, 50)


def _drawing(*, symbols=(), wires=(), texts=(), area=_AREA) -> Drawing:
    return Drawing(area, symbols, wires, (), texts, (), "t")


def _symbol(box: Box | None) -> DrawnSymbol:
    return DrawnSymbol(id="s", key="k", x=0, y=0, orient="R0", outline=box)


def test_an_empty_page_reads_zero() -> None:
    assert fill_percent(_drawing()) == 0
    assert fill_percent(_drawing(symbols=(_symbol(None),))) == 0


def test_the_ink_extent_is_the_share_of_the_area() -> None:
    assert fill_percent(_drawing(symbols=(_symbol(Box(0, 0, 50, 25)),))) == 25
    two = (_symbol(Box(0, 0, 10, 10)), _symbol(Box(40, 20, 10, 10)))
    assert fill_percent(_drawing(symbols=two)) == 50 * 30 * 100 // (100 * 50)


def test_a_wire_and_a_text_count_as_ink() -> None:
    wire = DrawnWire(id="w", points=((0, 0), (100, 0), (100, 25)), style="w")
    assert fill_percent(_drawing(wires=(wire,))) == 50
    text = DrawnText(text="T", box=Box(0, 0, 100, 10), kind="k", anchor="NW")
    assert fill_percent(_drawing(texts=(text,))) == 20


def test_ink_beyond_the_area_is_clipped() -> None:
    assert fill_percent(_drawing(symbols=(_symbol(Box(-20, -20, 500, 500)),))) == 100
