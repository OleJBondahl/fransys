"""Unit boundaries (units spec U1): one dash-dot outline per black-box unit instance."""

from typing import TYPE_CHECKING

from fransys_model.layout import Outline, page_slice, sheet_format_of

from ._numbers import format_decimal, grid_to_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import Page, SheetFormat


def _point_mm(sheet: SheetFormat, x: int, y: int) -> str:
    """One point converted to an `"x,y"` mm pair (D5), mirroring `_markers._point_mm`."""
    x_mm = grid_to_mm(sheet.content_x_mm, x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)
    return f"{format_decimal(x_mm)},{format_decimal(y_mm)}"


def _outline_glyph(sheet: SheetFormat, outline: Outline) -> str:
    """The boundary's outline: one closed `<polyline>`, four corners (mirrors `_box_glyph`)."""
    min_x, min_y = outline.x, outline.y
    max_x, max_y = min_x + outline.width, min_y + outline.height
    vertices = ((min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y))
    closed = (*vertices, vertices[0])
    points = " ".join(_point_mm(sheet, x, y) for x, y in closed)
    return f'<polyline class="unit-boundary" points="{points}"/>'


def outlines_group(model: Model, page: Page) -> str:
    """Every `layout.outline` of `page`, in id order, as a dash-dot outline."""
    sheet = sheet_format_of(model, page.sheet_format)
    return "".join(_outline_glyph(sheet, outline) for outline in page_slice(model, Outline, page))
