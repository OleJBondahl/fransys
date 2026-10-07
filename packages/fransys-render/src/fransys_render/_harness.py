"""Harness lines and connector boxes: drawn from the layout records as given (render-0010)."""

from typing import TYPE_CHECKING, Any
from xml.sax.saxutils import escape

from fransys_model.derive import connector_box_lines, line_designation
from fransys_model.derive.drawing_text import port_marking
from fransys_model.layout import (
    ConnectorBox,
    DrawingSet,
    HarnessLine,
    layout_of,
    page_slice,
    profile_of,
    sheet_format_of,
)

from ._constants import ASCENT_RATIO
from ._numbers import format_decimal, grid_to_mm
from ._routes import _point_mm

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import BoxCell, Page, SheetFormat


def _x_mm(sheet: SheetFormat, x: int) -> Decimal:
    return grid_to_mm(sheet.content_x_mm, x, sheet.module_mm)


def _y_mm(sheet: SheetFormat, y: int) -> Decimal:
    return grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)


def _text(
    x_mm: Decimal, baseline_mm: Decimal, font_mm: Decimal, value: str, *, middle: bool = False
) -> str:
    anchor = ' text-anchor="middle"' if middle else ""
    return (
        f'<text class="label" x="{format_decimal(x_mm)}" y="{format_decimal(baseline_mm)}" '
        f'font-size="{format_decimal(font_mm)}"{anchor}>{escape(value)}</text>'
    )


def _line_element(
    model: Model, sheet: SheetFormat, step: int, line: HarnessLine, unit: Id[Any] | None
) -> str:
    points = " ".join(_point_mm(sheet, point.x, point.y) for point in line.points)
    element = f'<polyline class="harness-line" points="{points}"/>'
    designation = line_designation(model, line.harness, line.branch, unit=unit)
    if not designation:
        return element
    font_mm = grid_to_mm(0, step, sheet.module_mm)
    baseline = _y_mm(sheet, line.text_y) - font_mm / 2 + font_mm * ASCENT_RATIO
    return element + _text(_x_mm(sheet, line.text_x), baseline, font_mm, designation, middle=True)


def harness_lines_group(model: Model, page: Page) -> str:
    """Every harness line on `page` as one `<polyline>` each, in `id` order, with its text."""
    sheet = sheet_format_of(model, page.sheet_format)
    step = profile_of(model).text_height
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    return "".join(
        _line_element(model, sheet, step, line, unit)
        for line in page_slice(model, HarnessLine, page)
    )


def _rect(css_class: str, sheet: SheetFormat, box: ConnectorBox | BoxCell) -> str:
    return (
        f'<rect class="{css_class}" x="{format_decimal(_x_mm(sheet, box.x))}" '
        f'y="{format_decimal(_y_mm(sheet, box.y))}" '
        f'width="{format_decimal(grid_to_mm(0, box.width, sheet.module_mm))}" '
        f'height="{format_decimal(grid_to_mm(0, box.height, sheet.module_mm))}"/>'
    )


def _cell_element(model: Model, sheet: SheetFormat, step: int, cell: BoxCell) -> str:
    font_mm = grid_to_mm(0, step, sheet.module_mm)
    top = _y_mm(sheet, cell.y) + (grid_to_mm(0, cell.height, sheet.module_mm) - font_mm) / 2
    centre = _x_mm(sheet, cell.x) + grid_to_mm(0, cell.width, sheet.module_mm) / 2
    name = port_marking(model, cell.port)
    baseline = top + font_mm * ASCENT_RATIO
    return _rect("connector-cell", sheet, cell) + _text(
        centre, baseline, font_mm, name, middle=True
    )


def _box_element(
    model: Model, sheet: SheetFormat, step: int, box: ConnectorBox, unit: Id[Any] | None
) -> str:
    lines = connector_box_lines(model, box.function, unit=unit)
    font_mm = grid_to_mm(0, step, sheet.module_mm)
    texts = "".join(
        _text(
            _x_mm(sheet, slot.x),
            _y_mm(sheet, slot.y) + font_mm * ASCENT_RATIO,
            font_mm,
            lines[slot.index],
        )
        for slot in box.texts
        if slot.index < len(lines)
    )
    cells = "".join(_cell_element(model, sheet, step, cell) for cell in box.cells)
    return _rect("connector-box", sheet, box) + texts + cells


def connector_boxes_group(model: Model, page: Page) -> str:
    """Every connector box on `page`: its rectangle, text lines and pin cells, in `id` order."""
    sheet = sheet_format_of(model, page.sheet_format)
    step = profile_of(model).text_height
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    return "".join(
        _box_element(model, sheet, step, box, unit) for box in page_slice(model, ConnectorBox, page)
    )
