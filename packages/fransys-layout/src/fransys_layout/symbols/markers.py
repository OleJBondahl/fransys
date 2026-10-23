"""The marker symbol's keep-out box at each orientation, set once on the core's options."""

from dataclasses import replace
from typing import TYPE_CHECKING

from symdef import fitted_symbol, measure

from ._grid import ORIENTATIONS, symdef_orientation, to_box

if TYPE_CHECKING:
    from collections.abc import Mapping

    from symdef import Library

    from fransys_layout.core.values import Box, Options, Orientation

    from .shape import LibrarySymbol

__all__ = (
    "fitted_marker",
    "fitted_marker_views",
    "marker_views",
    "with_marker",
)


def marker_views(symbol: LibrarySymbol, library: Library) -> Mapping[Orientation, Box]:
    """`symbol`'s keep-out box at each of the eight orientations (SB4, layout-0305)."""
    return {
        o: to_box(measure(symbol, symdef_orientation(o), library).keepout) for o in ORIENTATIONS
    }


def with_marker(options: Options, symbol: LibrarySymbol, library: Library) -> Options:
    """`options` with `Options.marker` read from the marker `symbol`."""
    return replace(options, marker=marker_views(symbol, library))


def fitted_marker_views(
    symbol: LibrarySymbol, slot: str, text: str, library: Library
) -> Mapping[Orientation, Box]:
    """`symbol`'s keep-out box at each orientation once its `slot` is stretched to hold `text`.

    A text that fits asks for nothing, so the boxes equal `marker_views` (D95).
    """
    return marker_views(fitted_marker(symbol, slot, text, library), library)


def fitted_marker(symbol: LibrarySymbol, slot: str, text: str, library: Library) -> LibrarySymbol:
    """`symbol` stretched by symdef so its `slot` holds `text`, as placement measures it (D95).

    A drawn marker's ports are read from it (R430.1); a text that fits asks for nothing.
    """
    return fitted_symbol(symbol, {slot: text}, library, 1.0)
