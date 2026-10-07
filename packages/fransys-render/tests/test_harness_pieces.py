"""Harness lines and connector boxes drawn from hand-made layout records (render-0010)."""

from dataclasses import replace
from decimal import Decimal
from xml.etree import ElementTree as ET

from _cable_build import World
from fransys_render import pages
from fransys_render._constants import ASCENT_RATIO
from fransys_render._numbers import format_decimal, grid_to_mm

from fransys_model.derive import connector_box_lines
from fransys_model.kernel import make_id
from fransys_model.layout import (
    BoxCell,
    BoxText,
    ConnectorBox,
    DrawingSet,
    HarnessLine,
    Page,
    PageRole,
    RoutePoint,
    default_profile,
    default_sheet_format,
)
from fransys_model.vocab import Function, Port

SVG = "{http://www.w3.org/2000/svg}"
_MODULE = Decimal("2.5")
_TEXT_H = default_profile().text_height


def _mm(origin: int, g: int) -> str:
    return format_decimal(grid_to_mm(origin, g, _MODULE))


def _model_with_boxes(specs, *, marking=None):
    """One page, harness `WH` from A1 to B1, a line, and a box per spec on A1's then B1's function.

    `specs`: (x, y, w, h, with_cells). Returns the model, the page, the box functions, A1's ports.
    """
    world = World()
    harness = world.item("wh", "WH")
    cable = world.cable("w1", "W1", ("BK",), parent=harness)
    _, a = world.device("a1", "A1", "1", "2")
    _, b = world.device("b1", "B1", "1")
    world.core("c1", cable, (a["1"], b["1"]), 1)
    key_set, key_page, key_line = ("ds",), ("pg",), ("line",)
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, key_set), key=key_set, location=None, number=1, produced_by="t"
    )
    page = Page(
        id=make_id(Page, key_page),
        key=key_page,
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=None,
        groups=(),
        produced_by="t",
    )
    line = HarnessLine(
        id=make_id(HarnessLine, key_line),
        key=key_line,
        page=page.id,
        harness=harness,
        branch=1,
        points=(RoutePoint(index=0, x=0, y=0), RoutePoint(index=1, x=8, y=0)),
        text_x=4,
        text_y=-2,
        produced_by="t",
    )
    world.records.extend((drawing_set, page, line))
    functions = [make_id(Function, (key, "f")) for key in ("a1", "b1")]
    for n, (function, (x, y, w, h, cells)) in enumerate(zip(functions, specs, strict=False)):
        key = ("box", str(n))
        world.records.append(
            ConnectorBox(
                id=make_id(ConnectorBox, key),
                key=key,
                page=page.id,
                function=function,
                x=x,
                y=y,
                width=w,
                height=h,
                texts=(BoxText(index=0, x=x + 1, y=y + 1),),
                cells=_cells((a, b)[n], x, y) if cells else (),
                produced_by="t",
            )
        )
    if marking is not None:
        world.records[:] = [
            replace(r, marking=marking) if isinstance(r, Port) and r.name == "1" else r
            for r in world.records
        ]
    return world.model(), page, functions, a


def _cells(ports, x, y):
    return tuple(
        BoxCell(index=i, port=port, x=x + 1, y=y + 3 + 2 * i, width=4, height=2)
        for i, port in enumerate(ports.values())
    )


def _svg(model, page) -> ET.Element:
    del page
    (svg,) = pages(model).values()
    return ET.fromstring(svg)  # noqa: S314 -- the SVG is this package's own output


def _of(root, tag, css):
    return [e for e in root.iter(SVG + tag) if css in e.get("class", "").split()]


def test_a_harness_line_is_a_polyline_of_its_points_in_its_own_class() -> None:
    model, page, _, _ = _model_with_boxes(())
    root = _svg(model, page)
    (line,) = _of(root, "polyline", "harness-line")
    sheet = default_sheet_format()
    expected = " ".join(
        f"{_mm(sheet.content_x_mm, x)},{_mm(sheet.content_y_mm, y)}" for x, y in ((0, 0), (8, 0))
    )
    assert line.get("points") == expected
    assert _of(root, "polyline", "wire") == []


