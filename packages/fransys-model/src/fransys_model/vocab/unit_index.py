"""The per-model unit index: every unit, board and harness membership fact, computed once.

`vocab.membership` reads it, so no query scans the items table per call (decision model-0067).
Cached on `model.digest`, like `vocab.closure`; the index holds ids only.
"""

import dataclasses
from collections import deque
from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, Model, digest_cached, index_ids, parent_chain

from .cables import cable_items
from .facets.pcb import PcbFacet
from .tables import boundaries, facets_of, items
from .tables import units as units_table

if TYPE_CHECKING:
    from fransys_model.kernel import Id

    from .core import Function, Item, Unit
    from .templates import Part


def descendants[K](children: frozendict[Id[K], tuple[Id[K], ...]], root: Id[K]) -> list[Id[K]]:
    """Every descendant of `root` by `children`, `root` excluded, sorted; a repeat ends a branch."""
    seen = {root}
    found: list[Id[K]] = []
    queue = deque([root])
    while queue:
        for child in children.get(queue.popleft(), ()):
            if child not in seen:
                seen.add(child)
                found.append(child)
                queue.append(child)
    return sorted(found)


@dataclasses.dataclass(frozen=True, slots=True)
class UnitIndex:
    """Every per-unit and per-item membership fact of one model, for the one digest."""

    # Each unit -> itself and every unit whose `parent` chain reaches it; cycle-safe.
    subtree_of: frozendict[Id[Unit], frozenset[Id[Unit]]]
    # Each unit -> the items whose `unit` is in its subtree; a unit with no items maps to empty.
    items_of: frozendict[Id[Unit], frozenset[Id[Item]]]
    # Every item that is external: it or an ancestor by `Item.parent` has `external=True`.
    external: frozenset[Id[Item]]
    # Each unit -> its own root items in the items table's order; a unit with none maps to `()`.
    own_roots: frozendict[Id[Unit], tuple[Id[Item], ...]]
    # Each item with a cable child (is_cable, model-0108) -> those children in `Id` order; no
    # entry otherwise.
    cable_children: frozendict[Id[Item], tuple[Id[Item], ...]]
    # The parts that carry a `pcb` facet.
    pcb_parts: frozenset[Id[Part]]
    # Each unit -> the units whose `subtree_of` holds it, itself included. A unit id the units
    # table does not hold is no key: read `.get(unit, frozenset())` (an item whose `unit` is
    # `None` or unknown is in no unit's subtree).
    containing: frozendict[Id[Unit], frozenset[Id[Unit]]]
    # Each unit -> the functions of its `Boundary` records, once each in `Id` order; `()` if none.
    boundary_of: frozendict[Id[Unit], tuple[Id[Function], ...]]


def _external_items(all_items: frozendict[Id[Item], Item]) -> frozenset[Id[Item]]:
    """The external items, one memoised `parent` walk per item; a `parent` cycle ends its walk."""
    verdict: dict[Id[Item], bool] = {}
    for start in all_items.values():
        path: list[Id[Item]] = []
        result = False
        # A `parent` naming no item ends the walk, as a root does.
        chain = parent_chain(
            lambda node: all_items[node].parent if all_items[node].parent in all_items else None,
            start.id,
        )
        for node_id in chain:
            known = verdict.get(node_id)
            if known is not None:
                result = known
                break
            path.append(node_id)
            if all_items[node_id].external:
                result = True
                break
        for item_id in path:
            verdict[item_id] = result
    return frozenset(item_id for item_id, is_external in verdict.items() if is_external)


def _containing(
    subtree_of: dict[Id[Unit], frozenset[Id[Unit]]],
) -> frozendict[Id[Unit], frozenset[Id[Unit]]]:
    """Each unit -> the units whose subtree holds it, by inverting `subtree_of` once."""
    above: dict[Id[Unit], set[Id[Unit]]] = {unit: set() for unit in subtree_of}
    for unit, subtree in subtree_of.items():
        for below in subtree:
            above[below].add(unit)
    return frozendict({unit: frozenset(holders) for unit, holders in above.items()})


def _boundary_of(
    model: Model, all_units: frozendict[Id[Unit], Unit]
) -> frozendict[Id[Unit], tuple[Id[Function], ...]]:
    """Each unit -> its boundary functions, one pass over the `Boundary` table."""
    grouped = index_ids({(record.unit, record.function) for record in boundaries(model).values()})
    return frozendict({unit: grouped.get(unit, ()) for unit in all_units})


@digest_cached(DIGEST_CACHE_SIZE)
def unit_index(model: Model) -> UnitIndex:
    """The `UnitIndex` of `model`, built once per digest and kept for the last few models.

    Every field holds ids only and is immutable, so a caller may keep or share it freely.
    """
    all_units = units_table(model)
    all_items = items(model)
    children = index_ids(
        (unit.parent, unit.id) for unit in all_units.values() if unit.parent is not None
    )
    subtree_of = {unit: frozenset({unit, *descendants(children, unit)}) for unit in all_units}

    external = _external_items(all_items)
    by_unit = index_ids(
        (record.unit, record.id) for record in all_items.values() if record.unit is not None
    )
    roots: dict[Id[Unit], list[Id[Item]]] = {}
    for record in all_items.values():
        if record.unit is None:
            continue
        is_root = record.parent is None or all_items[record.parent].unit != record.unit
        if is_root and record.id not in external:
            roots.setdefault(record.unit, []).append(record.id)

    cable_items_ = cable_items(model)
    cables = index_ids(
        (record.parent, record.id)
        for record in all_items.values()
        if record.parent is not None and record.id in cable_items_
    )

    return UnitIndex(
        containing=_containing(subtree_of),
        boundary_of=_boundary_of(model, all_units),
        subtree_of=frozendict(subtree_of),
        items_of=frozendict(
            {
                unit: frozenset(item for below in subtree for item in by_unit.get(below, ()))
                for unit, subtree in subtree_of.items()
            }
        ),
        external=external,
        own_roots=frozendict({unit: tuple(roots.get(unit, ())) for unit in all_units}),
        cable_children=cables,
        pcb_parts=frozenset(facet.subject for facet in facets_of(model, PcbFacet).values()),
    )
