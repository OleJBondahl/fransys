"""The pdf's printed sizes in mm (EXACT-SIZES E3, E7, E10); `Sizes`, `sizes_of` live in derive."""

from typing import TYPE_CHECKING

from fransys_model.derive import Sizes, sizes_of
from fransys_model.derive.print_sizes import rule_mm

if TYPE_CHECKING:
    from fransys_model.kernel import Model

__all__ = ["Sizes", "font_mm", "rule_of", "sizes_of"]


def rule_of(model: Model) -> str:
    """The table rule as a Typst mm length, from the build's `[lines] rule` (SIZES)."""
    return f"{rule_mm(model)}mm"


def font_mm(size_mm: float) -> str:
    """A font size as a Typst mm length, deterministic: `2.46915mm`."""
    return f"{size_mm:g}mm"
