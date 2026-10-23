"""One grid coordinate to an absolute millimetre position (render and pdf both place by it).

Reached as `fransys_model.derive.grid_mm.<name>`, never re-exported from `derive/__init__.py`.
"""

from decimal import Decimal

__all__ = ["grid_to_mm"]


def grid_to_mm(origin_mm: int, g: int | Decimal, mm_per_division: Decimal) -> Decimal:
    """One grid coordinate `g` converted to an absolute mm position (`derive.mm_per_division`)."""
    return Decimal(origin_mm) + Decimal(g) * mm_per_division
