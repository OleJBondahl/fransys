"""A diagram tab reaches its own cable's line, or the width of its text when no line is there."""

from decimal import Decimal

from fransys_render._cable_pen import Pen
from fransys_render._constants import DIAGRAM_TAB_PAD_G
from fransys_render._diagram_boxes import _tab, tab_outer

from electrical_symbols import LIBRARY
from fransys_model.kernel import make_id
from fransys_model.layout import (
    BoxRef,
    DiagramBox,
    DiagramLine,
    DiagramSheet,
    RoutePoint,
    Side,
    TabCell,
)
from fransys_model.vocab import Item

_CABLE = make_id(Item, ("item", "cable"))
_OTHER = make_id(Item, ("item", "other"))
_PEN = Pen(LIBRARY, module_mm=Decimal("2.5"), text_height_mm=Decimal("2.5"), pad_g=2)


def _box(*, x=40, width=24) -> DiagramBox:
    return DiagramBox(
        id=make_id(DiagramBox, ("diagram_box", "b")),
        key=("diagram_box", "b"),
        sheet=make_id(DiagramSheet, ("diagram_sheet", "s")),
        subject=BoxRef(unit=None, item=make_id(Item, ("item", "box"))),
        dashed=False,
        x=x,
        y=8,
        width=width,
        height=32,
        tabs=(),
        produced_by="test",
    )


def _line(cable, xs, y) -> DiagramLine:
    box = BoxRef(unit=None, item=make_id(Item, ("item", "box")))
    return DiagramLine(
        id=make_id(DiagramLine, ("diagram_line", "l")),
        key=("diagram_line", "l"),
        sheet=make_id(DiagramSheet, ("diagram_sheet", "s")),
        cable=cable,
        a=box,
        b=box,
        points=tuple(RoutePoint(index=i, x=x, y=y) for i, x in enumerate(xs)),
        text_x=0,
        text_y=0,
        produced_by="test",
    )


def _tab_cell(side, *, line=_CABLE, y=20, text_width=10) -> TabCell:
    return TabCell(index=0, line=line, side=side, y=y, text_width=text_width)


def test_a_tab_reaches_the_nearest_point_of_its_own_line_past_the_edge() -> None:
    lines = [_line(_CABLE, [70, 90, 100], 20), _line(_OTHER, [66], 20)]
    assert tab_outer(64, _tab_cell(Side.E), lines) == 70
    lines = [_line(_CABLE, [30, 10, 0], 20)]
    assert tab_outer(40, _tab_cell(Side.W), lines) == 30


def test_a_tab_whose_line_has_no_point_at_its_height_has_no_outer_end() -> None:
    assert tab_outer(64, _tab_cell(Side.E, y=24), [_line(_CABLE, [70], 20)]) is None
    assert tab_outer(64, _tab_cell(Side.E), [_line(_OTHER, [70], 20)]) is None


def test_a_tab_with_no_line_is_its_text_width_and_two_pads_wide_on_the_outside() -> None:
    reach = 10 + 2 * DIAGRAM_TAB_PAD_G
    east = _tab(_PEN, _box(), _tab_cell(Side.E), [], "")
    assert f'x="{_PEN.mm(64)}" y="' in east
    assert f'width="{_PEN.mm(reach)}"' in east
    assert "<text" not in east
    west = _tab(_PEN, _box(), _tab_cell(Side.W), [], "A1")
    assert f'x="{_PEN.mm(40 - reach)}" y="' in west
    assert f'width="{_PEN.mm(reach)}"' in west
    assert west.endswith(">A1</text>")
