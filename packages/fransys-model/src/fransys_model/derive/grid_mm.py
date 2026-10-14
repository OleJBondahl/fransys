"""One grid coordinate to an absolute millimetre position (render and pdf both place by it).

Reached as `fransys_model.derive.grid_mm.<name>`, never re-exported from `derive/__init__.py`.
"""

from decimal import Decimal

from fransys_model.derive.text_width import G_PER_MODULE

__all__ = ["grid_to_mm"]


def grid_to_mm(origin_mm: int, g: int | Decimal, module_mm: Decimal) -> Decimal:
    """One grid coordinate `g` (0.125 M each) converted to an absolute mm position."""
    return Decimal(origin_mm) + Decimal(g) * module_mm / G_PER_MODULE
