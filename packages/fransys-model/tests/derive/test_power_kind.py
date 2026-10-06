"""`derive.power_kind` and `supply_of_potential`: what a net is on the drawing (model-0117)."""

from typing import TYPE_CHECKING

from plant import Plant
from rating_plant import rail, supply

from fransys_model.derive import (
    PowerKind,
    port_power_kind,
    port_power_text,
    power_kind,
    power_text,
)
from fransys_model.kernel import Id, make_id
from fransys_model.vocab import ConductorKind, Net, NetClass, Rail
from fransys_model.vocab.enums import Current
from fransys_model.vocab.tables import nets, supply_of_potential

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_DC24 = {"24V": rail("24"), "0V": rail("0")}


def _plant(rails: dict[str, Rail] | None = None, current: Current = Current.DC) -> Plant:
    plant = Plant()
    if rails is not None:
        supply(plant, "main", rails, current=current)
    return plant


def _declare(plant: Plant, key: str, potential: str | None) -> Id[Net]:
    return plant.net(key, (plant.pin(key, "f", "1"),), potential=potential)


def _pe(plant: Plant, key: str = "pe") -> Id[Net]:
    """A declared net of class `PE`, with no potential."""
    net = Net(
        id=make_id(Net, (key,)),
        key=(key,),
        name=None,
        net_class=NetClass.PE,
        ports=(plant.pin(key, "f", "1"),),
    )
    plant.add(net)
    return net.id


def _kind(plant: Plant, net: Id[Net]) -> PowerKind:
    model: Model = plant.model()
    return power_kind(model, net)


def test_a_dc_rail_above_zero_is_a_supply() -> None:
    plant = _plant(_DC24)
    assert _kind(plant, _declare(plant, "a", "24V")) is PowerKind.SUPPLY


def test_a_dc_rail_at_zero_is_ground() -> None:
    plant = _plant(_DC24)
    assert _kind(plant, _declare(plant, "a", "0V")) is PowerKind.GROUND


def test_a_net_of_class_pe_is_pe_with_no_supply_at_all() -> None:
    plant = _plant()
    assert _kind(plant, _pe(plant)) is PowerKind.PE


def test_a_net_of_class_pe_is_pe_beside_a_supply_that_does_not_name_it() -> None:
    plant = _plant(_DC24)
    assert _kind(plant, _pe(plant)) is PowerKind.PE


def test_an_ac_rail_is_none() -> None:
    plant = _plant({"L1": rail("230", 0), "N": rail("0")}, Current.AC)
    assert _kind(plant, _declare(plant, "a", "L1")) is PowerKind.NONE
    assert _kind(plant, _declare(plant, "b", "N")) is PowerKind.NONE


def test_a_potential_in_no_supply_is_none() -> None:
    plant = _plant(_DC24)
    assert _kind(plant, _declare(plant, "a", "12V")) is PowerKind.NONE


def test_a_net_with_no_potential_is_none() -> None:
    plant = _plant(_DC24)
    assert _kind(plant, _declare(plant, "a", None)) is PowerKind.NONE


def test_a_dc_supply_that_declares_no_zero_volt_rail_leaves_its_zero_volt_net_none() -> None:
    plant = _plant({"24V": rail("24")})
    assert _kind(plant, _declare(plant, "a", "24V")) is PowerKind.SUPPLY
    assert _kind(plant, _declare(plant, "b", "0V")) is PowerKind.NONE


def test_a_negative_dc_rail_is_a_supply() -> None:
    """Owner's A6, confirmed 2026-10-02 (model-0117): the sign of `max_v` does not make ground."""
    plant = _plant({"-24V": rail("-24"), "0V": rail("0")})
    assert _kind(plant, _declare(plant, "a", "-24V")) is PowerKind.SUPPLY


def test_two_potentials_on_one_physical_net_give_none() -> None:
    plant = _plant(_DC24)
    high = _declare(plant, "a", "24V")
    low = _declare(plant, "b", "0V")
    first, second = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    plant.wire(first, second, key="short")
    assert _kind(plant, high) is PowerKind.NONE
    assert _kind(plant, low) is PowerKind.NONE


