"""Render's grid and font facts, read from the symbol library (GRID-HOME SB9).

This drawing code dies at the switch to symdef-drawn pages, so it keeps its own reading of the
library and takes no model: the model's `DrawingLibrary` record is the facade's copy of the same
numbers, and `derive` reads that. A test pins the two together.
"""

import math
from decimal import Decimal

from electrical_symbols import LIBRARY
from fransys_model.derive.print_sizes import TextRole

__all__ = [
    "ASCENT_RATIO",
    "CAPITAL_RATIO",
    "DIVISIONS",
    "FONT_FAMILY",
    "font_size_mm",
    "grid_to_mm",
    "role_height_mm",
    "text_room_g",
]

_FONT = LIBRARY.font
assert _FONT is not None  # noqa: S101 - the bundled library always carries its font
FONT_FAMILY = _FONT.family
DIVISIONS = LIBRARY.grid.divisions_per_module
_HEIGHTS = _FONT.heights
CAPITAL_RATIO = Decimal(_FONT.cap_height) / Decimal(_FONT.units_per_em)
ASCENT_RATIO = Decimal(_FONT.ascent) / Decimal(_FONT.units_per_em)
_HEIGHT_NAME = {
    TextRole.LABEL: "smallest",
    TextRole.BODY: "body",
    TextRole.HEADING_2: "heading_2",
    TextRole.HEADING_1: "heading_1",
}


def _per_division(module_mm: Decimal) -> Decimal:
    return module_mm / Decimal(DIVISIONS)


def grid_to_mm(origin_mm: int, g: int | Decimal, module_mm: Decimal) -> Decimal:
    """One grid coordinate `g` converted to an absolute mm position."""
    return Decimal(origin_mm) + Decimal(g) * _per_division(module_mm)


def font_size_mm(capital_height_mm: Decimal) -> Decimal:
    """The font size, in mm, whose capitals are `capital_height_mm` high."""
    return capital_height_mm / CAPITAL_RATIO


def role_height_mm(role: TextRole, profile_text_height_mm: Decimal) -> Decimal:
    """The capital height, in mm, that text of `role` prints at (the library's heights)."""
    if role is TextRole.LABEL:
        return profile_text_height_mm
    return max(Decimal(str(_HEIGHTS[_HEIGHT_NAME[role]])), profile_text_height_mm)


def text_room_g(text_height_mm: Decimal, module_mm: Decimal) -> int:
    """The grid units a text of capital height `text_height_mm` gets: font size over one G, up."""
    return math.ceil(font_size_mm(text_height_mm) / _per_division(module_mm))
