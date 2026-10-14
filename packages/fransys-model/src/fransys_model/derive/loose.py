"""A function with nothing connected is drawn on no page (layout-0218, model-0226).

Layout leaves it off and render's `LAYOUT_MISSING` does not count it: one fact for both.
"""

from collections import Counter
from typing import Any

from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import functions, mates
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function


def function_is_loose(model: Model, function: Id[Function]) -> bool:
    """Whether nothing is connected to `function`: it is drawn on no page.

    A port is connected by a conductor or a net of two or more ports (a header join draws no
    line); a mated function counts its mate's ports. One connected pole keeps its item's
    same-kind functions.
    """
    return function in _loose(model)


@digest_cached(DIGEST_CACHE_SIZE)
def _loose(model: Model) -> frozenset[Id[Function]]:
    indexes = build_indexes(model)
    ports_on = _connected_ports(model)
    on = {f for f, ports in indexes.ports_by_function.items() if not ports_on.isdisjoint(ports)}
    on |= {f for mate in mates(model).values() if {mate.a, mate.b} & on for f in (mate.a, mate.b)}
    table = functions(model)
    live = {(table[f].item, table[f].kind) for f in on if f in table}
    return frozenset(
        f for f, record in table.items() if f not in on and (record.item, record.kind) not in live
    )


def _connected_ports(model: Model) -> frozenset[Id[Any]]:
    """The ports a conductor or a net of two or more ports connects; a header join draws nothing."""
    indexes = build_indexes(model)
    size = Counter(net for nets in indexes.nets_by_port.values() for net in nets)
    return frozenset(
        {
            *(port for port, found in indexes.conductors_by_port.items() if found),
            *(
                port
                for port, nets in indexes.nets_by_port.items()
                if any(size[net] > 1 for net in nets)
            ),
        }
    )
