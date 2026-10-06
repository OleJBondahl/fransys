"""Whether an item is a cable: its part carries a `cable_product` facet (RW4, decision model-0108).

The one predicate every reader in this codebase eventually switches to. It reads exactly one
fact: whether `item`'s `Item.part` carries a `CableProductFacet`. It reads nothing else -- not
`category`, and not the item's own `CableFacet`, which records only the as-installed length of a
cable already known to be one, and stays that way (design/facets.md and
design/examples.md 11). Lives in `vocab`, not `derive`: `vocab.validators.cables` must
read it, and a layer imports only the layers to its right (`derive` -> `layout` -> `vocab` ->
`kernel`, design/foundations.md 4), so `vocab` never imports `derive`. `derive.reports`'s
`_cable_products_by_part`/`_cores_by_cable` (decision model-0105) answer a different question -- a
caller-supplied cable's own product and core facts -- not this one.
"""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached

from .facets.cable import CableProductFacet
from .tables import facets_of, items
lazy from .core import Item


@digest_cached(DIGEST_CACHE_SIZE)
def cable_items(model: Model) -> frozenset[Id[Item]]:
    """Every item whose part carries a `cable_product` facet, built once per digest.

    The one selection rule behind `is_cable`: an item is in this set exactly when its `Item.part`
    is one of the parts a `CableProductFacet` names as `subject`. Reads nothing else -- not
    `category`, not the item's own `CableFacet` (installed length only).

    Args:
        model: The model to read.

    Returns:
        Every item id whose part carries a `cable_product` facet.
    """
    cable_parts = {facet.subject for facet in facets_of(model, CableProductFacet).values()}
    return frozenset(item.id for item in items(model).values() if item.part in cable_parts)


def is_cable(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is a cable: `item in cable_items(model)`.

    The one fact that decides it is whether `item`'s `Part` carries a `cable_product` facet.
    Reads nothing else: not `category`, not the item's own `CableFacet`, which records only the
    as-installed length of a cable and stays that way.

    Args:
        model: The model to read.
        item: The item to check.

    Returns:
        `True` when `item`'s part carries a `cable_product` facet.
    """
    return item in cable_items(model)
