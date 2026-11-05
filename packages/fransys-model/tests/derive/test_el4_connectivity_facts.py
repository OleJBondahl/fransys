"""The facts behind the connectivity and supply checks (EL-4)."""

from decimal import Decimal

from plant import Plant

from fransys_model.derive.facts.closure import net_on_one_board, port_item
from fransys_model.derive.facts.net_facts import declared_nets_of
from fransys_model.derive.facts.potential_without_supply import (
    declared_rails,
    potentials_without_supply,
)
from fransys_model.derive.facts.supply_sources import (
    declarations_by_name,
    supplies_by_potential,
    supply_differences,
)
from fransys_model.derive.facts.wired_ports import half_connected, mated_ports, wired_ports
from fransys_model.elecdef import Current
from fransys_model.kernel import make_id
from fransys_model.vocab import Rail, SupplySystem
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind


def _supply(key: str, name: str, *potentials: str) -> SupplySystem:
    rails = frozendict({p: Rail(max_v=Decimal(24), phase=None) for p in potentials})
    return SupplySystem(
        id=make_id(SupplySystem, (key,)),
        key=(key,),
        name=name,
        current=Current.DC,
        rails=rails,
    )


def test_declared_nets_of_lists_the_nets_that_hold_a_port() -> None:
    plant = Plant()
    a, b, c = (plant.pin(name, "f", "1") for name in "abc")
    first, second = plant.net("n1", (a, b)), plant.net("n2", (a,))
    model = plant.model()
    assert sorted(declared_nets_of(model, a)) == sorted((first, second))
    assert declared_nets_of(model, c) == ()


def test_port_item_and_one_board() -> None:
    plant = Plant()
    a, b = plant.pin("x", "f", "1"), plant.pin("y", "f", "1")
    model = plant.model()
    assert port_item(model, a) == make_id(Item, ("x",))
    assert not net_on_one_board(model, (a, b))
    assert not net_on_one_board(model, ())


def test_wired_mated_and_half_connected() -> None:
    plant = Plant()
    function = plant.function(plant.item("k1"), "f", kind=FunctionKind.COIL)
    a1, a2 = plant.port(function, "A1"), plant.port(function, "A2")
    other = plant.pin("other", "f", "1")
    plant.wire(a1, other, key="w")
    model = plant.model()
    assert wired_ports(model) == {a1, other}
    assert mated_ports(model) == frozenset()
    ((held, opened),) = half_connected(model)
    assert (held.id, opened.id) == (function, a2)


def test_mated_ports_covers_every_port_of_a_shared_name() -> None:
    plant = Plant()
    a, b = plant.pin("x", "f", "1"), plant.pin("y", "f", "1")
    plant.mate(make_id(Function, ("x", "f")), make_id(Function, ("y", "f")))
    assert mated_ports(plant.model()) == {a, b}


def test_potentials_without_supply_skips_declared_rails() -> None:
    plant = Plant()
    a, b = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    bare = plant.net("bare", (a,), potential="12V")
    plant.net("fed", (b,), potential="24V")
    plant.add(_supply("s", "S", "24V"))
    model = plant.model()
    assert potentials_without_supply(model) == ((bare, "12V"),)
    assert declared_rails(model) == ("24V",)


def test_supply_facts_group_by_name_and_potential() -> None:
    plant = Plant()
    plant.add(_supply("s1", "A", "24V"), _supply("s2", "A", "24V", "0V"))
    plant.add(_supply("s3", "B", "24V"))
    model = plant.model()
    assert sorted(s.key[0] for s in declarations_by_name(model)["A"]) == ["s1", "s2"]
    assert sorted(s.key[0] for s in supplies_by_potential(model)["24V"]) == ["s1", "s2", "s3"]
    assert list(supply_differences(model)) == ["A"]
    assert "rails" in supply_differences(model)["A"]
