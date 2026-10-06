"""Route polylines: one `<polyline>` per `layout.route` on a page (D8), ordered by `id` (D11)."""

from typing import TYPE_CHECKING

from fransys_model.layout import Route, page_slice, sheet_format_of

from ._numbers import format_decimal, grid_to_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import Page, SheetFormat


def routes_on_page(model: Model, page: Page) -> tuple[Route, ...]:
    """Every `layout.route` drawn on `page`, ordered by `id` (D11)."""
    return page_slice(model, Route, page)


def _point_mm(sheet: SheetFormat, x: int, y: int) -> str:
    """One route point converted to an `"x,y"` mm pair (D5), each coordinate formatted."""
    x_mm = grid_to_mm(sheet.content_x_mm, x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)
    return f"{format_decimal(x_mm)},{format_decimal(y_mm)}"


def routes_group(model: Model, page: Page) -> str:
    """Every route on `page` as one `<polyline>` each, in `id` order (D8, D11)."""
    sheet = sheet_format_of(model, page.sheet_format)
    return "".join(
        '<polyline class="wire" points="'
        + " ".join(_point_mm(sheet, point.x, point.y) for point in route.points)
        + '"/>'
        for route in routes_on_page(model, page)
    )
