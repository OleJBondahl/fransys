"""The one table of printed sizes, in mm (EXACT-SIZES E3, E4, E7, E10).

Reached as `fransys_model.derive.print_sizes.<name>`, never re-exported from `derive/__init__.py`.
A text size is a capital height (ISO 3098's h); `font_size_mm` turns it into the font size by the
library font's capital ratio, which the model's `DrawingLibrary` record holds (GRID-HOME G6), so
no package keeps a ratio or a role height of its own.
"""

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from fransys_model.derive.library_grid import library_grid, text_height

if TYPE_CHECKING:
    from fransys_model.kernel import Model

__all__ = [
    "DASH_GAP_MM",
    "DASH_LONG_MM",
    "JUNCTION_DOT_MM",
    "LINE_RULE_MM",
    "LINE_THICK_MM",
    "LINE_THIN_MM",
    "OUTLINE_DASHES_MM",
    "SYMBOL_DASH_GAP_MM",
    "SYMBOL_DASH_MM",
    "TextRole",
    "ascent_ratio",
    "font_size_mm",
    "house_text_height_mm",
    "role_height_mm",
]


class TextRole(Enum):
    """The four text roles of E3: a drawing label or table cell, body, heading 2, heading 1."""

    LABEL = "label"
    BODY = "body"
    HEADING_2 = "heading-2"
    HEADING_1 = "heading-1"


# The library height each role prints at; the heights themselves are the record's.
_ROLE_HEIGHT_NAME = {
    TextRole.LABEL: "smallest",
    TextRole.BODY: "body",
    TextRole.HEADING_2: "heading_2",
    TextRole.HEADING_1: "heading_1",
}

# Line roles: stroke widths.
LINE_THIN_MM = Decimal("0.25")
LINE_THICK_MM = Decimal("0.5")
LINE_RULE_MM = Decimal("0.18")

# Dashes and the dot.
DASH_LONG_MM = Decimal(4)
DASH_GAP_MM = Decimal(1)
OUTLINE_DASHES_MM = (Decimal(4), Decimal(1), Decimal("0.25"), Decimal(1))
SYMBOL_DASH_MM = Decimal("1.25")
SYMBOL_DASH_GAP_MM = Decimal("0.625")
JUNCTION_DOT_MM = Decimal(1)


def font_size_mm(model: Model, capital_height_mm: Decimal) -> Decimal:
    """The font size, in mm, whose capitals are `capital_height_mm` high."""
    return capital_height_mm / library_grid(model).capital_ratio


def ascent_ratio(model: Model) -> Decimal:
    """How far the font's ascent reaches above the baseline per font size."""
    return library_grid(model).ascent_ratio


def house_text_height_mm(model: Model) -> Decimal:
    """The house text height: the library's smallest capital height; a label prints at it (E10)."""
    return text_height(model, _ROLE_HEIGHT_NAME[TextRole.LABEL])


def role_height_mm(model: Model, role: TextRole, profile_text_height_mm: Decimal) -> Decimal:
    """The capital height, in mm, that text of `role` prints at: the one place that decides it.

    `text_height_mm` sets the smallest text on every page kind (E10): a label prints at it, and a
    larger role at its library height or at it, whichever is larger.
    """
    if role is TextRole.LABEL:
        return profile_text_height_mm
    return max(text_height(model, _ROLE_HEIGHT_NAME[role]), profile_text_height_mm)
