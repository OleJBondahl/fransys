"""External outlines: one closed dashed polyline per `layout.external_outline` record."""

import re
from decimal import Decimal

from fransys_render._outlines import outlines_group
from fransys_render._style import style_block

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import (
    DrawingSet,
    ExternalOutline,
    Page,
    PageRole,
    SheetFormat,
)
from fransys_model.vocab import Item

_ORIGIN = Origin(
    file="packages/fransys-render/tests/test_external_outlines.py", line=1, note="invented"
)

_POLYLINE_RE = re.compile(r'<polyline class="external-outline" points="([^"]*)"/>')


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_an_external_outline_is_a_closed_dashed_five_point_polyline():
    drawing_set_key = ("drawing_set", "ext1")
    drawing_set = DrawingSet(
        id=make_id(DrawingSet, drawing_set_key),
        key=drawing_set_key,
        location=None,
        unit=None,
        number=1,
        produced_by="test",
    )
    sheet_key = ("sheet_format", "ext1")
    sheet = SheetFormat(
        id=make_id(SheetFormat, sheet_key),
        key=sheet_key,
        name="ext1",
        width_mm=300,
        height_mm=200,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=280,
        content_height_mm=160,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )
    page_key = ("page", "ext1")
    page = Page(
        id=make_id(Page, page_key),
        key=page_key,
        drawing_set=drawing_set.id,
        number=1,
        role=PageRole.CONTROL,
        sheet_format=sheet.id,
        groups=(),
        produced_by="test",
    )
    item_key = ("item", "ext1")
    item = Item(
        id=make_id(Item, item_key),
        key=item_key,
        part=None,
        parent=None,
        position=None,
        tag="X1",
        description="Invented",
        unit=None,
    )
    outline_key = ("external_outline", "ext1")
    outline = ExternalOutline(
        id=make_id(ExternalOutline, outline_key),
        key=outline_key,
        item=item.id,
        page=page.id,
        x=-20,
        y=-8,
        width=300,
        height=40,
        produced_by="test",
    )
    model = _model(drawing_set, sheet, page, item, outline)

    (points,) = _POLYLINE_RE.findall(outlines_group(model, page))
    assert len(points.split(" ")) == 5
    assert points.split(" ")[0] == points.split(" ")[-1]

    css = style_block()
    assert ".external-outline { stroke: black; fill: none;" in css
    assert ".external-outline { stroke-dasharray: 4,1; }" in css
    assert ".unit-boundary { stroke-dasharray: 4,1,0.25,1; }" in css
