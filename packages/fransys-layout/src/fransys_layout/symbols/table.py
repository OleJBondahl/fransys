"""A table as one symdef symbol, sized to its texts and put at a point (el-0013)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from symdef import fitted_table, from_divisions, measure, translate

from fransys_layout.core.geometry import offset_to

from ._grid import symdef_orientation, to_box

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from symdef import Library

    from .shape import LibrarySymbol

__all__ = ("TableAsk", "placed_table")

HEADING_SLOT = "heading"  # the head slot that takes the ask's heading text (es-0075)


@dataclass(frozen=True, slots=True)
class TableAsk:
    """What the table is made of: its row and head symbols, a text per cell, and its top-left.

    `texts` holds one mapping of slot id to text per row. `at` is where the table's keep-out
    starts, in G, in the frame of the symbol it belongs to. `heading` is the text of the head's
    `heading` slot, copied as given: a caller who sets it passes a headed `head` (es-0075).
    """

    row: LibrarySymbol
    head: LibrarySymbol
    texts: Sequence[Mapping[str, str]]
    at: tuple[int, int]
    heading: str | None = None


def placed_table(ask: TableAsk, library: Library, text_height: int) -> LibrarySymbol:
    """The fitted table, head always set, its keep-out's top-left at `ask.at`.

    The text is set at `text_height` G, which is the library's `body` text height (the
    el tests hold that equal); the layer does no unit arithmetic of its own.
    """
    made = fitted_table(
        ask.row,
        "y",
        ask.texts,
        library,
        from_divisions(library.grid, text_height),
        head=ask.head,
        head_texts=None if ask.heading is None else {HEADING_SLOT: ask.heading},
    )
    keep = to_box(measure(made, symdef_orientation("R0"), library).keepout)
    dx, dy = offset_to(keep, *ask.at)
    return translate(made, from_divisions(library.grid, dx), from_divisions(library.grid, dy))
