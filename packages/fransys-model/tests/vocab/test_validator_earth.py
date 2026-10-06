"""Decision model-0123: `GNYE_NOT_PE`, `PE_NOT_GNYE` and `PE_PORT_OFF_PE`."""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING

from plant import Plant

from fransys_model.kernel import Id, Model, Severity, make_id
from fransys_model.vocab import ALL_VALIDATORS
from fransys_model.vocab.connectivity import Net
from fransys_model.vocab.enums import NetClass, PortRole
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.facets.wire import WireFacet

if TYPE_CHECKING:
    from fransys_model.vocab.core import Port

from fransys_model.vocab.validators.earth import (
    GNYE_NOT_PE,
    PE_NOT_GNYE,
    PE_PORT_OFF_PE,
    check_earth,
)


def _wire(plant: Plant, name: str, colour: str, *, pe: bool, declared: bool = True) -> None:
    """A wire `name` between two pins, on a net of class PE or GENERIC, coloured `colour`."""
    a, b = plant.pin(name, "f", "a"), plant.pin(name, "f", "b")
    conductor = plant.wire(a, b, key=f"w-{name}")
    plant.add(
        WireFacet(
            id=make_id(WireFacet, (name,)),
            key=(name,),
            subject=conductor,
            colour=colour,
            gauge_mm2=Decimal("1.5"),
            length_mm=None,
            label=None,
        )
    )
    net = Net(
        id=make_id(Net, (f"n-{name}",)),
        key=(f"n-{name}",),
        name=None,
        net_class=NetClass.PE if pe else NetClass.GENERIC,
        ports=(a, b),
    )
    if declared:
        plant.add(net)


def _codes(model: Model) -> list[tuple[str, Severity]]:
    return [(f.code, f.severity) for f in check_earth(model)]


def test_gnye_on_a_non_pe_net_is_an_error() -> None:
    plant = Plant()
    _wire(plant, "x", "GNYE", pe=False)
    assert _codes(plant.model()) == [(GNYE_NOT_PE, Severity.ERROR)]


def test_gnye_on_a_net_declared_nowhere_is_silent() -> None:
    plant = Plant()
    _wire(plant, "x", "GNYE", pe=False, declared=False)
    assert _codes(plant.model()) == []


def test_gnye_on_a_pe_net_is_silent() -> None:
    plant = Plant()
    _wire(plant, "x", "GNYE", pe=True)
    assert _codes(plant.model()) == []


def test_a_pe_wire_of_another_colour_is_a_warning_and_an_empty_colour_is_not() -> None:
    plant = Plant()
    _wire(plant, "x", "BK", pe=True)
    _wire(plant, "y", "", pe=True)
    findings = check_earth(plant.model())
    assert [(f.code, f.severity) for f in findings] == [(PE_NOT_GNYE, Severity.WARNING)]
    assert make_id(WireFacet, ("x",)) in findings[0].subjects


def test_a_non_gnye_wire_on_a_non_pe_net_is_silent() -> None:
    plant = Plant()
    _wire(plant, "x", "BK", pe=False)
    assert _codes(plant.model()) == []


def _cable(plant: Plant, colours: tuple[str, ...], *, pe: bool) -> None:
    """A one-core cable whose core 1 sits on a PE or GENERIC net; the product holds `colours`."""
    part = plant.part("cable")
    plant.add(
        CableProductFacet(
            id=make_id(CableProductFacet, ("p",)),
            key=("p",),
            subject=part,
            core_colours=colours,
            gauge_mm2=Decimal("1.5"),
            shielded=False,
        )
    )
    cable = plant.item("cable", part=part)
    a, b = plant.pin("ca", "f", "a"), plant.pin("cb", "f", "b")
    core = plant.core(a, b, key="core", carrier=cable)
    plant.add(CoreFacet(id=make_id(CoreFacet, ("c",)), key=("c",), subject=core, index=1))
    net = Net(
        id=make_id(Net, ("n",)),
        key=("n",),
        name=None,
        net_class=NetClass.PE if pe else NetClass.GENERIC,
        ports=(a, b),
    )
    plant.add(net)


def test_a_gnye_cable_core_on_a_non_pe_net_is_an_error() -> None:
    plant = Plant()
    _cable(plant, ("GNYE",), pe=False)
    assert _codes(plant.model()) == [(GNYE_NOT_PE, Severity.ERROR)]


def test_a_cable_core_on_a_pe_net_is_not_a_single_wire() -> None:
    plant = Plant()
    _cable(plant, ("BK",), pe=True)
    assert _codes(plant.model()) == []


def _pe_port(plant: Plant, *, pe: bool) -> Id[Port]:
    a, b = plant.pin("t", "f", "a"), plant.pin("t", "f", "b")
    plant.wire(a, b, key="w")
    plant.add(
        Net(
            id=make_id(Net, ("n",)),
            key=("n",),
            name=None,
            net_class=NetClass.PE if pe else NetClass.GENERIC,
            ports=(a, b),
        )
    )
    return a


def _with_role(plant: Plant, port: Id[Port]) -> Model:
    plant.records = [replace(r, role=PortRole.PE) if r.id == port else r for r in plant.records]
    return plant.model()


def test_a_pe_port_off_a_pe_net_is_a_warning() -> None:
    plant = Plant()
    model = _with_role(plant, _pe_port(plant, pe=False))
    assert _codes(model) == [(PE_PORT_OFF_PE, Severity.WARNING)]


def test_a_pe_port_on_a_pe_net_is_silent() -> None:
    plant = Plant()
    model = _with_role(plant, _pe_port(plant, pe=True))
    assert _codes(model) == []


def test_a_pe_port_on_a_net_declared_nowhere_is_silent() -> None:
    plant = Plant()
    a = plant.pin("t", "f", "a")
    assert _codes(_with_role(plant, a)) == []


def test_the_earth_validator_is_registered() -> None:
    assert check_earth in ALL_VALIDATORS
