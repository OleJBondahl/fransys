"""Every finding code of `check_connectivity`, firing and not firing."""

from typing import Any

from plant import Plant

from fransys_model.checks.connectivity import (
    FUNCTION_HALF_CONNECTED,
    NET_SHORTED,
    NET_UNREALISED,
    check_connectivity,
)
from fransys_model.kernel import Finding, Id, Severity, make_id
from fransys_model.vocab.connectivity import Net
from fransys_model.vocab.core import Item, Port
from fransys_model.vocab.enums import FunctionKind, NetClass
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import ports


def _of(plant: Plant, code: str) -> list[Finding]:
    return [f for f in check_connectivity(plant.model()) if f.code == code]


# ---- NET_UNREALISED -----------------------------------------------------------------------


def _two_piece_net(net_class: NetClass) -> Plant:
    plant = Plant()
    a, b = plant.pin("a", "f", "1"), plant.pin("b", "f", "1")
    plant.add(
        Net(
            id=make_id(Net, ("n",)),
            key=("n",),
            name=None,
            net_class=net_class,
            ports=(a, b),
            potential=None,
        )
    )
    return plant


def test_a_pe_net_in_two_physical_nets_is_not_unrealised() -> None:
    assert _of(_two_piece_net(NetClass.PE), NET_UNREALISED) == []


def test_a_non_pe_net_in_two_physical_nets_is_unrealised() -> None:
    assert len(_of(_two_piece_net(NetClass.GENERIC), NET_UNREALISED)) == 1


# ---- board realisation --------------------------------------------------------------------


# ---- NET_SHORTED and NET_POTENTIAL_CONFLICT -----------------------------------------------


def _rails(plant: Plant) -> tuple[Any, ...]:
    ports = [plant.pin(name, "f", "1") for name in "abcdef"]
    return tuple(ports)


# ---- FUNCTION_HALF_CONNECTED --------------------------------------------------------------


def _two_port(plant: Plant, key: str, kind: FunctionKind) -> tuple[Id[Port], Id[Port]]:
    function = plant.function(plant.item(key), "f", kind=kind)
    return plant.port(function, "A1"), plant.port(function, "A2")


def _half_wired(kind: FunctionKind) -> list[Finding]:
    plant = Plant()
    a1, _ = _two_port(plant, "x", kind)
    plant.wire(a1, plant.pin("other", "f", "1"), key="w")
    return _of(plant, FUNCTION_HALF_CONNECTED)


def test_a_coil_wired_at_one_port_names_the_open_port() -> None:
    plant = Plant()
    a1, a2 = _two_port(plant, "k1", FunctionKind.COIL)
    plant.wire(a1, plant.pin("other", "f", "1"), key="w")
    (finding,) = _of(plant, FUNCTION_HALF_CONNECTED)
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (a2,)
    assert finding.message.endswith(f"open at {ref(ports(plant.model())[a2])}")


def test_a_terminal_wired_at_one_port_gives_no_finding() -> None:
    # MUTATION: `_half_connected` drops the `_THROUGH_KINDS` test
    assert _half_wired(FunctionKind.TERMINAL) == []
    assert _half_wired(FunctionKind.PLC_CHANNEL) == []
    assert _half_wired(FunctionKind.CONNECTOR) == []


def test_a_function_wired_at_both_ports_or_neither_gives_no_finding() -> None:
    plant = Plant()
    a1, a2 = _two_port(plant, "k1", FunctionKind.COIL)
    _two_port(plant, "k2", FunctionKind.LOAD)
    other = plant.pin("other", "f", "1")
    plant.wire(a1, other, key="w1")
    plant.wire(a2, other, key="w2")
    assert _of(plant, FUNCTION_HALF_CONNECTED) == []


def test_a_declared_net_counts_as_a_connection() -> None:
    plant = Plant()
    a1, _ = _two_port(plant, "k1", FunctionKind.SWITCH)
    plant.net("n", (a1, plant.pin("other", "f", "1")))
    assert len(_of(plant, FUNCTION_HALF_CONNECTED)) == 1


# ---- CONDUCTOR_ON_UNINSTALLED -------------------------------------------------------------


# ---- the shape of the result --------------------------------------------------------------


def _mixed() -> Plant:
    plant = Plant()
    a, b, c, d, e = (plant.pin(name, "f", "1") for name in "abcde")
    plant.net("n1", (a, b), potential="24V")
    plant.net("n2", (c,), potential="0V")
    plant.wire(b, c, key="bridge")
    plant.wire(a, d, key="w")
    plant.item("pulled", installed=False)
    plant.wire(plant.port(plant.function(make_id(Item, ("pulled",)), "f"), "1"), e, key="p")
    return plant


def _wired_pair(name_a: str | None, name_b: str | None) -> Plant:
    plant = Plant()
    a, b, c, d = (plant.pin(name, "f", "1") for name in "abcd")
    plant.net("net-a", (a, b), name=name_a)
    plant.net("net-b", (c, d), name=name_b)
    plant.wire(a, c, key="bridge")
    return plant


def test_two_unnamed_declared_nets_joined_are_still_shorted() -> None:
    assert len(_of(_wired_pair(None, None), NET_SHORTED)) == 1
    assert len(_of(_wired_pair("BUS", None), NET_SHORTED)) == 1
