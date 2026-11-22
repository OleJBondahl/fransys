"""The ports a kit maps onto one point of one symbol: a terminal's sides, never the poles of a switch (R2079 G1, CP-S2c-1).

The symbol's binding states it (`fransys_layout.symbols.ports_at_one_node`, R2092): pins of one node of one symbol are one electrical point.
This maps them to the kit's ports, with no model link group between; the drawn netlist reads the pairs.
"""

from typing import TYPE_CHECKING

from electrical_symbols import is_generic_box
from fransys_layout.symbols import library_symbol, ports_at_one_node, symbol_shape

if TYPE_CHECKING:
    from electrical_symbols import Library
    from fransys_model.kernel import Id
    from fransys_model.vocab import Port

    from .placement_kit import Pick, SymbolKit

__all__ = ["node_joins"]


def _groups(library: Library, pick: Pick) -> frozenset[frozenset[str]]:
    """The pin groups the pick's symbol draws at one node; a generic box has none."""
    return frozenset() if is_generic_box(pick.key) else ports_at_one_node(symbol_shape(library_symbol(library, pick.key, pick.poles), library))


def node_joins(kit: SymbolKit, library: Library) -> tuple[tuple[Id[Port], Id[Port]], ...]:
    """Each `(first, other)` port pair the kit maps onto pins of one node of one symbol: the ink joins them, whatever the model names."""
    found: list[tuple[Id[Port], Id[Port]]] = []
    for pick in kit.values():
        for group in _groups(library, pick):
            ports = [port for port, pin in pick.ports.items() if pin in group]
            found += [(ports[0], other) for other in ports[1:]]
    return tuple(found)
