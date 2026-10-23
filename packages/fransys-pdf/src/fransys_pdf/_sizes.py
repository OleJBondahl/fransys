"""The pdf's printed sizes in mm (EXACT-SIZES E3, E7, E10); `Sizes`, `sizes_of` live in derive."""

from typing import TYPE_CHECKING

from fransys_model.derive import Sizes, sizes_of
from fransys_model.derive.print_sizes import LINE_THICK_MM, LINE_THIN_MM, rule_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model

__all__ = ["THICK_STROKE", "THIN_STROKE", "Sizes", "font_mm", "rule_of", "sizes_of"]

THIN_STROKE = f"{LINE_THIN_MM}mm"
THICK_STROKE = f"{LINE_THICK_MM}mm"


def rule_of(model: Model) -> str:
    """The table rule as a Typst mm length, from the build's `[lines] rule` (SIZES)."""
    return f"{rule_mm(model)}mm"


def font_mm(size_mm: float) -> str:
    """A font size as a Typst mm length, deterministic: `2.46915mm`."""
    return f"{size_mm:g}mm"
