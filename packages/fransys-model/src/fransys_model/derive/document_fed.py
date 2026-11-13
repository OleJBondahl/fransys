"""The top-level items a unit's interface strips feed: they print on the unit's pages (R316).

The old engine drew a motor outside the cabinet on the cabinet's pages, the by-others-on-unit-pages
convention (owner 2026-10-14). `document_sets` reads them to choose each set's one printer.
"""

from collections import defaultdict

from fransys_model.vocab.tables import conductors
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .facts.unit_index import item_unit
from .facts.units import item_root
from .lookups import item_of_port, strip_set
from .memo import Memo

__all__ = ["fed_items"]


def _links(model: Model) -> dict[Id[Item], set[Id[Item]]]:
    """Each root item to the root items a conductor joins it to."""
    links: dict[Id[Item], set[Id[Item]]] = defaultdict(set)
    for conductor in conductors(model).values():
        a = item_root(model, item_of_port(model, conductor.a))
        b = item_root(model, item_of_port(model, conductor.b))
        links[a].add(b)
        links[b].add(a)
    return links


_links_of = Memo(_links)


def _fed(model: Model, unit: Id[Unit]) -> frozenset[Id[Item]]:
    """The top-level items reached from `unit`'s own strips through top-level items alone."""
    links = _links_of(model)
    seen: set[Id[Item]] = set()
    todo = [item_root(model, s) for s in strip_set(model) if item_unit(model, s) == unit]
    while todo:
        for near in links.get(todo.pop(), ()):
            if near not in seen and item_unit(model, near) is None:
                seen.add(near)
                todo.append(near)
    return frozenset(seen)


fed_items = Memo(_fed)
