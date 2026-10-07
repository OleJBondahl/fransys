"""Invented plants for the cable drawing's derive tests: devices, cables, one edit helper."""

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fransys_model.kernel import Id, make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.templates import Part

if TYPE_CHECKING:
    from plant import Plant

    from fransys_model.vocab.core import Item, Port, Unit


def edit(plant: Plant, record_id: Id[Any], **changes: Any) -> None:
    """Replace the plant's record `record_id` by a copy with `changes` (records are frozen)."""
    (at,) = [n for n, record in enumerate(plant.records) if record.id == record_id]
    plant.records[at] = dataclasses.replace(plant.records[at], **changes)


def device(  # noqa: PLR0913 -- one keyword per Item field the tests vary
    plant: Plant,
    key: str,
    tag: str,
    *names: str,
    unit: Id[Unit] | None = None,
    external: bool = False,
    parent: Id[Item] | None = None,
) -> tuple[Id[Item], dict[str, Id[Port]]]:
    """An item `tag` with one function and a port per name, by name."""
    item = plant.item(key, designation=tag, unit=unit, parent=parent)
    if external:
        edit(plant, item, external=True)
    function = plant.function(item, "f")
    return item, {name: plant.port(function, name) for name in names}


def cable(  # noqa: PLR0913 -- one keyword per cable fact the tests vary
    plant: Plant,
    key: str,
    tag: str | None,
    *,
    parent: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
    shielded: bool = False,
    length: int | None = None,
) -> Id[Item]:
    """A cable item `tag` with a cable part (`is_cable`) and a `cable` facet."""
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
        shielded=shielded,
    )
    plant.add(part, product)
    item = plant.item(key, designation=tag, parent=parent, unit=unit, part=part.id)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=length,
        )
    )
    return item
