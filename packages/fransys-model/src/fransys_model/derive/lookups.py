"""Lookups shared by the query modules (design/derive-queries.md, decision 0021).

Every query takes the model first, then one positional identity argument, then keyword-only
arguments. An identity argument that is not a record of that kind in the model raises
`SchemaError` (as `designation.py` does); an empty result means "exists, has nothing".
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import (
    Id,
    Model,
    key_text,
    parent_chain,
)
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet
from fransys_model.vocab.markings import marking_key
from fransys_model.vocab.membership import item_chain, require
from fransys_model.vocab.tables import (
    aspect_nodes,
    facets_of,
    functions,
    items,
    parts,
    placements,
    ports,
    units,
)
from fransys_model.vocab.terminals import terminal_items
from fransys_model.vocab.unit_index import descendants
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Port
lazy from fransys_model.vocab.templates import FunctionTemplate

from .indexes import build_indexes

if TYPE_CHECKING:
    from fransys_model.vocab.connectivity import Conductor, Net
    from fransys_model.vocab.core import Function, Unit
    from fransys_model.vocab.enums import PortRole

    from .indexes import Indexes


__all__ = [
    "cable_end_owner",
    "channel_devices",
    "conductors_by_role",
    "connector_facets",
    "descendants",
    "effective_placement",
    "item_description",
    "item_location",
    "item_of_port",
    "list_context",
    "location_label",
    "net_name",
    "no_conductor_at",
    "pin_order",
    "position_rank",
    "require",
    "terminal_items",
    "unit_chain",
]


def net_name(net: Net) -> str:
    """The name a net goes by in a netlist: `Net.name`, else its authoring key joined by `/`."""
    return net.name if net.name is not None else key_text(net)


def pin_order(
    marking: str, port: Id[Port]
) -> tuple[tuple[tuple[int, int, str], ...], str, Id[Port]]:
    """The sort key of a pin: `marking_key` (digit runs by value, `A2` before `A10`), then the port.

    The marking text and the port id break ties; no designation is parsed. Shared by
    `connector_rows`, `harness_cables`, `overview_graph` and `fn.pins`.
    """
    return (marking_key(marking), marking, port)


def connector_facets(model: Model) -> frozendict[Id[FunctionTemplate], ConnectorFacet]:
    """Every `connector` facet by the function template it describes."""
    return frozendict({facet.subject: facet for facet in facets_of(model, ConnectorFacet).values()})


def effective_placement(model: Model, item: Id[Item], aspect: Aspect) -> Id[AspectNode] | None:
    """`item`'s own placement in `aspect`, else its nearest placed ancestor's, else `None`.

    Walks `Item.parent`, cycle-safe; a tie in one aspect resolves to the smallest placement id.

    Args:
        model: The model to read.
        item: The item whose effective placement is looked up.
        aspect: The aspect the placement is read in.

    Returns:
        The `AspectNode` id of the own or inherited placement, or `None` when there is none.

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    all_items = items(model)
    require(all_items.get(item), "item", item)
    indexes = build_indexes(model)
    all_placements = placements(model)
    nodes = aspect_nodes(model)
    for node in item_chain(model, item):
        found = sorted(
            placement_id
            for placement_id in indexes.placements_by_item.get(node, ())
            if nodes[all_placements[placement_id].node].aspect is aspect
        )
        if found:
            return all_placements[found[0]].node
    return None


def item_description(model: Model, item: Id[Item]) -> str:
    """The text a list shows for `item`: its own `description`, else its part's, else `""`.

    An item stores only the description its author wrote; the part's
    is never copied onto it. A part-less item with none authored has no text.

    Args:
        model: The model to read.
        item: The item whose list text is looked up.

    Returns:
        `item`'s own `description`, else its part's, else `""`.

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    record = require(items(model).get(item), "item", item)
    if record.description or record.part is None:
        return record.description
    return parts(model)[record.part].description


def item_location(model: Model, item: Id[Item]) -> Id[AspectNode] | None:
    """The `LOCATION` node `item` is placed at, own or inherited; `None` if it has none.

    `effective_placement` in the `LOCATION` aspect. A unit's list document with no location of its
    own reads its strip's or board's here.

    Args:
        model: The model to read.
        item: The item whose location is looked up.

    Returns:
        The `LOCATION` `AspectNode` id, own or inherited, or `None` when there is none.

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    return effective_placement(model, item, Aspect.LOCATION)


