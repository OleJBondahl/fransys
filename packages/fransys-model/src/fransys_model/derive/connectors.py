"""Board connectors: the query behind a connector list.

See vocabulary.md 6 and derive-queries-structure.md.
"""

from typing import TYPE_CHECKING

from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions, items, mates, nets, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .designation import (
    connector_designation,
    connector_segment,
    end_outside_nested_unit,
    unit_list_context,
)
from .drawing_text import port_designation_in, product_designation_in
from .indexes import build_indexes
from .lookups import connector_facets, descendants, net_name, pin_order, require
from .rows import ConnectorPin, ConnectorRow
from .unit_nodes import outside_unit

if TYPE_CHECKING:
    from fransys_model.vocab.connectivity import Net
    from fransys_model.vocab.core import Function, Port

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
    context = unit_list_context(model, unit, context)
    idx = build_indexes(model)
    on_board = {board, *descendants(idx.children_by_item, board)}
    shapes = connector_facets(model)
    declared: dict[Id[Port], list[tuple[str, Id[Net]]]] = {}
    for net in nets(model).values():
        for port in net.ports:
            declared.setdefault(port, []).append((net_name(net), net.id))
    partners: dict[Id[Function], list[Id[Function]]] = {}
    for mate in mates(model).values():
        partners.setdefault(mate.a, []).append(mate.b)
        partners.setdefault(mate.b, []).append(mate.a)
    candidates = []
    for function in functions(model).values():
        shape = None if function.template is None else shapes.get(function.template)
        if shape is None or function.kind is not FunctionKind.CONNECTOR:
            continue
        candidates.append((function, shape))
    rows = []
    for function, shape in candidates:
        if function.item not in on_board:
            continue
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
    return tuple(sorted(rows, key=lambda row: (row.designation, row.connector)))


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
    mate_ports: dict[str, Id[Port]] = {}
    for port in () if mate is None else idx.ports_by_function.get(mate, ()):
        mate_ports.setdefault(ports(model)[port].name, port)
    pins = []
    for port in idx.ports_by_function.get(connector, ()):
        marking = ports(model)[port].name
        mate_port = mate_ports.get(marking)
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
            )
        )
    return tuple(sorted(pins, key=lambda pin: pin_order(pin.marking, pin.port)))
