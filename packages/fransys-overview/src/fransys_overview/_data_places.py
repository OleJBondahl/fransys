"""The members of a place box of the location fold, by table index (O9, O14).

They come from `derive.location_fold`: the page lists them and recomputes no place membership.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import location_fold, unit_location
from fransys_model.layout import OverviewRefKind
from fransys_model.vocab import aspect_nodes

if TYPE_CHECKING:
    from fransys_model.derive import ViewBox
    from fransys_model.kernel import Id, Model

    from ._data import _Tables


def holds_of(tables: _Tables, box: ViewBox) -> list[list[Any]] | None:
    """`[[ref, label]]` per member of a place box, `ref` `['unit'|'item', ix]`, else `None`."""
    ref = box.key.ref
    fold = location_fold(tables.model)
    if ref.kind is not OverviewRefKind.PLACE or box.key.at is not None or fold is None:
        return None
    place = next(b for b in fold.boxes if b.place == ref.node)
    return [_member(tables, member) for member in place.boxes]


def _member(tables: _Tables, member: Id[Any]) -> list[Any]:
    if member.kind == "unit":
        return [["unit", tables.unit_ix[member]], tables.unit_label[member]]
    node = tables.nodes[tables.item_ix[member]]
    return [["item", tables.item_ix[member]], node.designation or node.description]


def unit_place_label(model: Model, unit: Id[Any]) -> str | None:
    """The label of the location node `unit` is placed at (`derive.unit_location`), else `None`."""
    node = unit_location(model, unit)
    return None if node is None else aspect_nodes(model)[node].label
