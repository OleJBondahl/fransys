"""The one table of printed sizes, in mm (EXACT-SIZES E3, E4, E7, E10).

Reached as `fransys_model.derive.print_sizes.<name>`, never re-exported from `derive/__init__.py`.
A text size is a capital height (ISO 3098's h); `font_size_mm` turns it into the font size by the
bundled font's capital ratio, so no package keeps a ratio of its own.
"""

from decimal import Decimal
from enum import Enum

from fransys_model.derive._text_widths import ASCENT_UNITS, CAP_HEIGHT_UNITS, UNITS_PER_EM

__all__ = [
    "ASCENT_RATIO",
    "CAPITAL_RATIO",
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
    "font_size_mm",
    "role_height_mm",
]

# Exact: UNITS_PER_EM is 2**11, so each ratio has a finite decimal form.
CAPITAL_RATIO = Decimal(CAP_HEIGHT_UNITS) / Decimal(UNITS_PER_EM)
ASCENT_RATIO = Decimal(ASCENT_UNITS) / Decimal(UNITS_PER_EM)


class TextRole(Enum):
    """The four text roles of E3: a drawing label or table cell, body, heading 2, heading 1."""

    LABEL = "label"
    BODY = "body"
    HEADING_2 = "heading-2"
    HEADING_1 = "heading-1"


# Capital heights of the roles (ISO 3098's h); read only through `role_height_mm`.
_ROLE_HEIGHT_MM = {
    TextRole.LABEL: Decimal("1.8"),
    TextRole.BODY: Decimal("2.5"),
    TextRole.HEADING_2: Decimal("3.5"),
    TextRole.HEADING_1: Decimal(5),
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


def font_size_mm(capital_height_mm: Decimal) -> Decimal:
    """The font size, in mm, whose capitals are `capital_height_mm` high."""
    return capital_height_mm / CAPITAL_RATIO


def role_height_mm(role: TextRole, profile_text_height_mm: Decimal) -> Decimal:
    """The capital height, in mm, that text of `role` prints at: the one place that decides it.

    `text_height_mm` sets the smallest text on every page kind (E10): a label prints at it, and a
    larger role at its own size or at it, whichever is larger. The house value 1.8 changes nothing.
    """
    if role is TextRole.LABEL:
        return profile_text_height_mm
    return max(_ROLE_HEIGHT_MM[role], profile_text_height_mm)
