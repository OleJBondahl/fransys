"""`function_is_loose`: a function with nothing connected (layout-0218, model-0226)."""

from plant import Plant

from fransys_model.derive import function_is_loose
from fransys_model.vocab.enums import FunctionKind


def test_a_wired_function_is_not_loose_and_an_unwired_one_is() -> None:
    plant = Plant()
    plant.wire(plant.pin("K1", "coil", "A1"), plant.pin("X1", "t1", "1"), key="w1")
    plant.pin("K2", "coil", "A1")
    model = plant.model()
    assert not function_is_loose(model, plant.function_id("K1", "coil"))
    assert not function_is_loose(model, plant.function_id("X1", "t1"))
    assert function_is_loose(model, plant.function_id("K2", "coil"))


def test_a_net_of_one_port_connects_nothing_a_net_of_two_does() -> None:
    plant = Plant()
    plant.net("alone", (plant.pin("A", "f", "1"),))
    plant.net("pair", (plant.pin("B", "f", "1"), plant.pin("C", "f", "1")))
    model = plant.model()
    assert function_is_loose(model, plant.function_id("A", "f"))
    assert not function_is_loose(model, plant.function_id("B", "f"))
    assert not function_is_loose(model, plant.function_id("C", "f"))


def test_a_mated_function_counts_its_mates_ports() -> None:
    plant = Plant()
    plant.wire(plant.pin("XS", "plug", "1"), plant.pin("M", "f", "1"), key="w1")
    plant.pin("XP", "socket", "1")
    plant.mate(plant.function_id("XP", "socket"), plant.function_id("XS", "plug"))
    assert not function_is_loose(plant.model(), plant.function_id("XP", "socket"))


def test_one_wired_pole_keeps_its_items_same_kind_poles_only() -> None:
    """A three-pole breaker with pole 1 wired is drawn whole; its auxiliary contact is not kept."""
    plant = Plant()
    item = plant.item("Q1")
    poles = [plant.function(item, f"pole_{n}", kind=FunctionKind.CONTACT_NO) for n in (1, 2, 3)]
    aux = plant.function(item, "aux", kind=FunctionKind.CONTACT_NC)
    for function in (*poles, aux):
        plant.port(function, "1")
    plant.wire(plant.pin("Q1", "pole_1", "1"), plant.pin("X1", "t1", "1"), key="w1")
    model = plant.model()
    assert not any(function_is_loose(model, pole) for pole in poles)
    assert function_is_loose(model, aux)
