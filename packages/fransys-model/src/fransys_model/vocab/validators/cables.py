"""Validator: cable cores conform to their cable product (design/facets.md)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity
from fransys_model.vocab.cables import is_cable
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet, OpenCoreFacet
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import conductors, facets_of, items

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item
    from fransys_model.vocab.templates import Part

CABLE_CORE_COUNT: Final[str] = "CABLE_CORE_COUNT"
CORE_INDEX_PAST_PRODUCT: Final[str] = "CORE_INDEX_PAST_PRODUCT"


def _past_product(model: Model, products: dict[Id[Part], CableProductFacet]) -> list[Finding]:
    """`CORE_INDEX_PAST_PRODUCT`: a wired core numbered beyond its cable product's core count."""
    owners = conductors(model)
    cables = items(model)
    found: list[Finding] = []
    for facet in facets_of(model, CoreFacet).values():
        core = owners.get(facet.subject)
        if core is None or core.carrier is None or core.carrier not in cables:
            continue
        cable = cables[core.carrier]
        product = products.get(cable.part) if cable.part else None
        if product is None or 1 <= facet.index <= len(product.core_colours):
            continue
        want = len(product.core_colours)
        found.append(
            Finding(
                code=CORE_INDEX_PAST_PRODUCT,
                severity=Severity.ERROR,
                subjects=(cable.id, core.id),
                message=(
                    f"cable {ref(cable)} has core {facet.index}, its product has {want} cores: "
                    f"use a core from 1 to {want} or a part with more cores"
                ),
            )
        )
    return found


def check_cables(model: Model) -> tuple[Finding, ...]:
    """Check each cable `Item`'s core `Conductor`s match its `cable_product` facet.

    `CABLE_CORE_COUNT`: wired plus open cores differ from `len(core_colours)`, `WARNING` if fewer,
    `ERROR` if more. `CORE_INDEX_PAST_PRODUCT`: a core index outside the product. Sorted.
    """
    products = {facet.subject: facet for facet in facets_of(model, CableProductFacet).values()}
    counts: dict[Id[Item], int] = {}
    for conductor in conductors(model).values():
        if conductor.kind is ConductorKind.CORE and conductor.carrier is not None:
            counts[conductor.carrier] = counts.get(conductor.carrier, 0) + 1
    for opened in facets_of(model, OpenCoreFacet).values():
        counts[opened.subject] = counts.get(opened.subject, 0) + 1
    found = _past_product(model, products)
    for cable in items(model).values():
        if not is_cable(model, cable.id):
            continue
        product = products.get(cable.part) if cable.part is not None else None
        if product is None:
            continue
        have, want = counts.get(cable.id, 0), len(product.core_colours)
        if have != want:
            found.append(
                Finding(
                    code=CABLE_CORE_COUNT,
                    severity=Severity.WARNING if have < want else Severity.ERROR,
                    subjects=(cable.id, product.id),
                    message=(
                        f"cable {ref(cable)} carries {have} cores, its product has {want}"
                        + (": wire it, or mark it with W1.spare(...)" if have < want else "")
                    ),
                )
            )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
