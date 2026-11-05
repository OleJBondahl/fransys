"""A slot that carries text takes its box from the text: symdef measures it, layout reads it once (TEXT-BOX-MEASURED)."""

from typing import TYPE_CHECKING

from symdef import from_divisions, measure

from ._grid import symdef_orientation, to_box, to_reach

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core.values import Box, Orientation

    from .shape import LibrarySymbol, SymbolLibrary

__all__ = ("measured_slots",)


def measured_slots(
    symbol: LibrarySymbol,
    orient: Orientation,
    texts: Mapping[str, str],
    library: SymbolLibrary,
    height: int,
) -> tuple[Mapping[str, Box], Box]:
    """(each slot's box, the keep-out) of `symbol` at `orient`, each slot in `texts` measured around its string.

    Boxes are relative to the symbol origin, in G. `height` is the text height in G. A slot with
    no string is its reserved box. symdef's `measure` is the one measure (it unites the string's extent).
    """
    found = measure(symbol, symdef_orientation(orient), library, texts or None, from_divisions(library.grid, height))
    return {name: to_box(box) for name, box in found.slots.items()}, to_reach(found.keepout, int(library.grid.wire_pitch))
