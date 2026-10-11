"""Every finding code of `check_connectivity`, firing and not firing."""

from typing import Any

from plant import Plant

from fransys_model.kernel import Finding, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.validators.connectivity import (
    NET_SHORTED,
    check_connectivity,
)


def _of(plant: Plant, code: str) -> list[Finding]:
    return [f for f in check_connectivity(plant.model()) if f.code == code]


# ---- NET_UNREALISED -----------------------------------------------------------------------


# ---- board realisation --------------------------------------------------------------------


# ---- NET_SHORTED and NET_POTENTIAL_CONFLICT -----------------------------------------------


def _rails(plant: Plant) -> tuple[Any, ...]:
    ports = [plant.pin(name, "f", "1") for name in "abcdef"]
    return tuple(ports)


# ---- PORT_UNCONNECTED ---------------------------------------------------------------------


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
