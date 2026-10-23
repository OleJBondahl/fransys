"""`connected_ports`: the ports the schematic engine counts as wired (model-0325, amended)."""

from plant import Plant

from fransys_model.derive import connected_ports
from fransys_model.vocab.enums import ConductorKind


def test_a_wire_and_a_net_connect_their_ports_and_a_bare_port_is_not() -> None:
    plant = Plant()
    a, b = plant.pin("K1", "aux", "13"), plant.pin("K1", "aux", "14")
    c, bare = plant.pin("K2", "aux", "13"), plant.pin("K2", "aux", "14")
    plant.wire(a, b, key="w")
    plant.net("n", (c,))
    found = connected_ports(plant.model())
    assert {a, b, c} <= found
    assert bare not in found


def test_a_jumper_connects_nothing() -> None:
    plant = Plant()
    a, b = plant.pin("K1", "aux", "13"), plant.pin("K1", "aux", "14")
    plant.wire(a, b, key="j", kind=ConductorKind.JUMPER)
    assert connected_ports(plant.model()) == frozenset()
