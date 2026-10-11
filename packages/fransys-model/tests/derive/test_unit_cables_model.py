"""Tests for `unit_cables` (decision pdf-0015).

See design/derive-queries-structure.md.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.derive import reading_cables, top_level_cables, unit_cables
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part
lazy from fransys_model.vocab.core import Unit

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


def test_reading_cables_none_is_the_top_level_cables() -> None:
    """`reading_cables(model, None)` is `top_level_cables`: the system's own cables only."""
    plant = Plant()
    unit = _unit(plant, "harness-unit")
    _cable(plant, "w1", "W1", unit=unit)
    top = _cable(plant, "t1", "T1")
    model = plant.model()
    assert reading_cables(model, None) == top_level_cables(model)
    assert tuple(row.cable for row in reading_cables(model, None)) == (top,)


def test_reading_cables_unit_is_the_unit_cables() -> None:
    """`reading_cables(model, unit)` is `unit_cables`: the unit's own cables only."""
    plant = Plant()
    unit = _unit(plant, "harness-unit")
    own = _cable(plant, "w1", "W1", unit=unit)
    _cable(plant, "t1", "T1")
    model = plant.model()
    assert reading_cables(model, unit) == unit_cables(model, unit)
    assert tuple(row.cable for row in reading_cables(model, unit)) == (own,)
