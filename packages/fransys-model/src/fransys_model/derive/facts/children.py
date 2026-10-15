"""The one reader of `Item.parent` as a children list: what hangs below an item."""

from typing import cast

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached, index_ids
from fransys_model.vocab.tables import items
lazy from fransys_model.vocab.core import Item


@digest_cached(DIGEST_CACHE_SIZE)
def children_index(model: Model) -> frozendict[Id[Item], tuple[Id[Item], ...]]:
    """Every item's children by `Item.parent`, in `Id` order."""
    pairs = ((i.parent, i.id) for i in items(model).values() if i.parent is not None)
    return cast("frozendict[Id[Item], tuple[Id[Item], ...]]", index_ids(pairs))


def child_items(model: Model, item: Id[Item]) -> tuple[Id[Item], ...]:
    """The ids of `item`'s children by `Item.parent`, in `Id` order; empty for a leaf."""
    return children_index(model).get(item, ())


def parent_item(model: Model, item: Id[Item]) -> Id[Item] | None:
    """The id of `item`'s parent by `Item.parent`; `None` for a root."""
    return items(model)[item].parent
