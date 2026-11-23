"""Pure `Decimal` number formatting: no `float` anywhere."""

from decimal import Decimal
from typing import TYPE_CHECKING

from ._library import font_size_mm

if TYPE_CHECKING:
    from electrical_symbols import Library


def printed_font_mm(library: Library, text_height_mm: Decimal) -> Decimal:
    """The font size in mm (to 0.0001) of a text with capitals `text_height_mm` high."""
    return font_size_mm(library, text_height_mm).quantize(Decimal("0.0001"))
