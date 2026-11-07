"""The box of an arrow, fitted to the widest text a reference marker can print (R350).

A reference marker prints `#n-p<page>:<column><row>` and a `+k`, known only once the pages
exist. Placement reserves the box of the widest such line: its numbers have as many digits as the
symbol count, its column and row are the highest of any sheet, each digit the widest symdef
measures.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import widest_target_line
from fransys_model.layout import sheet_for
from fransys_model.vocab import PageKind

from .placement_sets import drawing_scopes
from .placement_views import marker_boxes

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.core import Box, Orientation
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Unit

    from .placement_kit import SymbolKit

__all__ = ["link_fit", "widest_digit"]

_DIGITS = "123456789"  # 0 is no candidate: `widest_target_line` reads its numbers as ints, so 0 drops out


def widest_digit(library: Library, length: int) -> str:
    """The digit whose `length`-long run symdef measures widest as a marker line."""
    widest, best = _DIGITS[0], -1
    for digit in _DIGITS:
        width = marker_boxes(library, digit * length)["R0"].w
        if width > best:
            widest, best = digit, width
    return widest


def link_fit(model: Model, kit: SymbolKit, library: Library, unit: Id[Unit] | None) -> Mapping[Orientation, Box]:
    """The arrow's box at each orientation, for the widest line the set of `unit` can print.

    Only the symbols of `unit` count (as `marker_fit`'s `unit`): a unit drawn
    alone reads nothing of its parent, so it is the same alone as inside its parent.
    """
    sheets = [sheet_for(model, kind) for kind in PageKind]
    count = sum(len(one.symbols) for one in drawing_scopes(model, kit) if one.of_unit == unit)
    columns = max(one.frame_columns for one in sheets)
    rows = max(one.frame_rows for one in sheets)
    sample = len(widest_target_line(model, count, columns, rows, _DIGITS[0]))
    line = widest_target_line(model, count, columns, rows, widest_digit(library, sample))
    return marker_boxes(library, line)
