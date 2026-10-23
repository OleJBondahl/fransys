"""The accessory that declares its functions open on purpose (model-0333, designer ruling 25)."""

from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import unused_boundaries
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item


@digest_cached(DIGEST_CACHE_SIZE)
def _items_declared_unused(model: Model) -> frozenset[Id[Item]]:
    """Every item with a function whose every function carries an `UnusedBoundary`."""
    declared = {unused.function for unused in unused_boundaries(model).values()}
    by_item = build_indexes(model).functions_by_item
    return frozenset(
        item for item, owned in by_item.items() if owned and all(f in declared for f in owned)
    )


def declares_all_unused(model: Model, item: Id[Item]) -> bool:
    """Whether `item` has functions and every one is declared open on purpose (`unused=True`).

    A tuple that names only some of the functions leaves it `False`. A part with no function is
    `False`: its bars never apply.
    """
    return item in _items_declared_unused(model)
