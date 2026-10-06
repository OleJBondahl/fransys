"""The one PLC wiring walk: which functions share a physical net (decisions model-0068, 0083).

`check_plc_wiring` (the check) and `derive.passes.plc_allocation` (PW1, PW2 and PW4 of the
PLC-WIRED spec) both ask the same question: which functions of a given set share a physical net
with a function's ports. It is answered here, over `vocab.closure.net_of`, and nowhere else.
"""

from typing import TYPE_CHECKING

from fransys_model.vocab.closure import net_of
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port


def ports_by_function(model: Model) -> dict[Id[Function], list[Id[Port]]]:
    """Every port of `model`, grouped by the function that owns it."""
    by_function: dict[Id[Function], list[Id[Port]]] = {}
    for port in ports(model).values():
        by_function.setdefault(port.function, []).append(port.id)
    return by_function


def owner_of_port(
    by_function: Mapping[Id[Function], list[Id[Port]]], owners: Collection[Id[Function]]
) -> dict[Id[Port], Id[Function]]:
    """Each port of a function in `owners`, mapped to that function."""
    return {port: function for function in owners for port in by_function.get(function, ())}


def wired_functions(
    model: Model, own_ports: Collection[Id[Port]], owner_of: Mapping[Id[Port], Id[Function]]
) -> frozenset[Id[Function]]:
    """The functions of `owner_of` that share a physical net with any of `own_ports`.

    A function that owns some of `own_ports` itself is included when a port of it (or another
    of its ports) is on the same net; callers subtract the function they ask about.
    """
    found: set[Id[Function]] = set()
    for port in own_ports:
        net = net_of(model, port)
        if net is not None:
            found.update(owner_of[p] for p in net.ports if p in owner_of)
    return frozenset(found)
