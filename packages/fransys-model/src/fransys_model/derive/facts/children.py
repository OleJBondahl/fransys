"""The one readers of `Item.parent` (as a children list), `Unit.parent` and `AspectNode.parent`."""

from typing import cast

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached, index_ids
from fransys_model.vocab.tables import HasTables, aspect_nodes, items, units
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit


@digest_cached(DIGEST_CACHE_SIZE)
def children_index(model: HasTables) -> frozendict[Id[Item], tuple[Id[Item], ...]]:
    """Every item's children by `Item.parent`, in `Id` order."""
    pairs = ((i.parent, i.id) for i in items(model).values() if i.parent is not None)
    return cast("frozendict[Id[Item], tuple[Id[Item], ...]]", index_ids(pairs))


def child_items(model: Model, item: Id[Item]) -> tuple[Id[Item], ...]:
    """The ids of `item`'s children by `Item.parent`, in `Id` order; empty for a leaf."""
    return children_index(model).get(item, ())


def parent_item(model: HasTables, item: Id[Item]) -> Id[Item] | None:
    """The id of `item`'s parent by `Item.parent`; `None` for a root."""
    return items(model)[item].parent


def unit_parent(model: HasTables, unit: Id[Unit]) -> Id[Unit] | None:
    """The id of `unit`'s parent by `Unit.parent`; `None` for a root."""
    return units(model)[unit].parent


def aspect_parent(model: Model, node: Id[AspectNode]) -> Id[AspectNode] | None:
    """The id of `node`'s parent by `AspectNode.parent`; `None` for a root."""
    return aspect_nodes(model)[node].parent


def item_parents(model: Model) -> frozendict[Id[Item], Id[Item]]:
    """Each child item's parent item, in the order the items table gives the parents."""
    index = children_index(model)
    return frozendict({c: p for p in items(model) for c in index.get(p, ())})
