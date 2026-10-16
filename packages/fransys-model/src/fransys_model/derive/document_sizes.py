"""The font sizes of a document's pages, from the capital heights (EXACT-SIZES E3, E7, E10)."""

lazy from decimal import Decimal

from fransys_model.layout import profile_of
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

from .document_unit import document_unit
from .print_sizes import TextRole, font_size_mm, role_height_mm
from .rows_sheet import Sizes
from .title_band import title_band_need

__all__ = ["sizes_of"]


def _font_mm(role: TextRole, text_height_mm: Decimal) -> float:
    return float(font_size_mm(role_height_mm(role, text_height_mm)))


def sizes_of(model: Model, document: Id[Document]) -> Sizes:
    """The font sizes of a document's pages: its unit's profile (the top's) sets the smallest.

    `document` is the document's id.
    """
    height = profile_of(model, document_unit(model, document)).text_height_mm
    label, body = _font_mm(TextRole.LABEL, height), _font_mm(TextRole.BODY, height)
    return Sizes(
        label=label,
        body=body,
        heading_2=_font_mm(TextRole.HEADING_2, height),
        heading_1=_font_mm(TextRole.HEADING_1, height),
        title_band_mm=title_band_need(label, body),
    )
