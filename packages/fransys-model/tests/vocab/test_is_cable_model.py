"""RW4 acceptance: `is_cable` reads exactly one fact, the part's `cable_product` facet (model-0108).

Two fixtures, side by side: a cable-product part with no `CableFacet` at all is a cable; an
item that carries a `CableFacet` but whose part has no `cable_product` facet is not. Neither
`category` nor the item's own `CableFacet` (installed length only, design/facets.md and
design/examples.md 11) is read.
"""

from decimal import Decimal

from plant import Plant

from fransys_model.kernel import Id, make_id
from fransys_model.vocab import cable_items, is_cable
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part


def _cable_part(plant: Plant, key: str = "cable_a") -> Id[Part]:
    """A `Part` with a `cable_product` facet and no other cable fact, the RW4-cable example."""
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"EXAMPLE-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=make_id(CableProductFacet, (key, "product")),
        key=(key, "product"),
        subject=part.id,
        core_colours=("BN", "BK"),
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    plant.add(part, product)
    return part.id


def test_a_cable_product_part_with_no_installed_length_facet_is_a_cable() -> None:
    """A part's `cable_product` facet alone is enough: no `CableFacet` is needed at all."""
    plant = Plant()
    cable = plant.item("w012", part=_cable_part(plant))
    model = plant.model()
    assert is_cable(model, cable) is True
    assert cable in cable_items(model)


def test_an_installed_length_facet_with_no_cable_product_part_is_not_a_cable() -> None:
    """A `CableFacet` (installed length) is not read: with no `cable_product` part, not a cable."""
    plant = Plant()
    item = plant.item("not_a_cable", part=None)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("not_a_cable", "length")),
            key=("not_a_cable", "length"),
            subject=item,
            length_mm=1500,
        )
    )
    model = plant.model()
    assert is_cable(model, item) is False
    assert item not in cable_items(model)
