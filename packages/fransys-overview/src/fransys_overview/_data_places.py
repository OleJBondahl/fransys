"""The members of a place box of the location fold, by table index (O9, O14).

They come from `derive.location_fold`: the page lists them and recomputes no place membership.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    location_node_designation,
    location_place_title,
    place_members,
    unit_location,
    unit_system_designation,
)
from fransys_model.layout import OverviewRefKind
from fransys_model.vocab import Aspect, aspect_nodes

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
    return aspect_nodes(model)[node].label


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


def location_texts(model: Model) -> dict[str, str]:
    """Each location label (the class key) with the designation boxes and panels print for it."""
    texts: dict[str, str] = {}
    for node in aspect_nodes(model).values():
        if node.aspect is Aspect.LOCATION:
            texts.setdefault(node.label, location_node_designation(model, node.id))
    return texts


def unit_system_label(model: Model, unit: Id[Any], label: str) -> str | None:
    """The unit's system designation when it differs from its printed `label`, else `None`."""
    name = unit_system_designation(model, unit)
    return None if name is None or name == label else name
