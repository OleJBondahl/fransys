"""The pdf's printed sizes in mm (EXACT-SIZES E3, E7, E10); `Sizes`, `sizes_of` live in derive."""

from fransys_model.derive import Sizes, sizes_of
from fransys_model.derive.print_sizes import LINE_RULE_MM, LINE_THICK_MM, LINE_THIN_MM

__all__ = ["RULE", "THICK_STROKE", "THIN_STROKE", "Sizes", "font_mm", "sizes_of"]

THIN_STROKE = f"{LINE_THIN_MM}mm"
THICK_STROKE = f"{LINE_THICK_MM}mm"
RULE = f"{LINE_RULE_MM}mm"


def font_mm(size_mm: float) -> str:
    """A font size as a Typst mm length, deterministic: `2.46915mm`."""
    return f"{size_mm:g}mm"
