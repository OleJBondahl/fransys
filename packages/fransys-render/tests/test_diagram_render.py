"""The diagram box and tab drawing on hand-made records (render-0009)."""

from decimal import Decimal
from xml.etree import ElementTree as ET

from fransys_render._cable_pen import Pen
from fransys_render._diagram_boxes import box_parts, tab_outer

from fransys_model.kernel import Id
from fransys_model.layout import BoxRef, DiagramBox, DiagramLine, RoutePoint, Side, TabCell

SVG = "{http://www.w3.org/2000/svg}"
_CABLE: Id = Id(kind="item", value="c" * 32)
_OTHER: Id = Id(kind="item", value="d" * 32)
_REF = BoxRef(unit=None, item=_CABLE)
_REF_ID = _CABLE
_PEN = Pen(Decimal("2.5"), 8, 8)


def _line(cable: Id, *points: tuple[int, int]) -> DiagramLine:
    return DiagramLine(
        id=Id(kind="layout.diagram_line", value="1" * 32),
        key=("line",),
        sheet=Id(kind="layout.diagram_sheet", value="2" * 32),
        cable=cable,
        a=_REF,
        b=_REF,
        points=tuple(RoutePoint(index=i, x=x, y=y) for i, (x, y) in enumerate(points)),
        text_x=0,
        text_y=0,
        produced_by="t",
    )


def _tab(side: Side, y: int = 40) -> TabCell:
    return TabCell(index=0, line=_CABLE, side=side, y=y, text_width=13)


def _box(tab: TabCell) -> DiagramBox:
    return DiagramBox(
        id=Id(kind="layout.diagram_box", value="3" * 32),
        key=("box",),
        sheet=Id(kind="layout.diagram_sheet", value="2" * 32),
        subject=_REF,
        dashed=False,
        x=100,
        y=16,
        width=64,
        height=48,
        tabs=(tab,),
        produced_by="t",
    )


def test_an_east_tab_reaches_the_nearest_point_of_its_cable_at_its_y():
    line = _line(_CABLE, (232, 40), (190, 40), (190, 90))
    assert tab_outer(164, _tab(Side.E), [line]) == 190


def test_a_west_tab_reaches_the_nearest_point_on_the_west():
    line = _line(_CABLE, (20, 40), (80, 40), (80, 90))
    assert tab_outer(100, _tab(Side.W), [line]) == 80


def test_another_cables_point_does_not_count():
    assert tab_outer(164, _tab(Side.E), [_line(_OTHER, (190, 40))]) is None


def test_a_point_at_another_y_does_not_count():
    assert tab_outer(164, _tab(Side.E), [_line(_CABLE, (190, 41))]) is None


def _rects(svg: str) -> list[ET.Element]:
    return list(ET.fromstring(f'<g xmlns="{SVG[1:-1]}">{svg}</g>').iter(SVG + "rect"))  # noqa: S314 -- own output


def test_the_tab_rectangle_reaches_the_line_and_the_text_sits_inside():
    box = _box(_tab(Side.E))
    svg = box_parts(_PEN, box, ("-U1",), (_line(_CABLE, (188, 40)),), {(_CABLE, _REF_ID): "-X1"})
    tab = _rects(svg)[1]
    assert tab.get("width") == _PEN.mm(24)
    assert "-X1" in svg


def test_a_tab_with_no_line_point_falls_back_to_its_text_and_two_pads():
    box = _box(_tab(Side.E))
    tab = _rects(box_parts(_PEN, box, ("-U1",), (), {}))[1]
    assert tab.get("width") == _PEN.mm(13 + 8)
