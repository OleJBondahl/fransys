"""Pure `Decimal` number formatting: no `float` anywhere."""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.derive.grid_mm import grid_to_mm
from fransys_model.derive.print_sizes import font_size_mm

if TYPE_CHECKING:
    from fransys_model.layout import SheetFormat


def format_decimal(value: Decimal) -> str:
    """`value` with no exponent and no trailing zeros; any zero becomes `0`."""
    normalized = value.normalize()
    exponent = normalized.as_tuple().exponent
    if isinstance(exponent, int) and exponent > 0:
        normalized = normalized.quantize(Decimal(1))
    if normalized == 0:
        return "0"
    return f"{normalized:f}"


def printed_font_mm(text_height_mm: Decimal) -> Decimal:
    """The font size in mm (to 0.0001) of a text with capitals `text_height_mm` high."""
    return font_size_mm(text_height_mm).quantize(Decimal("0.0001"))


def point_mm(sheet: SheetFormat, x: int, y: int) -> str:
    """One grid point as an `"x,y"` mm pair on `sheet`, each coordinate formatted."""
    x_mm = grid_to_mm(sheet.content_x_mm, x, sheet.module_mm)
    y_mm = grid_to_mm(sheet.content_y_mm, y, sheet.module_mm)
    return f"{format_decimal(x_mm)},{format_decimal(y_mm)}"
