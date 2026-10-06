"""Symbol placements by function and page, with an item view standing in for its functions."""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.layout import PlacementView, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab.core import Function, Item


@digest_cached(DIGEST_CACHE_SIZE)
def placements_by_function_page(
    model: Model,
) -> Mapping[tuple[Id[Function], Id[Page]], SymbolPlacement]:
    """Every `SymbolPlacement` by function and page, last write winning (a replica adds a second).

    An item view also answers for its item's functions drawn in it (layout-0123).
    """
    table = functions(model)
    placements = list(layout_of(model, SymbolPlacement).values())
    found = {(one.function, one.page): one for one in placements}
    by_item: dict[Id[Item], list[Id[Function]]] = defaultdict(list)
    for function in table.values():
        by_item[function.item].append(function.id)
    for one in placements:
        if one.view is PlacementView.ITEM:
            for function in by_item[table[one.function].item]:
                found.setdefault((function, one.page), one)
    return found
