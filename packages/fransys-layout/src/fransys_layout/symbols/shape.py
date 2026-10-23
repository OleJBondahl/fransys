"""A library symbol and its shape at R0 before any text: the plain values the caller reads."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from symdef import UnknownSymbolError, from_divisions, measure, nodes_of, repeat

from fransys_layout.core.errors import CoreError
from fransys_layout.core.sym_values import PinTurn

from ._grid import symdef_orientation, to_box

if TYPE_CHECKING:
    from collections.abc import Mapping

    from symdef import Library, Symbol

    from fransys_layout.core.values import Box, Orientation

__all__ = (
    "LibrarySymbol",
    "Shape",
    "library_symbol",
    "stretched_body",
    "symbol_shape",
)

#: A symdef symbol, named here so a caller can annotate the value it only passes on.
type LibrarySymbol = Symbol


@dataclass(frozen=True, slots=True)
class Shape:
    """A symbol at R0: its body, each slot's reserved box, its pins and its nodes.

    `pins` are in the symbol's own order; `nodes` list the pin ids that are one point.
    """

    body: Box
    slots: Mapping[str, Box]
    pins: Mapping[str, PinTurn]
    nodes: tuple[tuple[str, ...], ...]


def library_symbol(library: Library, key: str, repeats: int = 1) -> LibrarySymbol:
    """The library's symbol `key`, repeated `repeats` times; `CoreError` names a key it lacks."""
    try:
        base = library.get(key)
    except UnknownSymbolError:
        msg = f"no symbol {key!r} in the symbol library; use a key the library holds"
        raise CoreError(msg) from None
    if repeats == 1:
        return base
    if repeats < 1 or not any(path.through for path in base.paths):
        msg = f"symbol {key!r} cannot be repeated {repeats} times; it has no through path"
        raise CoreError(msg)
    return repeat(base, repeats)


def symbol_shape(symbol: LibrarySymbol, library: Library) -> Shape:
    """`symbol` at R0 as plain values, its slots as reserved with no text in them."""
    found = measure(symbol, symdef_orientation("R0"), library)
    return Shape(
        to_box(found.body),
        {name: to_box(box) for name, box in found.slots.items()},
        {p.id: PinTurn(p.x, p.y, p.direction.name) for p in found.ports.values()},
        tuple(tuple(node.ports) for node in nodes_of(symbol)),
    )


def stretched_body(
    symbol: LibrarySymbol,
    orient: Orientation,
    axis: Literal["x", "y"],
    length: int,
    library: Library,
) -> Box:
    """The body of `symbol` stretched to `length` divisions along `axis`, then turned to `orient`.

    Only the body is read: a stretched symbol's slot anchors may sit between divisions (R450.3).
    """
    grown = {axis: from_divisions(library.grid, length)}
    return to_box(measure(symbol, symdef_orientation(orient), library, stretch=grown).body)