def list_context(
    model: Model, subject: Id[Item], *, location: Id[AspectNode] | None = None
) -> Id[AspectNode] | None:
    """The location a list's ends print short against: the document's, else `subject`'s own.

    `None` means no context: the list queries print full paths.

    Args:
        model: The model to read.
        subject: The strip or board item the list is of.
        location: The location document's own node, keyword-only; `None` falls back to `subject`'s.

    Returns:
        `location` when given, else `item_location` of `subject`; `None` when neither exists.

    Raises:
        SchemaError: `location` is `None` and `subject` is not an item of `model`.
    """
    return location if location is not None else item_location(model, subject)


def location_label(model: Model, item: Id[Item]) -> str | None:
    """The `label` of the `LOCATION` node `item` is placed at, own or inherited.

    Decision model-0040: reads through `effective_placement`, so an item with no location
    of its own reads its nearest placed ancestor's.
    """
    node = effective_placement(model, item, Aspect.LOCATION)
    return None if node is None else aspect_nodes(model)[node].label


def position_rank(module: Item) -> tuple[int, int]:
    """The order key of a module's `position` within its rack: every integer, then `None`.

    Shared by `plc_allocation` and `plc_rack_modules`, so the rack a query lists is the rack
    the allocation serves.
    """
    return (1, 0) if module.position is None else (0, module.position)


def unit_chain(model: Model, unit: Id[Unit]) -> list[Id[Unit]]:
    """`unit`, its parent, its parent's parent, ... up to the top-level ancestor.

    Cycle-safe: a repeat ends the walk (`UNIT_CYCLE` is the validator's, not this query's).
    """
    all_units = units(model)
    return list(parent_chain(lambda current: all_units[current].parent, unit))


def channel_devices(model: Model) -> dict[Id[Function], Id[Function]]:
    """Each bound channel function and the field function whose `plc_binding` names it.

    The smallest function id when several bindings name one channel.
    """
    bound: dict[Id[Function], Id[Function]] = {}
    for binding in facets_of(model, PlcBindingFacet).values():
        bound[binding.channel] = min(binding.subject, bound.get(binding.channel, binding.subject))
    return bound


def no_conductor_at(model: Model, port: Id[Port]) -> bool:
    """Whether no conductor (wire, jumper, cable core or link) ends at `port`.

    Unlike `unconnected_ports`, a mate or a declared net does not count (V1's unused pins).
    """
    return not build_indexes(model).conductors_by_port.get(port)


def item_of_port(model: Model, port: Id[Port]) -> Id[Item]:
    """The item whose function owns `port`."""
    return functions(model)[ports(model)[port].function].item


def cable_end_owner(model: Model, item: Id[Item]) -> Id[Item]:
    """`item`'s strip, when it is a terminal with a parent; else `item`.

    Shared by `derive.harness` and `cable_rows`, so a landing on a terminal resolves to one end.
    """
    if item in terminal_items(model):
        parent = items(model)[item].parent
        if parent is not None:
            return parent
    return item


def conductors_by_role(
    model: Model, idx: Indexes, terminal: Id[Item]
) -> dict[PortRole, set[Id[Conductor]]]:
    """The conductors on `terminal`'s ports, by the role of the port they land on."""
    by_role: dict[PortRole, set[Id[Conductor]]] = {}
    for function in idx.functions_by_item.get(terminal, ()):
        for port in idx.ports_by_function.get(function, ()):
            role = ports(model)[port].role
            landed = idx.conductors_by_port.get(port, ())
            if landed:
                by_role.setdefault(role, set()).update(landed)
    return by_role
