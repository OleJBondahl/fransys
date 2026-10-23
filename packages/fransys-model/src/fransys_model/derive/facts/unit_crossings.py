"""Where conductors and mates leave a unit: their ends, the units they cross, the owners.

A crossing here is subtree arithmetic on `Item.unit`: an end on an item inside a unit's subtree
whose other item is outside it. That is not `units.crosses_unit` (different `Item.unit`).
"""

from fransys_model.derive.facts.unit_index import item_unit, unit_index
from fransys_model.derive.facts.units import standalone
from fransys_model.derive.facts.units import units as unit_ids
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.enums import Gender
from fransys_model.vocab.facets.connector import ConnectorFacet
from fransys_model.vocab.tables import (
    conductors,
    facets_of,
    functions,
    mates,
    ports,
    units,
    unused_boundaries,
)
lazy from fransys_model.vocab.core import Function, Item, Unit
lazy from fransys_model.vocab.units import UnusedBoundary

_GENDERED = frozenset({Gender.MALE, Gender.FEMALE})


@digest_cached(DIGEST_CACHE_SIZE)
def ends(model: Model) -> tuple[tuple[Id[Function], Id[Item], Id[Item], Id[object]], ...]:
    """Each conductor's then each mate's two ends as (function, its item, other item, record)."""
    all_functions, all_ports = functions(model), ports(model)
    found: list[tuple[Id[Function], Id[Item], Id[Item], Id[object]]] = []
    for record, fn_a, fn_b in (
        *(
            (c.id, all_ports[c.a].function, all_ports[c.b].function)
            for c in conductors(model).values()
        ),
        *((m.id, m.a, m.b) for m in mates(model).values()),
    ):
        item_a, item_b = all_functions[fn_a].item, all_functions[fn_b].item
        found += [(fn_a, item_a, item_b, record), (fn_b, item_b, item_a, record)]
    return tuple(found)


@digest_cached(DIGEST_CACHE_SIZE)
def _item_pairs(model: Model) -> dict[Id[Function], tuple[tuple[Id[Item], Id[Item]], ...]]:
    grouped: dict[Id[Function], list[tuple[Id[Item], Id[Item]]]] = {}
    for function, item, other, _record in ends(model):
        grouped.setdefault(function, []).append((item, other))
    return {function: tuple(pairs) for function, pairs in grouped.items()}


def end_crosses(
    model: Model, subtree: frozenset[Id[Unit]], item: Id[Item], other: Id[Item]
) -> bool:
    """Whether an end on `item` leaves the unit whose subtree is `subtree` for `other`."""
    return item_unit(model, item) in subtree and item_unit(model, other) not in subtree


def crossed_units(model: Model, item: Id[Item], other: Id[Item]) -> tuple[Id[Unit], ...]:
    """The units holding `item` in their subtree that an end from `item` to `other` leaves."""
    index = unit_index(model)
    home = item_unit(model, item)
    held = () if home is None else index.containing.get(home, ())
    return tuple(unit for unit in held if end_crosses(model, index.subtree_of[unit], item, other))


def crosses_out_of(model: Model, unit: Id[Unit], function: Id[Function]) -> bool:
    """Whether a conductor or mate end on `function` leaves `unit`; declared `Net`s do not count."""
    subtree = unit_index(model).subtree_of[unit]
    return any(
        end_crosses(model, subtree, item, other)
        for item, other in _item_pairs(model).get(function, ())
    )


def offered_up(model: Model, unit: Id[Unit], function: Id[Function]) -> bool:
    """Whether a standalone unit enclosing `unit` holds `function` as its boundary (model-0184)."""
    index = unit_index(model)
    return any(
        function in index.boundary_of[outer] and standalone(model, outer)
        for outer in index.containing[unit] - {unit}
    )


def declared_owners(model: Model, unused: UnusedBoundary, owners: list[Id[Unit]]) -> list[Id[Unit]]:
    """The `owners` of the function whose instance carries the declaration (model-0210).

    An owner counts when its key is the declaring scope or a direct child of it; none: all.
    """
    scope, all_units = unused.key[:-2], units(model)
    near = [
        unit
        for unit in owners
        if all_units[unit].key[: len(scope)] == scope
        and len(all_units[unit].key) - 1 <= len(scope) + 1
    ]
    return near or owners


@digest_cached(DIGEST_CACHE_SIZE)
def open_boundaries(model: Model) -> tuple[tuple[Id[Unit], Id[Function]], ...]:
    """The (unit, boundary function) pairs joined across by nothing and not declared unused."""
    unused_functions = {unused.function for unused in unused_boundaries(model).values()}
    boundary_of = unit_index(model).boundary_of
    return tuple(
        (unit, function)
        for unit in unit_ids(model)
        if not standalone(model, unit)
        for function in boundary_of[unit]
        if not (crosses_out_of(model, unit, function) or function in unused_functions)
        if not offered_up(model, unit, function)
    )


@digest_cached(DIGEST_CACHE_SIZE)
def _genders(model: Model) -> dict[Id[Function], Gender]:
    by_template = {
        facet.subject: facet.gender for facet in facets_of(model, ConnectorFacet).values()
    }
    return {
        function.id: gender
        for function in functions(model).values()
        if function.template is not None
        and (gender := by_template.get(function.template)) in _GENDERED
    }


def function_gender(model: Model, function: Id[Function]) -> Gender | None:
    """The connector gender of `function` when its template states male or female, else `None`."""
    return _genders(model).get(function)
