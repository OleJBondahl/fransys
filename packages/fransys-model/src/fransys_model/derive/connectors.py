"""Board connectors: the query behind a connector list.

See vocabulary.md 6 and derive-queries-structure.md.
"""

from typing import TYPE_CHECKING
lazy from collections.abc import Collection

from fransys_model.derive.facts.roles import function_role
from fransys_model.vocab.tables import functions, items, nets, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .designation import (
    connector_designation,
    connector_segment,
    end_outside_nested_unit,
    unit_list_context,
)
from .facts.mates import mate_port_of
from .far_ends import far_ends
from .indexes import build_indexes
from .location_text import port_designation_in, product_designation_in
from .lookups import connector_facets, descendants, net_name, pin_order, require
from .mate_rows import mate_partners
from .order import in_designation_order, natural_key
from .rows import ConnectorPin, ConnectorRow
from .unit_nodes import outside_unit

if TYPE_CHECKING:
    from fransys_model.vocab.connectivity import Net
    from fransys_model.vocab.core import Function, Port
    from fransys_model.vocab.facets.connector import ConnectorFacet

    from .indexes import Indexes


def connector_rows(
    model: Model,
    board: Id[Item],
    *,
    unit: Id[Unit] | None = None,
    context: Id[AspectNode] | None = None,
) -> tuple[ConnectorRow, ...]:
    """One `ConnectorRow` per connector of `board`, with its pins, nets and mate.

    A connector is a `connector`-kind `Function` of `board` or a descendant whose template carries a
    `connector` facet. `designation` is `connector_designation`: the item's own designation, or
    `<item designation>-<label>` when the item has two or more connector functions. Rows sort by
    `(designation, connector id)`. `mate` is the other end of a `Mate`; a pin's `mate_port` is the
    port of equal name on it, and its `net` the declared net listing its port. `pins` sort by
    marking, digits first by value. `context` (default `None`, full paths) is the location the list
    prints against. `unit` is the unit whose document prints it: inside it reads unit-relative, and
    for a nested `unit` a mate outside its subtree prints `None`; `context` is ignored once `unit`
    has one.

    Raises:
        SchemaError: `board` is not an item of `model`, or an item shown has no designation.
    """
    require(items(model).get(board), "item", board)
    idx = build_indexes(model)
    on_board = {board, *descendants(idx.children_by_item, board)}
    return connector_rows_of(model, on_board, unit=unit, context=context)


def connector_items(model: Model) -> tuple[Id[Item], ...]:
    """Every item with a connector function of a `connector`-faceted template, designation order.

    The items a connector table can be headed by; `unit_connector_items` keeps a unit's own.
    """
    shapes = connector_facets(model)
    found = {
        function.item
        for function in functions(model).values()
        if function_role(model, function.id).pin_group
        and function.template is not None
        and function.template in shapes
    }
    return in_designation_order(model, found)


def unit_connector_items(model: Model, unit: Id[Unit]) -> tuple[Id[Item], ...]:
    """The `connector_items` `unit` owns directly, never a nested unit's (as `unit_boards`)."""
    return tuple(item for item in connector_items(model) if items(model)[item].unit == unit)


def _declared_nets(model: Model) -> dict[Id[Port], list[tuple[str, Id[Net]]]]:
    """Each port with the declared nets that list it, as `(name, id)`."""
    declared: dict[Id[Port], list[tuple[str, Id[Net]]]] = {}
    for net in nets(model).values():
        for port in net.ports:
            declared.setdefault(port, []).append((net_name(net), net.id))
    return declared


def _connectors_on(model: Model, on_board: set[Id[Item]]) -> list[tuple[Function, ConnectorFacet]]:
    """Each connector function of the items `on_board` with its shape, in table order."""
    shapes = connector_facets(model)
    found = []
    for function in functions(model).values():
        shape = None if function.template is None else shapes.get(function.template)
        if (
            shape is not None
            and function_role(model, function.id).pin_group
            and function.item in on_board
        ):
            found.append((function, shape))
    return found


def connector_rows_of(
    model: Model,
    item_ids: Collection[Id[Item]],
    *,
    unit: Id[Unit] | None = None,
    context: Id[AspectNode] | None = None,
) -> tuple[ConnectorRow, ...]:
    """One `ConnectorRow` per connector function of exactly the items `item_ids`, sorted.

    `connector_rows` is this over a board and its descendants; the rest is its contract.
    """
    context = unit_list_context(model, unit, context)
    idx = build_indexes(model)
    declared = _declared_nets(model)
    partners = mate_partners(model)
    rows = []
    for function, shape in _connectors_on(model, set(item_ids)):
        mate = min(partners.get(function.id, ()), default=None)
        rows.append(
            ConnectorRow(
                connector=function.id,
                designation=connector_designation(model, function.id, unit=unit),
                style=shape.style,
                pincount=shape.pincount,
                gender=shape.gender,
                mate=mate,
                mate_designation=(
                    None
                    if mate is None
                    or end_outside_nested_unit(model, functions(model)[mate].item, unit)
                    else _mate_text(model, mate, context, unit)
                ),
                pins=_pins(model, idx, function.id, mate, declared, unit=unit, context=context),
            )
        )
    return tuple(sorted(rows, key=lambda row: (natural_key(row.designation), row.connector)))


def _mate_text(
    model: Model, mate: Id[Function], context: Id[AspectNode] | None, unit: Id[Unit] | None
) -> str:
    """The mate's connector as the list prints it: outside `unit`, its whole path (model-0143)."""
    item = functions(model)[mate].item
    if not outside_unit(model, item, unit):
        return connector_designation(model, mate, unit=unit)
    return product_designation_in(model, item, context, unit=unit) + connector_segment(model, mate)


def _pins(  # noqa: PLR0913 -- one connector's lookups, its unit and the list's context
    model: Model,
    idx: Indexes,
    connector: Id[Function],
    mate: Id[Function] | None,
    declared: dict[Id[Port], list[tuple[str, Id[Net]]]],
    *,
    unit: Id[Unit] | None,
    context: Id[AspectNode] | None,
) -> tuple[ConnectorPin, ...]:
    pins = []
    for port in idx.ports_by_function.get(connector, ()):
        marking = ports(model)[port].name
        mate_port = None if mate is None else mate_port_of(model, port, mate)
        blank = mate is not None and end_outside_nested_unit(
            model, functions(model)[mate].item, unit
        )
        pins.append(
            ConnectorPin(
                port=port,
                marking=marking,
                net=min(declared[port])[0] if port in declared else None,
                mate_port=mate_port,
                mate_port_designation=(
                    None
                    if mate_port is None or blank
                    else port_designation_in(model, mate_port, context, unit=unit)
                ),
                ends=_pin_ends(model, idx, port, mate_port, unit=unit, context=context),
            )
        )
    return tuple(sorted(pins, key=lambda pin: pin_order(pin.marking, pin.port)))


def _pin_ends(  # noqa: PLR0913 -- one pin's lookups, its unit and the list's context
    model: Model,
    idx: Indexes,
    port: Id[Port],
    mate_port: Id[Port] | None,
    *,
    unit: Id[Unit] | None,
    context: Id[AspectNode] | None,
) -> tuple[str, ...]:
    """The far ends of every conductor on `port` or its `mate_port`, as a terminal row's."""
    near = (port,) if mate_port is None else (port, mate_port)
    landed = tuple(c for n in near for c in idx.conductors_by_port.get(n, ()))
    return far_ends(model, near, landed, unit=unit, context=context)[1]
