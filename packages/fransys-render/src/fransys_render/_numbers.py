"""Pure `Decimal` number formatting: no `float` anywhere."""

from decimal import Decimal

from fransys_model.derive.print_sizes import font_size_mm


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
