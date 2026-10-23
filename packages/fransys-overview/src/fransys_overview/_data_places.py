"""The members of a place box of the location fold, by table index (O9, O14).

They come from `derive.location_fold`: the page lists them and recomputes no place membership.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    OverviewRefKind,
    location_place_title,
    node_label,
    place_members,
    unit_location,
    unit_system_designation,
)

if TYPE_CHECKING:
    from fransys_model.derive import ViewBox
    from fransys_model.kernel import Id, Model

    from ._data import _Tables


def holds_of(tables: _Tables, box: ViewBox) -> list[list[Any]] | None:
    """`[[ref, label]]` per member of a place box, `ref` `['unit'|'item', ix]`, else `None`."""
    members = place_members(tables.model, box)
    return None if members is None else [_member(tables, member) for member in members]


def _member(tables: _Tables, member: Id[Any]) -> list[Any]:
    if member.kind == "unit":
        return [["unit", tables.unit_ix[member]], tables.unit_label[member]]
    node = tables.nodes[tables.item_ix[member]]
    return [["item", tables.item_ix[member]], node.designation or node.description]


def place_label(model: Model, node: Id[Any]) -> str:
    """The class key of a place under "Colour by location": the node's label, as an item's is."""
    return node_label(model, node)


def unit_place_label(model: Model, unit: Id[Any]) -> str | None:
    """The label of the location node `unit` is placed at (`derive.unit_location`), else `None`."""
    node = unit_location(model, unit)
    return None if node is None else place_label(model, node)


def place_title(model: Model, box: ViewBox) -> str | None:
    """The panel title of a place box: `derive.location_place_title`, else `None`."""
    ref = box.key.ref
    if ref.kind is not OverviewRefKind.PLACE or ref.node is None:
        return None
    return location_place_title(model, ref.node)


def unit_system_label(model: Model, unit: Id[Any], label: str) -> str | None:
    """The unit's system designation when it differs from its printed `label`, else `None`."""
    name = unit_system_designation(model, unit)
    return None if name is None or name == label else name
