"""Tests for `cable_list_rows`."""

from decimal import Decimal
from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.derive import cable_list_rows
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item, Unit

# Baseline top-level cable count for the exclusion test, asserted before the unit-owned cable
# is added (a named constant, not a bare "at least" count).


def _cable(plant: Plant, key: str, designation: str, *, unit: Id[Unit] | None = None) -> Id[Item]:
    """A cable item with a `cable` facet and a cable part (RW4b: `is_cable` needs a
    `CableProductFacet`, not just a `cable` facet), `unit` set or left `None`.

    `core_colours` starts empty; `query_builders.make_core`'s `_colour_core` grows it to match
    whatever cores the caller adds afterwards, so it always matches the modelled cores exactly.
    """
    part = Part(
        id=make_id(Part, (key, "cable-part")),
        key=(key, "cable-part"),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description=f"Invented {key}",
        category=PartCategory.CABLE,
        class_code="",
    )
    plant.add(
        part,
        CableProductFacet(
            id=make_id(CableProductFacet, (key, "product")),
            key=(key, "product"),
            subject=part.id,
            core_colours=(),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
        ),
    )
    item = plant.item(key, designation=designation, unit=unit, part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=None,
        )
    )
    return item


def test_a_cable_belonging_to_a_unit_is_listed_under_its_unit() -> None:
    """`cable_list_rows(unit=...)` lists the unit's own cable and not a loose one."""
    plant = Plant()
    _cable(plant, "w1", "W1")
    unit = plant.unit("cab", name="pump-cabinet", revision=1)
    plant.revision(unit)
    _cable(plant, "w3", "W3", unit=unit)
    rows = cable_list_rows(plant.model(), unit=unit)
    assert [row.designation for row in rows] == ["-W3"]
