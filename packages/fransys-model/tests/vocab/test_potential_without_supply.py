"""`POTENTIAL_WITHOUT_SUPPLY` (conventions V11): a potential no supply declares is reported."""

from decimal import Decimal

from plant import Plant

from fransys_model.kernel import Severity, make_id
from fransys_model.vocab import ALL_VALIDATORS
from fransys_model.vocab.connectivity import Net
from fransys_model.vocab.enums import Current, Earthing, NetClass
from fransys_model.vocab.supply_system import Rail, SupplySystem
from fransys_model.vocab.validators.potential_without_supply import (
    POTENTIAL_WITHOUT_SUPPLY,
    check_potential_without_supply,
)


def _plant(*, potential: str | None, declare: bool) -> Plant:
    plant = Plant()
    plant.net("n1", (plant.pin("X1", "f", "1"), plant.pin("X2", "f", "1")), potential=potential)
    if declare:
        plant.add(
            SupplySystem(
                id=make_id(SupplySystem, ("s1",)),
                key=("s1",),
                name="24V",
                current=Current.DC,
                earthing=Earthing.EARTHED,
                rails=frozendict({"+24V": Rail(max_v=Decimal(24), phase=None)}),
            )
        )
    return plant


def test_a_potential_no_supply_declares_gives_one_warning_naming_net_origin_and_potential() -> None:
    model = _plant(potential="+24V", declare=False).model()
    (finding,) = check_potential_without_supply(model)
    assert finding.code == POTENTIAL_WITHOUT_SUPPLY
    assert finding.severity == Severity.WARNING
    assert finding.subjects == (make_id(Net, ("n1",)),)
    assert finding.message == (
        "net n1 (plant.py:1) carries potential '+24V', which no supply declares "
        "(declared: none): it gets no rank and no power symbol"
    )
    assert finding in [f for check in ALL_VALIDATORS for f in check(model)]


def test_a_supply_declaring_the_potential_gives_none() -> None:
    assert check_potential_without_supply(_plant(potential="+24V", declare=True).model()) == ()


def test_a_net_with_no_potential_gives_none() -> None:
    assert check_potential_without_supply(_plant(potential=None, declare=False).model()) == ()


def test_a_potential_a_pe_net_carries_is_earth_and_gives_none() -> None:
    plant = _plant(potential=None, declare=False)
    ports = (plant.pin("X3", "f", "1"), plant.pin("X4", "f", "1"))
    plant.add(
        Net(
            id=make_id(Net, ("pe",)),
            key=("pe",),
            name=None,
            net_class=NetClass.PE,
            ports=ports,
            potential="PE",
        )
    )
    assert check_potential_without_supply(plant.model()) == ()


def test_the_message_names_the_declared_potentials_so_a_misspelt_name_shows_its_fix() -> None:
    plant = _plant(potential="42V", declare=False)
    for key, volts in ((("s24",), 24), (("s0",), 0)):
        plant.add(
            SupplySystem(
                id=make_id(SupplySystem, key),
                key=key,
                name=key[0],
                current=Current.DC,
                earthing=Earthing.EARTHED,
                rails=frozendict({f"{volts}V": Rail(max_v=Decimal(volts), phase=None)}),
            )
        )
    (finding,) = check_potential_without_supply(plant.model())
    assert "'42V'" in finding.message
    assert "(declared: 0V, 24V)" in finding.message
