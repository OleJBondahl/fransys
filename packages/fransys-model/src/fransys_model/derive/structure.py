"""Board netlists, aspect trees, units and `ext` usage (design/derive-queries-structure.md).

`boundary`, `standalone`, `unit_items`, `unit_subtree` and `units` (units spec U8), and
`enclosing_boards` (decision model-0040), are re-exported from `vocab.membership`, the same
shape `derive.closure` already uses for `vocab.closure` (decision 0019): they live in `vocab`
because `vocab.validators.units` (U5) and `vocab.validators.connectivity` (design/connectivity.md)
read them, and a layer imports only the layers to its right.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.vocab import is_cable
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.membership import (
    boundary,
    enclosing_boards,
    is_sole_unit_root,
    standalone,
    unit_items,
    unit_subtree,
    units,
)
from fransys_model.vocab.tables import (
    aspect_nodes,
    conductors,
    functions,
    items,
    nets,
    parts,
    placements,
    ports,
)
from fransys_model.vocab.unit_index import unit_index
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Function, Item

from .closure import port_groups
from .designation import footprint_facet, item_designation
from .indexes import build_indexes
from .lookups import descendants, effective_placement, item_of_port, net_name, require
from .natural_order import natural_key
from .rows import BoardNetlist, ExtUsage, NetlistNet, NetlistPart

if TYPE_CHECKING:
    from fransys_model.vocab.connectivity import Net
    from fransys_model.vocab.core import Port

__all__ = [
    "board_netlist",
    "boards",
    "boundary",
    "enclosing_boards",
    "ext_usage",
    "is_sole_unit_root",
    "items_at",
    "schematic_functions",
    "standalone",
    "subtree",
    "unit_items",
    "unit_subtree",
    "units",
]


def board_netlist(model: Model, board: Id[Item]) -> BoardNetlist:
    """`board`'s parts, footprints and nets as one `BoardNetlist`.

    Parts are the footprinted descendants of `board`. Nets join its internal conductors and its
    declared nets, never `Mate`s; part designations are relative to `board`.

    Args:
        model: The model to read.
        board: The item whose netlist is built.

    Returns:
        A `BoardNetlist` (defined in `derive.rows`) for `board`.

    Raises:
        SchemaError: `board` is not an item of `model`, or it or a listed item has no designation.
    """
    require(items(model).get(board), "item", board)
    idx = build_indexes(model)
    below = descendants(idx.children_by_item, board)
    on_board = {board, *below}
    all_parts = parts(model)
    board_designation = item_designation(model, board)
    listed = []
    without_footprint = []
    for item_id in below:
        item = items(model)[item_id]
        if item.part is None:
            continue
        footprint = footprint_facet(model, item.part)
        if footprint is None:
            without_footprint.append(item_id)
            continue
        listed.append(
            NetlistPart(
                item=item_id,
                designation=item_designation(model, item_id, relative_to=board),
                mpn=all_parts[item.part].mpn,
                footprint_library=footprint.library,
                footprint_name=footprint.name,
                installed=item.installed,
            )
        )
    return BoardNetlist(
        board=board,
        board_designation=board_designation,
        parts=tuple(sorted(listed, key=lambda part: (natural_key(part.designation), part.item))),
        nets=_board_nets(model, board, on_board),
        without_footprint=tuple(without_footprint),
    )


def _board_nets(model: Model, board: Id[Item], on_board: set[Id[Item]]) -> tuple[NetlistNet, ...]:
    """`board_netlist`'s `nets` (decision model-0042): see its docstring for the rule."""

    def _on_board(port: Id[Port]) -> bool:
        return item_of_port(model, port) in on_board

    conductor_pairs = [
        (conductor.a, conductor.b)
        for conductor in conductors(model).values()
        if _on_board(conductor.a)
        and _on_board(conductor.b)
        and (conductor.carrier is None or conductor.carrier in on_board)
    ]
    on_board_nets = [
        net for net in nets(model).values() if net.ports and all(_on_board(p) for p in net.ports)
    ]
    declared_groups = [net.ports for net in on_board_nets]
    declared_by_port: dict[Id[Port], list[Id[Net]]] = {}
    for net in on_board_nets:
        for port in net.ports:
            declared_by_port.setdefault(port, []).append(net.id)
    net_by_id = {net.id: net for net in on_board_nets}
    found = []
    for group in port_groups([*conductor_pairs, *declared_groups]):
        declared_ids = {net_id for port in group.ports for net_id in declared_by_port.get(port, ())}
        name = (
            min((net_name(net_by_id[net_id]), net_id) for net_id in declared_ids)[0]
            if declared_ids
            else _undeclared_net_name(model, board, group.ports)
        )
        found.append(NetlistNet(name=name, pins=group.ports))
    return tuple(sorted(found, key=lambda net: (net.name, net.pins)))


