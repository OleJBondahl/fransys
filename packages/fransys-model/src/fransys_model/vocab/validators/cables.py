"""Validator: cable cores conform to their cable product (design/facets.md, ROADMAP WP13)."""

from typing import TYPE_CHECKING, Final

from fransys_model.kernel import Finding, Severity, key_text
from fransys_model.vocab.cables import is_cable
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.cable import CableProductFacet
from fransys_model.vocab.tables import conductors, facets_of, items

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.core import Item

CABLE_CORE_COUNT: Final[str] = "CABLE_CORE_COUNT"


def check_cables(model: Model) -> tuple[Finding, ...]:
    """Check each cable `Item`'s core `Conductor`s match its `cable_product` facet.

    `CABLE_CORE_COUNT`: cores differ from `len(core_colours)`; `WARNING` if fewer, `ERROR` if more.
    Subjects the cable item and its product facet; findings sorted by `(code, subjects, message)`.
    """
    products = {facet.subject: facet for facet in facets_of(model, CableProductFacet).values()}
    cores: dict[Id[Item], list[Conductor]] = {}
    for conductor in conductors(model).values():
        if conductor.kind is ConductorKind.CORE and conductor.carrier is not None:
            cores.setdefault(conductor.carrier, []).append(conductor)
    found: list[Finding] = []
    for cable in items(model).values():
        if not is_cable(model, cable.id):
            continue
        product = products.get(cable.part) if cable.part is not None else None
        if product is None:
            continue
        have, want = len(cores.get(cable.id, [])), len(product.core_colours)
        if have != want:
            found.append(
                Finding(
                    code=CABLE_CORE_COUNT,
                    severity=Severity.WARNING if have < want else Severity.ERROR,
                    subjects=(cable.id, product.id),
                    message=(
                        f"cable {key_text(cable)} carries {have} cores, its product has {want}"
                    ),
                )
            )
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects, f.message)))
