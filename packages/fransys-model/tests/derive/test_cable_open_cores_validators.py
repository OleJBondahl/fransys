"""`CABLE_CORE_COUNT` counts open cores; `FUNCTION_HALF_CONNECTED` treats a spare's pin as wired."""

from decimal import Decimal
from typing import Any

from plant import Plant
from query_builders import make_part, make_pin

from fransys_model.derive.core_pairs import open_core_is_spare
from fransys_model.kernel import Id, Severity, make_id
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import FunctionKind, PartCategory, PortRole
from fransys_model.vocab.facets.cable import (
    CableFacet,
    CableProductFacet,
    CoreFacet,
    CorePair,
    OpenCoreFacet,
)
from fransys_model.vocab.validators.cables import (
    CABLE_CORE_COUNT,
    CORE_INDEX_PAST_PRODUCT,
    check_cables,
)
from fransys_model.vocab.validators.connectivity import FUNCTION_HALF_CONNECTED, check_connectivity
from fransys_model.vocab.validators.earth import PE_PORT_OFF_PE, check_earth


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
    # MUTATION: `_half_connected` leaves `OpenCoreFacet.at` out of the wired set
    plant, _ = _plant()
    coil = plant.function(plant.item("k1"), "coil", kind=FunctionKind.COIL)
    a1, a2 = plant.port(coil, "A1"), plant.port(coil, "A2")
    plant.wire(a1, make_pin(plant, "peer", "P"), key="w")

    def open_ports() -> set[tuple[Id[Any], ...]]:
        found = check_connectivity(plant.model())
        return {f.subjects for f in found if f.code == FUNCTION_HALF_CONNECTED}

    assert open_ports() == {(a2,)}
    _open(plant, 2, a2)
    assert open_ports() == set()


def test_a_core_past_its_product_is_an_error_naming_the_remedy() -> None:
    # MUTATION: `_past_product` tests `index > len` with `>=`, or is not called by `check_cables`
    plant, _ = _plant()
    core = plant.core(
        make_pin(plant, "c", "C"),
        make_pin(plant, "d", "D"),
        key="c5",
        carrier=make_id(Item, ("w1",)),
    )
    plant.add(CoreFacet(id=make_id(CoreFacet, ("c5", "f")), key=("c5", "f"), subject=core, index=5))
    (finding,) = [f for f in check_cables(plant.model()) if f.code == CORE_INDEX_PAST_PRODUCT]
    assert finding.severity is Severity.ERROR
    assert "core 5, its product has 3 cores" in finding.message
    assert "use a core from 1 to 3 or a part with more cores" in finding.message


def test_a_core_inside_its_product_gives_no_index_finding() -> None:
    plant, _ = _plant()
    assert [f for f in check_cables(plant.model()) if f.code == CORE_INDEX_PAST_PRODUCT] == []


def _pe_port_plant(*, wired: bool) -> tuple[Plant, Id[Port]]:
    """A PE-role port; wired to a loose pin when asked, and no declared net lists either."""
    plant, _ = _plant()
    function = plant.function(plant.item("m1"), "motor")
    key = ("m1", "motor", "PE")
    port = Port(
        id=make_id(Port, key),
        key=key,
        function=function,
        template=None,
        name="PE",
        role=PortRole.PE,
    )
    plant.add(port)
    port = port.id
    if wired:
        plant.wire(port, make_pin(plant, "loose", "L"), key="loose")
    return plant, port


def test_a_pe_port_on_a_loose_wire_warns_and_a_core_there_is_a_spare() -> None:
    # MUTATION: `_port_findings` needs a declared net again / `_is_pe` counts the PE role
    plant, port = _pe_port_plant(wired=True)
    model = plant.model()
    (finding,) = check_earth(model)
    assert (finding.code, finding.subjects) == (PE_PORT_OFF_PE, (port,))
    assert open_core_is_spare(model, "GNYE", port)


def test_a_lone_pe_port_with_no_wire_stays_silent() -> None:
    plant, port = _pe_port_plant(wired=False)
    assert check_earth(plant.model()) == ()
    assert open_core_is_spare(plant.model(), "GNYE", port)
