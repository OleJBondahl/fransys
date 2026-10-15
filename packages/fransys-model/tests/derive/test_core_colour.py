"""`derive.core_colour`: a core's colour is its carrier's product's `core_colours[index - 1]`."""

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from plant import Plant
from query_builders import make_part, make_pin

from fransys_model.derive import core_colour
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet, CoreFacet
lazy from fransys_model.vocab.connectivity import Conductor

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item

_COLOURS = ("BN", "BU", "GN")


def _plant(colours: tuple[str, ...] | None = _COLOURS) -> tuple[Plant, Id[Item], Id[Item]]:
    """A harness `WH1` and its cable `W1` with a `cable` facet, whose part has `colours` as
    `core_colours`; `None` gives a cable with no part."""
    plant = Plant()
    harness = plant.item("wh1", designation="WH1")
    part = None
    if colours is not None:
        part = make_part(plant, "cab", "MPN-cab", category=PartCategory.CABLE)
        plant.add(
            CableProductFacet(
                id=make_id(CableProductFacet, ("cab", "product")),
                key=("cab", "product"),
                subject=part,
                core_colours=colours,
                gauge_mm2=Decimal("0.5"),
                shielded=False,
            )
        )
    cable = plant.item("w1", designation="W1", parent=harness, part=part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=cable,
            length_mm=None,
        )
    )
    return plant, harness, cable


def _core(plant: Plant, cable: Id[Item], index: int | None) -> Id[Conductor]:
    """A core of `cable` with a `core` facet at `index`, or none when `index` is `None`."""
    key = f"core-{index}"
    conductor = plant.core(
        make_pin(plant, f"a-{key}", f"A{index}"),
        make_pin(plant, f"b-{key}", f"B{index}"),
        key=key,
        carrier=cable,
    )
    if index is not None:
        plant.add(
            CoreFacet(
                id=make_id(CoreFacet, (key, "facet")),
                key=(key, "facet"),
                subject=conductor,
                index=index,
            )
        )
    return conductor


def test_a_core_of_a_cable_with_no_product_has_no_colour() -> None:
    # MUTATION: `_product_colours` returns `("",)` instead of `()` for a cable with no part
    plant, _, cable = _plant(None)
    core = _core(plant, cable, 1)
    assert core_colour(plant.model(), core) == ""


def test_a_core_with_no_core_facet_raises() -> None:
    # MUTATION: `core_colour` falls back to `colours[0]` when it finds no `core` facet
    plant, _, cable = _plant()
    core = _core(plant, cable, None)
    with pytest.raises(SchemaError, match="no `core` facet"):
        core_colour(plant.model(), core)


def test_a_core_past_its_product_has_no_colour() -> None:
    # MUTATION: `_colour_at` wraps the index (`colours[index % len(colours) - 1]`) or raises
    plant, _, cable = _plant()
    core = _core(plant, cable, 4)
    assert core_colour(plant.model(), core) == ""
