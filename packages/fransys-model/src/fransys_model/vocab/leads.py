"""The connector items fitted on their parent's own leads (HA6, model-0172).

Lives in `vocab` so `derive.designation` reads one fact: a LEAD conductor joins a pin of the item
to a port of the item's parent device.
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, digest_cached

from .enums import ConductorKind
from .tables import conductors, functions, items, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from .core import Item, Port


def _owner(model: Model, port: Id[Port]) -> Id[Item]:
    return functions(model)[ports(model)[port].function].item


@digest_cached(DIGEST_CACHE_SIZE)
def _fitted_items(model: Model) -> frozenset[Id[Item]]:
    found: set[Id[Item]] = set()
    for conductor in conductors(model).values():
        if conductor.kind is not ConductorKind.LEAD:
            continue
        for here, there in ((conductor.a, conductor.b), (conductor.b, conductor.a)):
            item = _owner(model, here)
            if items(model)[item].parent == _owner(model, there):
                found.add(item)
    return frozenset(found)


def fitted_on_leads(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is a connector fitted on its parent's leads (HA5).

    True when a LEAD conductor ends in a port of `item` and its other end is a port of
    `item`'s `parent`. Unknown `item`: `False`.
    """
    return item in _fitted_items(model)
