"""Derived lookup tables over a `Model` (design/derive.md)."""

import dataclasses
from typing import Any

from fransys_model.kernel import (
    DIGEST_CACHE_SIZE,
    Id,
    Model,
    digest_cached,
    index_ids,
    namespace_of,
)
from fransys_model.vocab.tables import (
    aspect_nodes,
    conductors,
    facet_subject,
    functions,
    items,
    nets,
    placements,
    ports,
)
lazy from fransys_model.vocab.aspects import AspectNode, Placement
lazy from fransys_model.vocab.connectivity import Conductor, Net
lazy from fransys_model.vocab.core import Function, Item, Port
lazy from fransys_model.vocab.templates import Part


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Indexes:
    """Every lookup table `derive` needs more than once, built together off one `Model`.

    Each maps a record to the ids that refer to it, in `Id` order; a record nothing refers to
    has no entry, so read one with `.get(key, ())`. `facets_by_subject` holds facets of every
    kind, found through the `subject` field their kind declared.

    Not a `@value`: it is never nested in a record, and its tables are keyed by `Id`,
    outside the closed set `@value` enforces.

    Never stored in the model: call `build_indexes` again, or rely on
    its per-digest cache, rather than threading an `Indexes` value through a pass.
    """

    functions_by_item: frozendict[Id[Item], tuple[Id[Function], ...]]
    ports_by_function: frozendict[Id[Function], tuple[Id[Port], ...]]
    conductors_by_port: frozendict[Id[Port], tuple[Id[Conductor], ...]]
    nets_by_port: frozendict[Id[Port], tuple[Id[Net], ...]]
    items_by_part: frozendict[Id[Part], tuple[Id[Item], ...]]
    children_by_item: frozendict[Id[Item], tuple[Id[Item], ...]]
    facets_by_subject: frozendict[Id[Any], tuple[Id[Any], ...]]
    placements_by_item: frozendict[Id[Item], tuple[Id[Placement], ...]]
    nodes_by_parent: frozendict[Id[AspectNode], tuple[Id[AspectNode], ...]]


@digest_cached(DIGEST_CACHE_SIZE)
def build_indexes(model: Model) -> Indexes:
    """Build every index together off `model`.

    Cached on `model.digest`, holding the last few results: two calls with an equal digest
    return the identical `Indexes` object, so a caller never has to thread it through by hand.
    The digest ignores origins and aliases, which no index reads, and an `Indexes` holds only
    ids, so equal digests mean equal results. Identity is guaranteed within one thread.
    """
    return Indexes(
        functions_by_item=index_ids((f.item, f.id) for f in functions(model).values()),
        ports_by_function=index_ids((p.function, p.id) for p in ports(model).values()),
        conductors_by_port=index_ids(
            (end, c.id) for c in conductors(model).values() for end in (c.a, c.b)
        ),
        nets_by_port=index_ids((port, n.id) for n in nets(model).values() for port in n.ports),
        items_by_part=index_ids(
            (i.part, i.id) for i in items(model).values() if i.part is not None
        ),
        children_by_item=index_ids(
            (i.parent, i.id) for i in items(model).values() if i.parent is not None
        ),
        facets_by_subject=index_ids(
            (facet_subject(facet), facet.id)
            for kind, table in model.tables.items()
            if namespace_of(kind) == "facet"
            for facet in table.values()
        ),
        placements_by_item=index_ids((p.item, p.id) for p in placements(model).values()),
        nodes_by_parent=index_ids(
            (n.parent, n.id) for n in aspect_nodes(model).values() if n.parent is not None
        ),
    )
