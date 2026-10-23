"""The reference marker's box at each orientation: the flag beside a pin, the turned one over it.

A marker over or under a pin reads along its wire (S20 M1-M6): it is `MARKER_TURNED`, one text
height wide, so markers on neighbouring pins never share a stagger level. A marker beside a pin is
the flag with horizontal text. Both are measured here once, so every box comes from one place.
"""

from typing import TYPE_CHECKING, cast

from electrical_symbols import MARKER_SLOT, MARKER_TURNED
from fransys_layout.symbols import fitted_marker_views, library_symbol, marker_views

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.core import Box, Orientation

__all__ = ["MARKER", "MARKER_KEYS", "marker_boxes"]

#: The symbol whose keep-out box is the reference marker's footprint beside a pin (layout-0305).
MARKER = "reference-marker"

#: Every library key a reference marker draws with: the flag and the turned one (es-0082).
MARKER_KEYS = frozenset({MARKER, MARKER_TURNED})

# Core orientation (R90 faces south, R270 north; M is the mirrored one) -> the turned symbol's turn.
_TURNED = {"R90": "R0", "MR270": "R0", "R270": "R180", "MR90": "R180"}


def marker_boxes(library: Library, text: str | None = None) -> Mapping[Orientation, Box]:
    """The marker's keep-out box at every orientation once its slot holds `text`.

    `None` is the plain marker. A text that fits asks for nothing (D95).
    """
    flag, turned = library_symbol(library, MARKER), library_symbol(library, MARKER_TURNED)
    if text is None:
        across, along = marker_views(flag, library), marker_views(turned, library)
    else:
        across = fitted_marker_views(flag, MARKER_SLOT, text, library)
        along = fitted_marker_views(turned, MARKER_SLOT, text, library)
    return {
        o: along[cast("Orientation", _TURNED[o])] if o in _TURNED else box
        for o, box in across.items()
    }
