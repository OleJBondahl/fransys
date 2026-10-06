"""What the current graph is built from: the port pairs it ties and the open ends.

Split from `current_chains` (RATINGS-2 C3). `pairs` and `two_ports` say which ports a link, a
mate or a two-port function ties; `open_ends` says which ports let current leave the model.
"""

import dataclasses
from typing import TYPE_CHECKING

from fransys_model.vocab.closure import link_groups
from fransys_model.vocab.contacts import link_state
from fransys_model.vocab.enums import FunctionKind, LinkKind, PortRole
from fransys_model.vocab.membership import boundary, external, standalone, units
from fransys_model.vocab.tables import functions, internal_links, mates, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.contacts import LinkState
    from fransys_model.vocab.core import Function, Item, Port


@dataclasses.dataclass(frozen=True, slots=True)
class Joint:
    """Two ports tied by one internal link or one mate, and the two functions they belong to.

    A link has its `item` and the `state` it closes in (`link_state`, judged by the function of
    the first port); a mate has no item and is always closed (`both`).
    """

    first: Id[Port]
    second: Id[Port]
    one: Id[Function]
    other: Id[Function]
    item: Id[Item] | None = None
    state: LinkState = "both"


def pairs(model: Model) -> tuple[list[Joint], list[Joint]]:
    """The joints the internal links and the mates tie: (links, mates)."""
    function_of = {port.id: port.function for port in ports(model).values()}
    by_function: dict[Id[Function], list[Port]] = {}
    for port in ports(model).values():
        by_function.setdefault(port.function, []).append(port)
    links = [
        Joint(
            group.ports[0],
            other,
            group.function,
            function_of[other],
            group.item,
            link_state(model, group.function, group.link.id),
        )
        for group in link_groups(model, frozenset(LinkKind))
        for other in group.ports[1:]
    ]
    mated: list[Joint] = []
    for mate in mates(model).values():
        named: dict[str, list[Id[Port]]] = {}
        for port in by_function.get(mate.b, ()):
            named.setdefault(port.name, []).append(port.id)
        mated.extend(
            Joint(port.id, other, mate.a, mate.b)
            for port in by_function.get(mate.a, ())
            for other in named.get(port.name, ())
        )
    return links, mated


def two_ports(model: Model) -> list[tuple[Id[Port], Id[Port], Id[Function]]]:
    """The two-port functions no link joins internally, a connector or coil excepted.

    A source, a load, a sensor: exactly two ports and no `InternalLink` between them, either order.
    A link to another function's port does not disqualify it; `current_chains` treats it as a wire.
    """
    joined = {frozenset((link.a, link.b)) for link in internal_links(model).values()}
    by_function: dict[Id[Function], list[Port]] = {}
    for port in ports(model).values():
        by_function.setdefault(port.function, []).append(port)
    return [
        (own[0].id, own[1].id, function.id)
        for function in functions(model).values()
        if function.kind not in {FunctionKind.CONNECTOR, FunctionKind.COIL}
        and len(own := by_function.get(function.id, ())) == 2  # noqa: PLR2004 -- the "two" in `two_ports`, this function's own definition
        and frozenset((own[0].template, own[1].template)) not in joined
    ]


def open_ends(model: Model) -> frozenset[Id[Port]]:
    """The ports where current can leave the model: they join the outside.

    Every port of an external item, and of a standalone unit's boundary function but not `INTERNAL`.
    A unit that is not standalone has its outside in the build, so its boundary ports are not open.
    """
    facing = {
        function
        for unit in units(model)
        if standalone(model, unit)
        for function in boundary(model, unit)
    }
    all_functions = functions(model)
    return frozenset(
        port.id
        for port in ports(model).values()
        if external(model, all_functions[port.function].item)
        or (port.function in facing and port.role is not PortRole.INTERNAL)
    )
