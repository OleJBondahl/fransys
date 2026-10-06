"""Pure `Decimal` number formatting and grid-to-mm conversion (D5): no `float` anywhere."""

from decimal import Decimal


def format_decimal(value: Decimal) -> str:
    """`value` with no exponent and no trailing zeros; any zero becomes `0`."""
    normalized = value.normalize()
    exponent = normalized.as_tuple().exponent
    if isinstance(exponent, int) and exponent > 0:
        normalized = normalized.quantize(Decimal(1))
    if normalized == 0:
        return "0"
    return f"{normalized:f}"


def grid_to_mm(origin_mm: int, g: int, module_mm: Decimal) -> Decimal:
    """One grid coordinate `g` (0.125 M each) converted to an absolute mm position (D5)."""
    return Decimal(origin_mm) + Decimal(g) * module_mm / 8
