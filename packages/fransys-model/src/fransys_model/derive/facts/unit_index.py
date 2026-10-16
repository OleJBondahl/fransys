"""The per-model unit index: every unit, board and harness membership fact, computed once.

`derive.facts.units` reads it, so no query scans the items table per call (decision model-0067).
Cached on `model.digest`, like `vocab.closure`; the index holds ids only.
"""

import dataclasses
from collections import deque

from fransys_model.derive.facts.children import parent_item, unit_parent
from fransys_model.derive.facts.item_predicates import cable_items
from fransys_model.kernel import DIGEST_CACHE_SIZE, Model, digest_cached, index_ids, parent_chain
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.tables import boundaries, facets_of, items
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Function, Item, Unit
lazy from fransys_model.vocab.templates import Part
lazy from fransys_model.vocab.units import Boundary


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


def _external_items(model: Model, all_items: frozendict[Id[Item], Item]) -> frozenset[Id[Item]]:
    """The external items, one memoised `parent` walk per item; a `parent` cycle ends its walk."""
    verdict: dict[Id[Item], bool] = {}
    for start in all_items.values():
        path: list[Id[Item]] = []
        result = False
        # A `parent` naming no item ends the walk, as a root does.
        chain = parent_chain(
            lambda node: parent if (parent := parent_item(model, node)) in all_items else None,
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


def _own_roots(
    model: Model, all_items: frozendict[Id[Item], Item], external: frozenset[Id[Item]]
) -> dict[Id[Unit], list[Id[Item]]]:
    """Each unit -> its items whose parent is in no unit or another unit, external ones left out."""
    roots: dict[Id[Unit], list[Id[Item]]] = {}
    for record in all_items.values():
        if record.unit is None:
            continue
        parent = parent_item(model, record.id)
        is_root = parent is None or all_items[parent].unit != record.unit
        if is_root and record.id not in external:
            roots.setdefault(record.unit, []).append(record.id)
    return roots


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


def boundary_unit(model: Model, boundary: Id[Boundary]) -> Id[Unit]:
    """The unit `boundary` belongs to: the one reader of `Boundary.unit`."""
    return boundaries(model)[boundary].unit


@digest_cached(DIGEST_CACHE_SIZE)
def unit_index(model: Model) -> UnitIndex:
    """The `UnitIndex` of `model`, built once per digest and kept for the last few models.

    Every field holds ids only and is immutable, so a caller may keep or share it freely.
    """
    all_units = units_table(model)
    all_items = items(model)
    children = index_ids(
        (parent, unit) for unit in all_units if (parent := unit_parent(model, unit)) is not None
    )
    subtree_of = {unit: frozenset({unit, *descendants(children, unit)}) for unit in all_units}

    external = _external_items(model, all_items)
    by_unit = index_ids(
        (record.unit, record.id) for record in all_items.values() if record.unit is not None
    )
    roots = _own_roots(model, all_items, external)
    cable_items_ = cable_items(model)
    cables = index_ids(
        (parent, item)
        for item in all_items
        if item in cable_items_ and (parent := parent_item(model, item)) is not None
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


def item_unit(model: Model, item: Id[Item]) -> Id[Unit] | None:
    """The unit `item` is recorded in by `Item.unit`; `None` for the integrating script's own."""
    return items(model)[item].unit
