"""Tests for `top_level_cables` (design/derive-queries-structure.md, units spec U3)."""

from decimal import Decimal
from typing import TYPE_CHECKING

from plant import Plant
from query_builders import make_core, make_pin

from fransys_model.derive import top_level_cables
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Item, Unit

# Baseline top-level cable count for the exclusion test, asserted before the unit-owned cable
# is added (a named constant, not a bare "at least" count).
BASELINE_CABLE_COUNT = 1


def _cable(
    plant: Plant,
    key: str,
    designation: str,
    *,
    parent: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
) -> Id[Item]:
    """A cable item: a cable `Part` (`is_cable`, decision model-0108) and a `cable` facet,
    `parent`/`unit` set or left `None`."""
    part = Part(
        id=make_id(Part, (key, "part")),
        key=(key, "part"),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=make_id(CableProductFacet, (key, "part", "product")),
        key=(key, "part", "product"),
        subject=part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    plant.add(part, product)
    item = plant.item(key, designation=designation, parent=parent, unit=unit, part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=None,
        )
    )
    return item


def test_a_standalone_top_level_cable_appears() -> None:
    """A loose cable with no harness and no unit is in `top_level_cables`."""
    plant = Plant()
    cable = _cable(plant, "w1", "W1")
    cables = top_level_cables(plant.model())
    assert len(cables) == BASELINE_CABLE_COUNT
    (row,) = cables
    assert (row.cable, row.designation) == (cable, "-W1")


def test_a_cable_inside_a_harness_with_no_unit_still_appears() -> None:
    """A cable child of a harness (itself `unit=None`) is included, same as a loose cable."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    cable = _cable(plant, "w1", "WH1-W1", parent=harness)
    (row,) = top_level_cables(plant.model())
    assert row.cable == cable


def test_a_top_level_cable_carries_its_cores_and_ends_like_harness_cables() -> None:
    """The result is a real `HarnessCable`: cores and ends, not a `CableListRow`."""
    plant = Plant()
    cable = _cable(plant, "w1", "W1")
    near = make_pin(plant, "near", "B1")
    far = make_pin(plant, "far", "B2")
    make_core(plant, "core-1", cable, (near, far), index=1)
    (row,) = top_level_cables(plant.model())
    assert len(row.cores) == 1
    assert {end.designation for end in row.ends} == {"-B1", "-B2"}


def test_a_cable_belonging_to_a_unit_is_excluded() -> None:
    """A unit-owned cable never shows up in `top_level_cables`; the loose count stays put."""
    plant = Plant()
    _cable(plant, "w1", "W1")
    baseline = top_level_cables(plant.model())
    assert len(baseline) == BASELINE_CABLE_COUNT
    unit = plant.unit("cab", name="pump-cabinet", revision=1)
    plant.revision(unit)
    _cable(plant, "w2", "W2", unit=unit)
    cables = top_level_cables(plant.model())
    assert len(cables) == BASELINE_CABLE_COUNT
    # examined: the unit-owned cable is really absent, not merely uncounted
    assert "-W2" not in {row.designation for row in cables}
