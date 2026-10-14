"""Route polylines: one `<polyline>` per `layout.route` on a page, drawn in `wire_run` order."""

from typing import TYPE_CHECKING

from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.order import wire_run
from fransys_model.layout import Route, page_slice, sheet_format_of

from ._numbers import format_decimal

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import Page, SheetFormat


def routes_on_page(model: Model, page: Page) -> tuple[Route, ...]:
    """Every `layout.route` drawn on `page`, in `id` order (the drawn order is `wire_run`)."""
    return page_slice(model, Route, page)


def _point_mm(sheet: SheetFormat, x: int, y: int) -> str:
    """One route point converted to an `"x,y"` mm pair, each coordinate formatted."""
    x_mm = grid_to_mm(sheet.content_x_mm, x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)
    return f"{format_decimal(x_mm)},{format_decimal(y_mm)}"


def routes_group(model: Model, page: Page) -> str:
    """Every route on `page` as one `<polyline>` each, upper end first, in `wire_run` order."""
    sheet = sheet_format_of(model, page.sheet_format)
    runs = sorted(
        wire_run([(point.x, point.y) for point in route.points])
        for route in routes_on_page(model, page)
    )
    return "".join(
        '<polyline class="wire" points="' + " ".join(_point_mm(sheet, x, y) for x, y in run) + '"/>'
        for run in runs
    )
