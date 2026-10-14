"""The pdf's printed sizes in mm (EXACT-SIZES E3, E7, E10): font sizes from the capital heights."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import document_unit
from fransys_model.derive.print_sizes import (
    LINE_RULE_MM,
    LINE_THICK_MM,
    LINE_THIN_MM,
    TextRole,
    font_size_mm,
    role_height_mm,
)
from fransys_model.layout import profile_of

if TYPE_CHECKING:
    from decimal import Decimal

    from fransys_model.kernel import Model
    from fransys_model.vocab import Document


@dataclass(frozen=True)
class Sizes:
    """The four roles' font sizes in mm, for one document's profile `text_height_mm`."""

    label: float
    body: float
    heading_2: float
    heading_1: float


def _font_mm(role: TextRole, text_height_mm: Decimal) -> float:
    return float(font_size_mm(role_height_mm(role, text_height_mm)))


def sizes_of(model: Model, record: Document) -> Sizes:
    """The font sizes of a document's pages: its unit's profile (the top's) sets the smallest."""
    height = profile_of(model, document_unit(model, record)).text_height_mm
    return Sizes(
        label=_font_mm(TextRole.LABEL, height),
        body=_font_mm(TextRole.BODY, height),
        heading_2=_font_mm(TextRole.HEADING_2, height),
        heading_1=_font_mm(TextRole.HEADING_1, height),
    )


THIN_STROKE = f"{LINE_THIN_MM}mm"
THICK_STROKE = f"{LINE_THICK_MM}mm"
RULE = f"{LINE_RULE_MM}mm"


def font_mm(size_mm: float) -> str:
    """A font size as a Typst mm length, deterministic: `2.46915mm`."""
    return f"{size_mm:g}mm"