def test_the_harness_line_is_drawn_twice_as_thick_as_a_wire() -> None:
    model, page, _, _ = _model_with_boxes(())
    style = next(_svg(model, page).iter(SVG + "style")).text or ""
    assert ".harness-line { stroke: black; fill: none; stroke-width: 0.5; }" in style
    assert (
        ".wire, .marker, .unit-boundary { stroke: black; fill: none; stroke-width: 0.25; }" in style
    )


def test_a_line_prints_its_derived_designation_centred_on_its_text_fields() -> None:
    model, page, _, _ = _model_with_boxes(())
    sheet = default_sheet_format()
    (text,) = _of(_svg(model, page), "text", "label")
    font = grid_to_mm(0, _TEXT_H, _MODULE)
    centre = grid_to_mm(sheet.content_y_mm, -2, _MODULE)
    assert text.text == "-WH"
    assert text.get("text-anchor") == "middle"
    assert text.get("x") == _mm(sheet.content_x_mm, 4)
    assert text.get("y") == format_decimal(centre - font / 2 + font * ASCENT_RATIO)


def test_a_pin_cell_prints_the_part_marking_when_it_differs_from_the_name() -> None:
    model, page, _, _ = _model_with_boxes(
        ((10, 10, 8, 8, False), (30, 10, 8, 8, True)), marking="L1"
    )
    root = _svg(model, page)
    names = [t.text for t in _of(root, "text", "label") if t.text not in ("-WH", "-A1", "-B1")]
    assert names == ["L1"]


def test_a_box_is_its_rectangle_with_its_text_lines_from_derive() -> None:
    model, page, fns, _ = _model_with_boxes(((10, 10, 8, 8, False),))
    root = _svg(model, page)
    sheet = default_sheet_format()
    (rect,) = _of(root, "rect", "connector-box")
    assert rect.get("x") == _mm(sheet.content_x_mm, 10)
    assert rect.get("y") == _mm(sheet.content_y_mm, 10)
    assert rect.get("width") == _mm(0, 8)
    assert rect.get("height") == _mm(0, 8)
    lines = connector_box_lines(model, fns[0])
    assert lines == ("-A1",)
    texts = [t.text for t in _of(root, "text", "label") if t.text != "-WH"]
    assert texts == list(lines)


def test_a_box_with_no_cells_draws_none_and_one_with_cells_draws_each() -> None:
    model, page, _, ports = _model_with_boxes(((10, 10, 8, 8, False), (30, 10, 8, 8, True)))
    root = _svg(model, page)
    assert len(_of(root, "rect", "connector-box")) == 2
    cells = _of(root, "rect", "connector-cell")
    assert len(cells) == 1  # B1 has one port, A1's box holds no cell
    sheet = default_sheet_format()
    assert cells[0].get("x") == _mm(sheet.content_x_mm, 31)
    names = [
        t
        for t in _of(root, "text", "label")
        if t.get("text-anchor") == "middle" and t.text != "-WH"
    ]
    assert [t.text for t in names] == ["1"]
    assert names[0].get("x") == format_decimal(
        grid_to_mm(sheet.content_x_mm, 31, _MODULE) + grid_to_mm(0, 4, _MODULE) / 2
    )
    assert len(ports) == 2


def test_touching_plug_and_interface_boxes_are_both_drawn_as_given() -> None:
    """HL11: two records share the edge x=18; render merges and moves nothing."""
    model, page, _, _ = _model_with_boxes(((10, 10, 8, 8, False), (18, 10, 8, 8, False)))
    sheet = default_sheet_format()
    rects = _of(_svg(model, page), "rect", "connector-box")
    xs = sorted(r.get("x") for r in rects)
    assert xs == sorted([_mm(sheet.content_x_mm, 10), _mm(sheet.content_x_mm, 18)])
    left = next(r for r in rects if r.get("x") == _mm(sheet.content_x_mm, 10))
    assert Decimal(left.get("x")) + Decimal(left.get("width")) == Decimal(
        next(r for r in rects if r is not left).get("x")
    )
