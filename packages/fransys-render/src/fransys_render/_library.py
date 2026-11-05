"""Render's grid and font facts, read from the build's symbol `Library` (GRID-HOME SB9).

This drawing code dies at the switch to symdef-drawn pages, so it takes no model: every function
reads the `Library` the facade built for this build (the consumer's grid and font, SO-E).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from electrical_symbols import LIBRARY

if TYPE_CHECKING:
    from electrical_symbols import Library

__all__ = [
    "DIVISIONS",
    "capital_ratio",
    "font_family",
    "font_size_mm",
    "grid_to_mm",
    "smallest_height_mm",
]

DIVISIONS = LIBRARY.grid.divisions_per_module  # fixed library data; no consumer setting changes it


def font_family(library: Library) -> str:
    """The family name the build's font is set in."""
    return library.font.family


def smallest_height_mm(library: Library) -> Decimal:
    """The build's smallest capital height in mm: the library's `smallest`, a label's height."""
    return Decimal(str(library.font.heights["smallest"]))


def capital_ratio(library: Library) -> Decimal:
    """The capital height per font size of the build's font."""
    font = library.font
    return Decimal(font.cap_height) / Decimal(font.units_per_em)


def _per_division(module_mm: Decimal) -> Decimal:
    return module_mm / Decimal(DIVISIONS)


def grid_to_mm(origin_mm: int, g: int | Decimal, module_mm: Decimal) -> Decimal:
    """One grid coordinate `g` converted to an absolute mm position."""
    return Decimal(origin_mm) + Decimal(g) * _per_division(module_mm)


def font_size_mm(library: Library, capital_height_mm: Decimal) -> Decimal:
    """The font size, in mm, whose capitals are `capital_height_mm` high."""
    return capital_height_mm / capital_ratio(library)
