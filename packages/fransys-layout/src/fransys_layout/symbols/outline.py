"""The unit frame's room, read from the library (R889, R900): the margin and the label slot as one value, copied and never computed."""

from typing import TYPE_CHECKING

from fransys_layout.core.values import OutlineRoom, Size

from .shape import library_symbol, symbol_shape

if TYPE_CHECKING:
    from .shape import SymbolLibrary

__all__ = ("outline_room",)

_KEY = "unit-outline"


def outline_room(library: SymbolLibrary) -> OutlineRoom:
    """`[grid] outline_margin`, the `label` slot box and the body size of the `unit-outline` symbol, both in grid divisions."""
    shape = symbol_shape(library_symbol(library, _KEY), library)
    return OutlineRoom(library.grid.outline_margin, shape.slots["label"], Size(shape.body.w, shape.body.h))
