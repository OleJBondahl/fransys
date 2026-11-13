"""The ports one link joins at one point of one symbol: a terminal's sides, never the poles of a switch (R2079 G1, CP-S2c-1).

The symbol's binding states it (`fransys_layout.symbols.ports_at_one_node`, R2092): pins of one node of one symbol are one electrical point.
This maps them to the ports of a link group; the drawn netlist reads the pairs.
"""

from typing import TYPE_CHECKING

from electrical_symbols import is_generic_box
from fransys_layout.symbols import library_symbol, ports_at_one_node, symbol_shape

from .placement_ids import pin_names, symbol_ids

if TYPE_CHECKING:
    from collections.abc import Iterable

    from electrical_symbols import Library
    from fransys_model.derive import LinkGroup
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

    from .placement_kit import Pick, SymbolKit

__all__ = ["node_joins"]


def _groups(library: Library, pick: Pick) -> frozenset[frozenset[str]]:
    """The pin groups the pick's symbol draws at one node; a generic box has none."""
    return frozenset() if is_generic_box(pick.key) else ports_at_one_node(symbol_shape(library_symbol(library, pick.key, pick.poles), library))


def node_joins(model: Model, kit: SymbolKit, library: Library, groups: Iterable[LinkGroup]) -> tuple[tuple[Id[Port], Id[Port]], ...]:
    """Each `(first, other)` port pair of a link group whose two ports are pins of one node of one symbol."""
    ids = symbol_ids(model, kit)
    pins = pin_names(model, kit, ids)
    picks = {ids[lead]: pick for lead, pick in kit.items()}
    nodes: dict[str, frozenset[frozenset[str]]] = {}
    found = []
    for group in groups:
        first, *rest = group.ports
        for other in rest:
            a, b = pins.get(first), pins.get(other)
            if a is None or b is None or a.sym != b.sym:
                continue
            if any({a.pin, b.pin} <= group for group in nodes.setdefault(a.sym, _groups(library, picks[a.sym]))):
                found.append((first, other))
    return tuple(found)
