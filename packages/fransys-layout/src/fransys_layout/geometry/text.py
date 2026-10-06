"""Text width from per-glyph advances (docs/design/geometry.md 5.3)."""

from typing import TYPE_CHECKING

from .text_metrics import ADVANCES, UNITS_PER_EM

if TYPE_CHECKING:
    from .units import Coord

_WIDEST = max(ADVANCES.values())


def text_width(text: str, *, height: Coord) -> Coord:
    """Width of `text` set at `height`, in grid units."""
    thousandths = sum(ADVANCES.get(glyph, _WIDEST) for glyph in text)
    return -(-thousandths * height // UNITS_PER_EM)
