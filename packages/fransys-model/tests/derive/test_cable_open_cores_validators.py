"""`CABLE_CORE_COUNT` counts open cores; `PORT_UNCONNECTED` treats a parked spare's pin as wired."""

from decimal import Decimal

from plant import Plant
from query_builders import make_part, make_pin

from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import (
    CableFacet,
    CableProductFacet,
    CoreFacet,
    CorePair,
    OpenCoreFacet,
)
from fransys_model.vocab.validators.cables import CABLE_CORE_COUNT, check_cables
from fransys_model.vocab.validators.connectivity import PORT_UNCONNECTED, check_connectivity


def _plant(pairs: tuple[CorePair, ...] = ()) -> tuple[Plant, Id[Port]]:
    """A cable of three cores; core 1 is wired, so two are left. Also a pin for a parked spare."""
    plant = Plant()
    part = make_part(plant, "cab", "MPN-cab", category=PartCategory.CABLE)
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, ("cab", "product")),
            key=("cab", "product"),
            subject=part,
            core_colours=("BN", "BU", "GN"),
            gauge_mm2=Decimal("0.5"),
            shielded=False,
            pairs=pairs,
        )
    )
    cable = plant.item("w1", designation="W1", part=part)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "c")), key=("w1", "c"), subject=cable, length_mm=None
        )
    )
    core = plant.core(make_pin(plant, "a", "A"), make_pin(plant, "b", "B"), key="c1", carrier=cable)
    plant.add(CoreFacet(id=make_id(CoreFacet, ("c1", "f")), key=("c1", "f"), subject=core, index=1))
    return plant, make_pin(plant, "park", "P")


def _open(plant: Plant, index: int, at: Id[Port] | None) -> None:
    cable = make_id(Item, ("w1",))
    key = ("w1", "open", str(index))
    plant.add(
        OpenCoreFacet(id=make_id(OpenCoreFacet, key), key=key, subject=cable, index=index, at=at)
    )


def test_two_unwired_cores_warn_with_the_remedy() -> None:
    # MUTATION: the count ignores `OpenCoreFacet`
    plant, _ = _plant()
    (finding,) = check_cables(plant.model())
    assert finding.code == CABLE_CORE_COUNT
    assert "wire it, or mark it with W1.spare(...)" in finding.message


def test_open_cores_count_with_the_wired_ones() -> None:
    plant, park = _plant()
    _open(plant, 2, park)
    _open(plant, 3, None)
    assert check_cables(plant.model()) == ()


def test_one_core_too_many_stays_an_error() -> None:
    plant, _ = _plant()
    for index in (2, 3, 4):
        _open(plant, index, None)
    (finding,) = check_cables(plant.model())
    assert finding.severity.name == "ERROR"


def test_a_pin_a_spare_lands_on_is_connected() -> None:
    # MUTATION: `_unconnected` leaves `OpenCoreFacet.at` out of the wired set
    plant, park = _plant()
    before = {f.subjects for f in check_connectivity(plant.model()) if f.code == PORT_UNCONNECTED}
    assert (park,) in before
    _open(plant, 2, park)
    after = {f.subjects for f in check_connectivity(plant.model()) if f.code == PORT_UNCONNECTED}
    assert (park,) not in after
