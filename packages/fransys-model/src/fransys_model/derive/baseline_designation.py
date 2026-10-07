"""The listing's designation and cross-unit port texts (baseline spec L2): `unit_designation`."""

from typing import TYPE_CHECKING, cast

from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.membership import boundary, unit_own_roots
from fransys_model.vocab.tables import (
    aspect_nodes,
    functions,
    items,
    ports,
)
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .designation import (
    _own_designation,
    _segment,
    printed_designation,
    reference_leaves,
    terminal_of,
)
from .instance_tag import instance_name, instance_tags
from .unit_nodes import SIGNS, chain_up

if TYPE_CHECKING:
    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.core import Function, Port


# -- unit_designation (L2) -------------------------------------------------------------------


def _own_location_leaves(model: Model, unit: Id[Unit]) -> set[Id[AspectNode]]:
    leaves: set[Id[AspectNode]] = set()
    for item in items(model).values():
        if item.unit != unit:
            continue
        leaf = reference_leaves(model, item.id).get(Aspect.LOCATION)
        if leaf is not None:
            leaves.add(leaf.id)
    return leaves


def _shared_prefix(
    common: list[Id[AspectNode]], chain: list[Id[AspectNode]]
) -> list[Id[AspectNode]]:
    shared = 0
    for own, other in zip(common, chain, strict=False):
        if own != other:
            break
        shared += 1
    return common[:shared]


def _common_location(model: Model, unit: Id[Unit] | None) -> Id[AspectNode] | None:
    """The deepest location that holds every located item of `unit`'s own items.

    Own items only, each read via `reference_leaves`; an unlocated item does not count.
    `unit=None` (the system listing) gives `None`: a top-level item keeps its whole location.
    """
    if unit is None:
        return None
    nodes = aspect_nodes(model)
    leaves = _own_location_leaves(model, unit)
    if not leaves:
        return None
    chains = [list(reversed(list(chain_up(nodes, leaf)))) for leaf in leaves]
    common = chains[0]
    for chain in chains[1:]:
        common = _shared_prefix(common, chain)
    return common[-1] if common else None


def _location_keep(
    nodes: frozendict[Id[AspectNode], AspectNode],
    leaf: Id[AspectNode],
    common: Id[AspectNode] | None,
) -> frozenset[Id[AspectNode]]:
    """The nodes of `leaf`'s chain strictly below `common`; every node with `common=None`."""
    chain = list(chain_up(nodes, leaf))
    if common is None:
        return frozenset(chain)
    keep = []
    for node in chain:
        if node == common:
            break
        keep.append(node)
    return frozenset(keep)


def unit_designation(model: Model, unit: Id[Unit] | None, item: Id[Item]) -> str:
    """`item`'s designation relative to `unit` (baseline spec L2).

    `reference_designation`'s rule, except the `+` (location) segment drops `unit`'s own common
    location (`_common_location`); the `=` (group) segment is never truncated, as a group move
    changes the release. The product part is `printed_designation(unit=unit)` (UNIT-ID I4 R2).

    Args:
        model: The frozen model to read.
        unit: The unit the text is relative to; `None` for the system listing.
        item: The item to name.

    Returns:
        The designation text.
    """
    # Not `reference_designation(unit=unit)`'s `own_nodes` rule: that truncates both segments,
    # the wrong rule here, as it is meant for drawing inside the unit's own document set.
    nodes = aspect_nodes(model)
    leaves = reference_leaves(model, item)
    common = _common_location(model, unit)
    segments = []
    for aspect, sign in SIGNS.items():
        leaf = leaves.get(aspect)
        if leaf is None:
            continue
        keep = _location_keep(nodes, leaf.id, common) if aspect is Aspect.LOCATION else None
        segments.append(_segment(nodes, leaf, sign, keep=keep))
    return "".join(segments) + printed_designation(model, item, unit=unit)


# -- cross-unit rendering (a mate or conductor end on a nested unit's boundary) --------------


def _instance_prefix(model: Model, unit: Id[Unit] | None, owner_unit: Id[Unit]) -> str:
    """`"<instance name>/"` for the unit `owner_unit`, an instance nested somewhere in `unit`.

    The instance name is the smallest, in sort order, of its own root items' `unit_designation`
    in `unit` (baseline spec L2); a tagged instance is named by its tags instead (UT2).
    """
    if tags := instance_tags(model, owner_unit, unit):
        return f"{instance_name(tags)}/"
    roots = unit_own_roots(model, owner_unit)
    name = min(unit_designation(model, unit, root) for root in roots)
    return f"{name}/"


def _plain_port_text(model: Model, render_unit: Id[Unit] | None, port_id: Id[Port]) -> str:
    """`port_id` rendered relative to `render_unit`: a plain port, or a terminal's bare text."""
    record = ports(model)[port_id]
    fn = functions(model)[record.function]
    owner = items(model)[fn.item]
    if owner.parent is not None and terminal_of(model, owner.id) is not None:
        strip_text = unit_designation(model, render_unit, owner.parent)
        return f"{strip_text}:{_own_designation(model, owner.id)}"
    return f"{unit_designation(model, render_unit, owner.id)}:{record.name}"


def _cross_port_text(model: Model, unit: Id[Unit] | None, port_id: Id[Port]) -> str:
    """`port_id`'s baseline text for `unit`'s own listing (conductor ends).

    Plain against `unit` when its owner item is `unit`'s own; else against the owner's unit,
    prefixed `"<instance>/"` (a mate or conductor end on a nested unit's boundary).
    """
    record = ports(model)[port_id]
    fn = functions(model)[record.function]
    owner = items(model)[fn.item]
    if owner.unit == unit:
        return _plain_port_text(model, unit, port_id)
    # `_conductor_unit`'s U6 rule (or, for `unit=None`, the `owner.unit == unit` branch above)
    # guarantees `owner.unit` is a real unit here.
    owner_unit = cast("Id[Unit]", owner.unit)
    prefix = _instance_prefix(model, unit, owner_unit)
    return f"{prefix}{_plain_port_text(model, owner_unit, port_id)}"


def _cross_function_text(model: Model, unit: Id[Unit] | None, function_id: Id[Function]) -> str:
    """`function_id`'s baseline text for `unit`'s own listing (mate ends, baseline spec L2)."""
    fn = functions(model)[function_id]
    owner = items(model)[fn.item]
    if owner.unit == unit:
        return f"{unit_designation(model, unit, owner.id)}:{fn.name}"
    # `_lowest_common_unit` (or, for `unit=None`, the branch above) guarantees a real unit.
    owner_unit = cast("Id[Unit]", owner.unit)
    prefix = _instance_prefix(model, unit, owner_unit)
    return f"{prefix}{unit_designation(model, owner_unit, owner.id)}:{fn.name}"


def _net_port_text(
    model: Model, unit: Id[Unit] | None, direct_nested: frozenset[Id[Unit]], port_id: Id[Port]
) -> str | None:
    """`port_id`'s baseline text for a `nets` row, `None` when it is not a member port of `unit`.

    Member: a port on an item of `unit` itself, or on a boundary function of a unit nested in it.
    Anything else (several levels down, or no bearing on `unit`) is left out of the row.
    """
    record = ports(model)[port_id]
    fn = functions(model)[record.function]
    owner = items(model)[fn.item]
    if owner.unit == unit:
        return _plain_port_text(model, unit, port_id)
    if owner.unit in direct_nested and record.function in boundary(model, owner.unit):
        prefix = _instance_prefix(model, unit, owner.unit)
        return f"{prefix}{_plain_port_text(model, owner.unit, port_id)}"
    return None
