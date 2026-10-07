"""Tests for `supply_share`: the share of an interface's connected pins on a supply (model-0176).

The worked example's interfaces (harness-assemblies spec, HL13): `-U1-J1` 4/8, `-U1-J5` 2/4,
`-U1-J7` 4/12, `-U1-J2` and `-U1-J3` 0. A rank counts whatever it is: 24 V and GND alike.
"""

from decimal import Decimal
from fractions import Fraction

from plant import Plant

from fransys_model.derive import supply_share
from fransys_model.kernel import Id, Model, make_id
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import Current
from fransys_model.vocab.supply_system import Rail, SupplySystem

_RAILS = {"24V": Rail(max_v=Decimal(24), phase=None), "GND": Rail(max_v=Decimal(0), phase=None)}


def _plant() -> Plant:
    plant = Plant()
    plant.add(
        SupplySystem(
            id=make_id(SupplySystem, ("control",)),
            key=("control",),
            name="control",
            current=Current.DC,
            rails=frozendict(_RAILS),
        )
    )
    return plant


def _interface(plant: Plant, name: str, *, supply: tuple[str, ...], signals: int) -> Id[Function]:
    """An interface `name` with one connected pin per `supply` potential and per signal.

    A supply pin stands on a net with that potential; a signal pin is wired to a pin of a peer
    that is on no net.
    """
    for index, potential in enumerate(supply):
        pin = plant.pin(name, "f", f"s{index}")
        plant.net(f"{name}-{index}", (pin,), potential=potential)
    for index in range(signals):
        pin = plant.pin(name, "f", f"d{index}")
        peer = plant.pin(f"{name}-peer", "f", f"d{index}")
        plant.wire(pin, peer, key=f"{name}-w{index}")
    return plant.function_id(name, "f")


def test_the_worked_examples_interfaces() -> None:
    plant = _plant()
    j1 = _interface(plant, "j1", supply=("24V", "24V", "GND", "GND"), signals=4)
    j5 = _interface(plant, "j5", supply=("24V", "GND"), signals=2)
    j7 = _interface(plant, "j7", supply=("24V", "24V", "GND", "GND"), signals=8)
    j2 = _interface(plant, "j2", supply=(), signals=2)
    j3 = _interface(plant, "j3", supply=(), signals=4)
    model = plant.model()
    got = [supply_share(model, f) for f in (j1, j5, j7, j2, j3)]
    assert got == [Fraction(4, 8), Fraction(2, 4), Fraction(4, 12), Fraction(0), Fraction(0)]


def test_ground_counts_as_a_supply() -> None:
    plant = _plant()
    only_gnd = _interface(plant, "j1", supply=("GND",), signals=1)
    assert supply_share(plant.model(), only_gnd) == Fraction(1, 2)


def test_a_pin_on_no_conductor_and_no_net_is_not_counted() -> None:
    plant = _plant()
    function = _interface(plant, "j1", supply=("24V",), signals=1)
    plant.pin("j1", "f", "spare")
    assert supply_share(plant.model(), function) == Fraction(1, 2)


def test_an_interface_with_no_connected_pin_has_share_zero() -> None:
    plant = _plant()
    plant.pin("j1", "f", "spare")
    assert supply_share(plant.model(), plant.function_id("j1", "f")) == Fraction(0)


def test_a_potential_no_supply_declares_is_no_supply() -> None:
    plant = _plant()
    function = _interface(plant, "j1", supply=("ZZ", "24V"), signals=0)
    assert supply_share(plant.model(), function) == Fraction(1, 2)


def test_a_function_not_in_the_model_has_share_zero() -> None:
    model: Model = _plant().model()
    assert supply_share(model, make_id(Function, ("nope", "f"))) == Fraction(0)
