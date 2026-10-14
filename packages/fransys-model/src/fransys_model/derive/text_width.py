"""The one width of drawn text: DejaVu Sans Condensed advances from the TTFs (model-0190).

Reached as `fransys_model.derive.text_width.<name>`, never re-exported from `derive/__init__.py`.
Layout measures in grid units, pdf in millimetres; both scale `text_units`, so there is one rule.
A glyph outside the table counts as the widest advance of its weight, so a text is never
under-measured.
"""

from typing import TYPE_CHECKING

from fransys_model.derive._text_widths import BOLD_PAIRS, REGULAR_PAIRS, UNITS_PER_EM

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["G_PER_MODULE", "UNITS_PER_EM", "marking_widths", "text_units", "text_width"]

G_PER_MODULE = 8  # grid units in one module unit (DESIGN 6.1); a port marking is set one M high


def _table(pairs: str) -> frozendict[str, int]:
    entries = (pair.split("=") for pair in pairs.split())
    return frozendict({chr(int(code, 16)): int(advance) for code, advance in entries})


_REGULAR = _table(REGULAR_PAIRS)
_BOLD = _table(BOLD_PAIRS)
_WIDEST = {False: max(_REGULAR.values()), True: max(_BOLD.values())}


def text_units(text: str, *, bold: bool = False) -> int:
    """Width of `text` in font units (`UNITS_PER_EM` to the em), regular or bold."""
    table = _BOLD if bold else _REGULAR
    return sum(table.get(glyph, _WIDEST[bold]) for glyph in text)


def text_width(text: str, *, height: int, bold: bool = False) -> int:
    """Width of `text` set at `height`, in grid units, rounded up."""
    return -(-text_units(text, bold=bold) * height // UNITS_PER_EM)


def marking_widths(markings: Iterable[str]) -> tuple[int, ...]:
    """Each port marking's width in grid units, set one module high, for a generic box."""
    return tuple(text_width(marking, height=G_PER_MODULE) for marking in markings)
