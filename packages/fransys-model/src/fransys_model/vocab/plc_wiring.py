"""The one PLC wiring walk: which functions share a physical net (decisions model-0068, 0083).

`check_plc_wiring` (the check) and `derive.passes.plc_allocation` (PW1, PW2 and PW4 of the
PLC-WIRED spec) both ask the same question: which functions of a given set share a physical net
with a function's ports. It is answered here, over `vocab.closure.net_of`, and nowhere else.
"""

from typing import TYPE_CHECKING

from fransys_model.vocab.closure import net_of
from fransys_model.vocab.tables import conductors, ports

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port


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


def direct_neighbours(model: Model) -> dict[Id[Function], frozenset[Id[Function]]]:
    """Each function mapped to the functions one conductor joins it to (model-0211).

    A net also passes terminals, links and mates; this is the single conductor only.
    """
    all_ports = ports(model)
    found: dict[Id[Function], set[Id[Function]]] = {}
    for conductor in conductors(model).values():
        a, b = all_ports[conductor.a].function, all_ports[conductor.b].function
        found.setdefault(a, set()).add(b)
        found.setdefault(b, set()).add(a)
    return {function: frozenset(others) for function, others in found.items()}
