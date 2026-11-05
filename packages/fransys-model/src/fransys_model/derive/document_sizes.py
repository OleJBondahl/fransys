"""The font sizes of the build's pages, from the library heights (EXACT-SIZES E3, E7, E10)."""

lazy from fransys_model.kernel import Model

from .print_sizes import TextRole, font_size_mm, role_height_mm
from .rows_sheet import Sizes
from .title_band import title_band_need

__all__ = ["sizes_of"]


def _font_mm(model: Model, role: TextRole) -> float:
    return float(font_size_mm(model, role_height_mm(model, role)))


def sizes_of(model: Model) -> Sizes:
    """The font sizes of the build's pages, from the build's library heights."""
    label, body = _font_mm(model, TextRole.LABEL), _font_mm(model, TextRole.BODY)
    return Sizes(
        label=label,
        body=body,
        heading_2=_font_mm(model, TextRole.HEADING_2),
        heading_1=_font_mm(model, TextRole.HEADING_1),
        title_band_mm=title_band_need(model),
    )
