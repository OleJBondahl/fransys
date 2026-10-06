"""Tests for `unit_cables` (units spec U3, decision pdf-0015).

See design/derive-queries-structure.md.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from plant import Plant
from query_builders import make_core, make_pin

from fransys_model.derive import top_level_cables, unit_cables
from fransys_model.kernel import SchemaError, make_id
from fransys_model.vocab.core import Unit
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Item


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


def _unit(plant: Plant, key: str, *, parent: Id[Unit] | None = None) -> Id[Unit]:
    """A unit with its history entry, optionally nested in `parent`."""
    unit = plant.unit(key, name=key, revision=1, parent=parent)
    plant.revision(unit)
    return unit


def test_a_harness_unit_gives_its_own_harness_cable() -> None:
    """A harness that is a unit: its cable child (`unit=U`) is the unit's cable.

    Built without `_cable()` (decision model-0108): `harness` must stay classified
    `is_harness`, which now needs its cable child to carry a cable part, not just a bare
    `CableFacet`.
    """
    plant = Plant()
    unit = _unit(plant, "harness-unit")
    harness = plant.item("wh1", designation="WH1", unit=unit)
    part = Part(
        id=make_id(Part, ("w1", "part")),
        key=("w1", "part"),
        mpn="MPN-w1",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    product = CableProductFacet(
        id=make_id(CableProductFacet, ("w1", "part", "product")),
        key=("w1", "part", "product"),
        subject=part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    plant.add(part, product)
    cable = plant.item("w1", designation="W1", parent=harness, unit=unit, part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    (row,) = unit_cables(plant.model(), unit)
    assert (row.cable, row.designation) == (cable, "-WH1-W1")


def test_a_unit_cable_is_a_real_harness_cable_with_cores_and_ends() -> None:
    """The result carries the cable's cores and ends, built like `top_level_cables`' rows."""
    plant = Plant()
    unit = _unit(plant, "harness-unit")
    cable = _cable(plant, "w1", "W1", unit=unit)
    near = make_pin(plant, "near", "B1")
    far = make_pin(plant, "far", "B2")
    make_core(plant, "core-1", cable, (near, far), index=1)
    (row,) = unit_cables(plant.model(), unit)
    assert len(row.cores) == 1
    assert {end.designation for end in row.ends} == {"-B1", "-B2"}


def test_a_container_unit_gives_its_loose_cable_and_not_a_nested_units_or_a_top_level_one() -> None:
    """A container unit's own loose cable (no harness parent) is drawn; a cable of a unit nested
    in it, and a top-level cable, are not."""
    plant = Plant()
    container = _unit(plant, "cabinet")
    nested = _unit(plant, "board", parent=container)
    own = _cable(plant, "w1", "W1", unit=container)
    nested_cable = _cable(plant, "w2", "W2", unit=nested)
    top_level = _cable(plant, "w3", "W3")
    model = plant.model()

    assert [row.cable for row in unit_cables(model, container)] == [own]
    assert [row.cable for row in unit_cables(model, nested)] == [nested_cable]
    assert [row.cable for row in top_level_cables(model)] == [top_level]


def test_unit_cables_are_sorted_by_designation() -> None:
    """Sorted by `(designation, id)`, `harness_cables`' order, whatever the insertion order."""
    plant = Plant()
    unit = _unit(plant, "cabinet")
    inserted = [_cable(plant, f"k{n}", f"W{n}", unit=unit) for n in (5, 3, 1, 4, 2)]
    expected = [inserted[2], inserted[4], inserted[1], inserted[3], inserted[0]]
    assert [row.cable for row in unit_cables(plant.model(), unit)] == expected


def test_a_unit_with_no_cable_gives_nothing() -> None:
    """A unit none of whose items is a cable gives `()`, not an error."""
    plant = Plant()
    unit = _unit(plant, "cabinet")
    plant.item("d1", designation="D1", unit=unit)
    assert unit_cables(plant.model(), unit) == ()


def test_an_unknown_unit_is_refused() -> None:
    """A unit id that names no `Unit` of the model is a `SchemaError`, like a missing item."""
    plant = Plant()
    _cable(plant, "w1", "W1")
    with pytest.raises(SchemaError):
        unit_cables(plant.model(), make_id(Unit, ("nowhere",)))
