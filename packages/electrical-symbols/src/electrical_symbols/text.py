"""The one width of drawn text: per-glyph advances of the drawing font (RR-O5, layout-0132)."""

from .text_metrics import ADVANCES, UNITS_PER_EM

_WIDEST = max(ADVANCES.values())


def text_width(text: str, *, height: int) -> int:
    """Width of `text` set at `height`, in grid units."""
    thousandths = sum(ADVANCES.get(glyph, _WIDEST) for glyph in text)
    return -(-thousandths * height // UNITS_PER_EM)