def _undeclared_net_name(model: Model, board: Id[Item], pins: tuple[Id[Port], ...]) -> str:
    """KiCad's own auto-net form, `Net-(designation-pin)`, from the group's smallest pin.

    Smallest is `(item_designation(model, item, relative_to=board), Port.name, Port.id)`, in order.
    """
    all_ports = ports(model)

    def _key(port: Id[Port]) -> tuple[str, str, Id[Port]]:
        item = item_of_port(model, port)
        return (item_designation(model, item, relative_to=board), all_ports[port].name, port)

    designation, marking, _ = min(
        (_key(port) for port in pins), key=lambda k: (natural_key(k[0]), *k[1:])
    )
    return f"Net-({designation}-{marking})"


def boards(model: Model) -> tuple[Id[Item], ...]:
    """Every item whose `Part` carries a `pcb` facet, in `Id` order.

    `PcbFacet.subject` is a `Part`, not an item: an item is a board when its own `part` is one
    that carries the facet. Shared by `fransys`'s export enumeration
    and the pdf document contents, so the two never disagree about what a board is.

    Args:
        model: The model to read.

    Returns:
        Every board item's id, sorted.
    """
    pcb_parts = unit_index(model).pcb_parts
    return tuple(sorted(item.id for item in items(model).values() if item.part in pcb_parts))


def schematic_functions(model: Model) -> tuple[Id[Function], ...]:
    """Every `Function` the schematic engine actually attempts to draw, in `Id` order.

    Excludes a cable item's own function and every function on or under a board item
    (`enclosing_boards`), with two exceptions. A `CONNECTOR` function on or under a board is always
    drawn: the board is a black box on the cabinet page, its edge connectors are not. A
    non-`CONNECTOR` function stays when the nearest enclosing board `is_sole_unit_root`: a board
    that is the whole content of its `Unit` is drawn like any unit's set. One predicate for layout
    and render, since neither package may import the other.

    Args:
        model: The model to read.

    Returns:
        Every drawn function's id, sorted.
    """

    def excluded(item_id: Id[Item], kind: FunctionKind) -> bool:
        if is_cable(model, item_id):
            return True
        board_chain = enclosing_boards(model, item_id)
        if not board_chain or kind is FunctionKind.CONNECTOR:
            return False
        return not is_sole_unit_root(model, board_chain[-1])

    return tuple(
        sorted(
            function.id
            for function in functions(model).values()
            if not excluded(function.item, function.kind)
        )
    )


def subtree(model: Model, node: Id[AspectNode]) -> tuple[Id[AspectNode], ...]:
    """Every descendant of `node` by `AspectNode.parent`, `node` excluded, sorted by id.

    Follows `parent` whatever the aspect (`ASPECT_CROSS_PARENT` is the validator's) and is
    cycle-safe.

    Args:
        model: The model to read.
        node: The aspect node whose descendants are listed.

    Returns:
        Every descendant's id, sorted.

    Raises:
        SchemaError: `node` is not an aspect node of `model`.
    """
    require(aspect_nodes(model).get(node), "aspect_node", node)
    return tuple(descendants(build_indexes(model).nodes_by_parent, node))


def items_at(model: Model, node: Id[AspectNode]) -> tuple[Id[Item], ...]:
    """Every item at `node` or at a node in `subtree(model, node)`, once each, sorted by id.

    An item counts by its own `Placement`, else by its nearest placed ancestor's
    (`effective_placement`): a board's own component is listed at the board's location or group.

    Args:
        model: The model to read.
        node: The aspect node (and its subtree) to list items at.

    Returns:
        Every item's id found at `node` or its subtree, once each, sorted.

    Raises:
        SchemaError: `node` is not an aspect node of `model`.
    """
    target = require(aspect_nodes(model).get(node), "aspect_node", node)
    below = {node, *subtree(model, node)}
    direct = {placement.item for placement in placements(model).values() if placement.node in below}
    inherited = {
        item_id
        for item_id in items(model)
        if item_id not in direct and effective_placement(model, item_id, target.aspect) in below
    }
    return tuple(sorted(direct | inherited))


def ext_usage(model: Model) -> tuple[ExtUsage, ...]:
    """One `ExtUsage` per `(record kind, top-level ext key)` over every namespace.

    `subjects` are the record ids in id order, `count` their number, sorted by `(kind, key)`;
    nested keys inside an `ext` value are not walked. It keeps `ext` a tracked escape hatch
    rather than a silent second schema (design/kernel-records.md 5.3).

    Args:
        model: The model to read.

    Returns:
        One `ExtUsage` per `(record kind, top-level ext key)` found, sorted.
    """
    found: dict[tuple[str, str], list[Id[Any]]] = {}
    for kind, table in model.tables.items():
        for record in table.values():
            for key in record.ext:
                found.setdefault((kind, key), []).append(record.id)
    return tuple(
        ExtUsage(kind=kind, key=key, count=len(subjects), subjects=tuple(sorted(subjects)))
        for (kind, key), subjects in sorted(found.items())
    )
