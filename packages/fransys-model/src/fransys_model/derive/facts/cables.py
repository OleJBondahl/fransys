"""The cable-product facts: a cable's product, its core counts, and where they fail the product."""

from fransys_model.derive.facts.cores import core_count, cores_past_product, is_core
from fransys_model.derive.facts.item_predicates import is_cable
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet, OpenCoreFacet
from fransys_model.vocab.tables import conductors, facets_of, items
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item
lazy from fransys_model.vocab.templates import Part


@digest_cached(DIGEST_CACHE_SIZE)
def cable_products_by_part(model: Model) -> frozendict[Id[Part], CableProductFacet]:
    """Every `CableProductFacet` by the part it describes, built once per model digest.

    The facet's `unique=True` allows at most one per part, so no first-match tie-break is needed.
    """
    return frozendict({f.subject: f for f in facets_of(model, CableProductFacet).values()})


def cable_product(model: Model, item: Id[Item]) -> CableProductFacet | None:
    """The `CableProductFacet` of `item`'s part, `None` when `item` is unknown or has none."""
    record = items(model).get(item)
    return (
        None
        if record is None or record.part is None
        else cable_products_by_part(model).get(record.part)
    )


@digest_cached(DIGEST_CACHE_SIZE)
def core_counts(model: Model) -> frozendict[Id[Item], int]:
    """Cores per cable: its wired cores plus its open cores."""
    counts: dict[Id[Item], int] = {}
    for conductor in conductors(model).values():
        if is_core(model, conductor.id) and conductor.carrier is not None:
            counts[conductor.carrier] = counts.get(conductor.carrier, 0) + 1
    for opened in facets_of(model, OpenCoreFacet).values():
        counts[opened.subject] = counts.get(opened.subject, 0) + 1
    return frozendict(counts)


@digest_cached(DIGEST_CACHE_SIZE)
def wired_cores_past_product(model: Model) -> tuple[tuple[Id[Item], Id[Conductor], int, int], ...]:
    """Each wired core numbered beyond its product, as (cable, core, index, product core count)."""
    found = []
    for facet in facets_of(model, CoreFacet).values():
        core = conductors(model).get(facet.subject)
        if core is None or core.carrier is None:
            continue
        product = cable_product(model, core.carrier)
        if product is not None and cores_past_product(core_count(product), facet.index):
            found.append((core.carrier, core.id, facet.index, core_count(product)))
    return tuple(found)


@digest_cached(DIGEST_CACHE_SIZE)
def core_count_gaps(model: Model) -> tuple[tuple[Id[Item], Id[CableProductFacet], int, int], ...]:
    """Each cable whose core count differs from its product's, as (cable, product, have, want)."""
    found = []
    for cable in items(model).values():
        product = cable_product(model, cable.id) if is_cable(model, cable.id) else None
        have = core_counts(model).get(cable.id, 0)
        if product is not None and have != core_count(product):
            found.append((cable.id, product.id, have, core_count(product)))
    return tuple(found)
