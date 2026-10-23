"""The house label height in G (CORE-TEXTS A, model-0319)."""

from typing import TYPE_CHECKING

from fransys_model.derive import mm_per_division
from fransys_model.derive.print_sizes import house_text_height_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.layout import SheetFormat

__all__ = ["label_height"]


def label_height(model: Model, sheet: SheetFormat) -> int:
    """The house label height in G: its millimetres over one grid division of `sheet` (E10)."""
    return round(house_text_height_mm(model) / mm_per_division(model, sheet))
