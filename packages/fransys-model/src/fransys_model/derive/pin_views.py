"""The connector pins drawn as views, the mated pin pairs and the connector gender (KIT-FACTS).

One home for what the old engine decided about a connector's pins at three points of its read step.
"""

from collections import defaultdict
lazy from collections.abc import Iterable, Mapping
lazy from collections.abc import Set as AbstractSet

from fransys_model.derive.facts.children import parent_item
from fransys_model.derive.facts.item_predicates import cable_items
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.facts.unit_index import item_unit, unit_index
from fransys_model.derive.facts.units import (
    boundary,
    enclosing_boards,
    item_chain,
    unit_subtree,
    units,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import connector_facets
from fransys_model.derive.order_kit import (
    lower_function,
    pin_items_in_order,
    pin_mates_in_order,
)
from fransys_model.derive.rows_pin_views import PinMate, PinView
from fransys_model.derive.unused import port_is_reached
from fransys_model.vocab.tables import functions, mates, ports, unused_boundaries
lazy from fransys_model.kernel import AuthoringKey, Id, Model, canonical
lazy from fransys_model.vocab.core import Function, Item, Port
lazy from fransys_model.vocab.templates import FunctionTemplate
lazy from fransys_model.vocab.units import Unit

__all__ = ["connector_pin_mates", "connector_pin_views", "template_gender"]


def template_gender(model: Model, template: Id[FunctionTemplate] | None) -> str | None:
    """The connector facet's gender of a function template, `None` without one."""
    shape = None if template is None else connector_facets(model).get(template)
    return None if shape is None or shape.gender is None else shape.gender.value


def connector_pin_views(
    model: Model, chained: AbstractSet[Id[Item]], wired: AbstractSet[Id[Port]]
) -> tuple[PinView, ...]:
    """One row per pin of each connector function, in port id order.

    A connector of an item in `chained` (a device chain's member) stays whole and has no row.
    A pin is drawn if it or its mate is in `wired`, or it is on a unit boundary whose function
    has no such pin. `wired` is the engine's set of ports on kept connections.
    """
    pins = _pins(model, chained)
    pairs = connector_pin_mates(model, frozenset(pins))
    mate_of = _mates(pairs)
    own = _mates(p for p in pairs if _own(model, pins, p))
    edges = _edges(model)
    kept = _kept(pins, mate_of, wired, edges)
    table = functions(model)
    return tuple(
        PinView(
            port=port,
            function=function,
            item=table[function].item,
            name=ports(model)[port].name,
            gender=template_gender(model, table[function].template) or "",
            mate=mate_of.get(port),
            drawn=port in kept,
            elsewhere=port in kept and function in edges and not _reached(model, port, own),
        )
        for port, function in pin_items_in_order(pins)
    )


def _pins(model: Model, chained: AbstractSet[Id[Item]]) -> dict[Id[Port], Id[Function]]:
    """Each port of a connector function outside `chained`, with its function."""
    by_function = build_indexes(model).ports_by_function
    return {
        port: function.id
        for function in functions(model).values()
        if function_role(model, function.id).pin_group and function.item not in chained
        for port in by_function.get(function.id, ())
    }


def _mates(pairs: Iterable[PinMate]) -> dict[Id[Port], Id[Port]]:
    """Each mated pin mapped to the one it is plugged into, in both directions."""
    found: dict[Id[Port], Id[Port]] = {}
    for pair in pairs:
        found[pair.upper], found[pair.lower] = pair.lower, pair.upper
    return found


def _edges(model: Model) -> frozenset[Id[Function]]:
    """The boundary functions of every unit, less those an `UnusedBoundary` record waives."""
    edges = {f for unit in units(model) for f in boundary(model, unit)}
    return frozenset(edges - {one.function for one in unused_boundaries(model).values()})


def _kept(
    pins: Mapping[Id[Port], Id[Function]],
    mate_of: Mapping[Id[Port], Id[Port]],
    wired: AbstractSet[Id[Port]],
    edges: AbstractSet[Id[Function]],
) -> frozenset[Id[Port]]:
    """The pins wired or mated to a wired one, then every pin of a boundary function with none."""
    kept = {port for port in pins if port in wired or mate_of.get(port) in wired}
    live = {pins[port] for port in kept}
    return frozenset(kept | {port for port, f in pins.items() if f in edges and f not in live})


def _reached(model: Model, port: Id[Port], own: Mapping[Id[Port], Id[Port]]) -> bool:
    """Whether a wire inside the drawing reaches `port`, or its mate whose document knows it."""
    mate = own.get(port)
    return port_is_reached(model, port) or (mate is not None and port_is_reached(model, mate))


def _knows(model: Model, document: Id[Unit] | None, other: Id[Unit] | None) -> bool:
    """Whether the document of unit `document` knows a thing in unit `other`.

    A nested unit's document knows only its own subtree; a top-level unit's and the system's know
    every unit, since their leaving wires draw as stubs.
    """
    nested = document is not None and len(unit_index(model).containing.get(document, ())) > 1
    return document is None or not nested or other in unit_subtree(model, document)


def _own(model: Model, pins: Mapping[Id[Port], Id[Function]], pair: PinMate) -> bool:
    """Whether both pins' documents know the mate: a nested unit's knows none from outside it."""
    table = functions(model)
    one, other = (item_unit(model, table[pins[p]].item) for p in (pair.upper, pair.lower))
    return _knows(model, one, other) and _knows(model, other, one)


def connector_pin_mates(model: Model, pins: AbstractSet[Id[Port]]) -> tuple[PinMate, ...]:
    """Each mate's equal-named pins of `pins`, upper (plug) side first, in id order."""
    table = ports(model)
    by_function: dict[Id[Function], dict[str, Id[Port]]] = defaultdict(dict)
    for port in canonical(pins):
        by_function[table[port].function][table[port].name] = port
    cable_like = _cable_like(model)
    found = []
    for mate in mates(model).values():
        if mate.a not in by_function or mate.b not in by_function:
            continue
        lower = lower_function(
            mate.a,
            mate.b,
            _lower_rank(model, cable_like, mate.a),
            _lower_rank(model, cable_like, mate.b),
        )
        upper = mate.b if lower == mate.a else mate.a
        names = by_function[upper].keys() & by_function[lower].keys()
        found.extend(
            PinMate(upper=by_function[upper][n], lower=by_function[lower][n]) for n in names
        )
    return pin_mates_in_order(found)


def _lower_rank(
    model: Model, cable_like: frozenset[Id[Item]], function: Id[Function]
) -> tuple[bool, bool, AuthoringKey]:
    """On or under a board first, then not on a cable or harness, then the later key."""
    record = functions(model)[function]
    return (
        bool(enclosing_boards(model, record.item)),
        not _on_cable(model, cable_like, record.item),
        record.key,
    )


def _cable_like(model: Model) -> frozenset[Id[Item]]:
    """Every cable item and every harness (a cable's parent)."""
    cables = cable_items(model)
    harnesses = {parent for c in cables if (parent := parent_item(model, c)) is not None}
    return frozenset(cables | harnesses)


def _on_cable(model: Model, cable_like: frozenset[Id[Item]], item: Id[Item]) -> bool:
    """Whether `item` or an ancestor is in `cable_like`: a cable or a harness."""
    return any(node in cable_like for node in item_chain(model, item))
