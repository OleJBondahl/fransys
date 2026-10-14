"""Unit boundaries (dash-dot) and external outlines (dashed): one closed polyline per record."""

from itertools import chain
from typing import TYPE_CHECKING

from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.order import drawn_on_page
from fransys_model.layout import ExternalOutline, Outline, sheet_format_of

from ._numbers import format_decimal

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import Page, SheetFormat


def _point_mm(sheet: SheetFormat, x: int, y: int) -> str:
    """One point converted to an `"x,y"` mm pair, mirroring `_markers._point_mm`."""
    x_mm = grid_to_mm(sheet.content_x_mm, x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)
    return f"{format_decimal(x_mm)},{format_decimal(y_mm)}"


def _rect_polyline(sheet: SheetFormat, css: str, record: Outline | ExternalOutline) -> str:
    """A closed `<polyline class="css">` round the record's rectangle (mirrors `_box_glyph`)."""
    min_x, min_y = record.x, record.y
    max_x, max_y = min_x + record.width, min_y + record.height
    vertices = ((min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y))
    closed = (*vertices, vertices[0])
    points = " ".join(_point_mm(sheet, x, y) for x, y in closed)
    return f'<polyline class="{css}" points="{points}"/>'


def _outline_glyph(sheet: SheetFormat, outline: Outline) -> str:
    """The unit boundary: one closed `<polyline>`, dash-dot (`unit-boundary`)."""
    return _rect_polyline(sheet, "unit-boundary", outline)


def _external_outline_glyph(sheet: SheetFormat, outline: ExternalOutline) -> str:
    """The external item's outline: one closed `<polyline>`, dashed (`external-outline`)."""
    return _rect_polyline(sheet, "external-outline", outline)


def outlines_group(model: Model, page: Page) -> str:
    """Every `layout.outline` of `page` by place, then every `layout.external_outline`."""
    sheet = sheet_format_of(model, page.sheet_format)
    outlines = (_outline_glyph(sheet, o) for o in drawn_on_page(model, Outline, page))
    externals = (
        _external_outline_glyph(sheet, o) for o in drawn_on_page(model, ExternalOutline, page)
    )
    return "".join(chain(outlines, externals))
