"""A slot that carries text takes its box from the text: symdef measures it, layout reads it once (TEXT-BOX-MEASURED)."""

from typing import TYPE_CHECKING

from symdef import from_divisions, measure, orient
from symdef import ink_boxes as symdef_ink_boxes

from ._grid import symdef_orientation, to_box, to_reach

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core.values import Box, Orientation

    from .shape import LibrarySymbol, SymbolLibrary

__all__ = ("ink_boxes", "measured_slots")


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


def ink_boxes(symbol: LibrarySymbol, orient_to: Orientation, texts: Mapping[str, str], library: SymbolLibrary, height: int) -> Mapping[str, Box]:
    """Each string's ink in `texts` for `symbol` at `orient_to`: what is drawn, with no reserved room.

    Boxes are relative to the symbol origin, in G, rounded outward by symdef (`ink_boxes(on_grid=True)`)
    after the symbol is turned. `height` is the text height in G. A slot with no string has no box;
    a string for a slot the symbol lacks raises symdef's `UnknownNameError`.
    """
    found = symdef_ink_boxes(
        orient(symbol, symdef_orientation(orient_to)), texts, from_divisions(library.grid, height), library.font, library.grid, on_grid=True
    )
    return {name: to_box(box) for name, box in found.texts.items()}