def test_a_port_on_a_supply_net_by_wire_only_has_the_supply_kind() -> None:
    """A load pin wired to the 24 V terminal is on that physical net though no `Net` lists it."""
    plant = _plant(_DC24)
    declared = _declare(plant, "a", "24V")
    load = plant.pin("load", "f", "1")
    plant.wire(plant.pin("a", "f", "1"), load, key="w")
    plant.wire(load, plant.pin("load2", "f", "1"), key="w2")  # a third port: a rail, not a wire
    model = plant.model()
    assert port_power_kind(model, load) is PowerKind.SUPPLY
    assert power_kind(model, declared) is PowerKind.SUPPLY
    assert port_power_kind(model, Id(kind="port", value="0" * 32)) is PowerKind.NONE


def _named(plant: Plant, key: str, potential: str, name: str | None) -> Id[Net]:
    return plant.net(key, (plant.pin(key, "f", "1"),), potential=potential, name=name)


def test_power_text_of_a_supply_is_its_name_and_ground_prints_none() -> None:
    """Owner's A4, 2026-10-02 (model-0117): only the supply prints; a named ground prints none."""
    plant = _plant(_DC24)
    high, low = _named(plant, "a", "24V", "+24 V"), _named(plant, "b", "0V", "GND")
    model = plant.model()
    assert power_text(model, high) == "+24 V"
    assert power_text(model, low) is None


def test_power_text_falls_back_to_the_potential_and_a_negative_one_keeps_its_sign() -> None:
    plant = _plant({"-15V": rail("-15"), **_DC24})
    first, second = _named(plant, "a", "24V", None), _named(plant, "b", "-15V", None)
    model = plant.model()
    assert power_text(model, first) == "24V"
    assert power_text(model, second) == "-15V"


def test_power_text_is_none_for_pe_and_for_none() -> None:
    plant = _plant(_DC24)
    pe, other = _pe(plant), _named(plant, "a", "12V", "X")
    model = plant.model()
    assert power_text(model, pe) is None
    assert power_text(model, other) is None


def test_a_load_pin_wired_to_a_named_supply_net_prints_that_nets_text() -> None:
    plant = _plant(_DC24)
    _named(plant, "a", "24V", "+24 V")
    load = plant.pin("load", "f", "1")
    plant.wire(plant.pin("a", "f", "1"), load, key="w")
    plant.wire(load, plant.pin("load2", "f", "1"), key="w2")  # a third port: a rail, not a wire
    other = plant.pin("lone", "f", "1")
    model = plant.model()
    assert port_power_text(model, load) == "+24 V"
    assert port_power_text(model, other) is None


def test_supply_of_potential_is_the_one_lookup() -> None:
    plant = _plant(_DC24)
    model = plant.model()
    found = supply_of_potential(model, "24V")
    assert found is not None
    assert found.name == "main"
    assert supply_of_potential(model, "12V") is None


def test_a_two_port_net_is_none_whatever_its_potential_and_keeps_the_potential() -> None:
    """V3: a point-to-point net is a wire. The three-port net beside it is a rail."""
    plant = _plant(_DC24)
    wire = _declare(plant, "a", "24V")
    plant.wire(plant.pin("a", "f", "1"), plant.pin("b", "f", "1"), key="w")
    rail_net = _declare(plant, "c", "24V")
    plant.wire(plant.pin("c", "f", "1"), plant.pin("d", "f", "1"), key="w1")
    plant.wire(plant.pin("c", "f", "1"), plant.pin("e", "f", "1"), key="w2")
    model = plant.model()
    assert power_kind(model, wire) is PowerKind.NONE
    assert power_kind(model, rail_net) is PowerKind.SUPPLY
    assert port_power_kind(model, plant.pin("b", "f", "1")) is PowerKind.NONE
    assert nets(model)[wire].potential == "24V"


def test_a_two_port_pe_net_stays_pe() -> None:
    plant = _plant(_DC24)
    pe = _pe(plant)
    other = plant.pin("x", "f", "1")
    plant.wire(plant.pin("pe", "f", "1"), other, key="w")
    assert _kind(plant, pe) is PowerKind.PE
    assert port_power_kind(plant.model(), other) is PowerKind.PE  # the port, read by its net


def test_a_third_port_that_arrives_over_a_bridge_makes_the_net_a_rail() -> None:
    plant = _plant(_DC24)
    net = _declare(plant, "a", "24V")
    plant.wire(plant.pin("a", "f", "1"), plant.pin("b", "f", "1"), key="w")
    assert _kind(plant, net) is PowerKind.NONE
    plant.wire(
        plant.pin("b", "f", "1"),
        plant.pin("c", "f", "1"),
        key="bridge",
        kind=ConductorKind.JUMPER,
    )
    assert _kind(plant, net) is PowerKind.SUPPLY
