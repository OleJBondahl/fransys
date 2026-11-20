"""Field case: two plugs mated to a nested unit's connectors, pins 1-3 of both wired to the same pins of one device (KI-1069).
The bug: CONNECTION_NOT_DRAWN on the plugs' pins and the device pin, though each mated pin owes an OFF stub.
Fixed at the root (R2578): `cut_ledger.whole` and `restood`, called from `widen._stand` after the losses; up to three sibling plugs (R2580)."""

import importlib
from dataclasses import replace
from functools import cache
from typing import NamedTuple, TypedDict

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_layout.core.outputs import Refused
from fransys_layout.core.route_env import lost_key


class _Release(TypedDict):
    revision: int
    interface_version: int
    date: str
    text: str
    by: str


_REL: _Release = {"revision": 1, "interface_version": 1, "date": "2026-11-16", "text": "First", "by": "XX"}
widen = importlib.import_module("fransys_layout.core.widen")
_ORDER = ("a.A1", "a.A2", "b.B1", "b.B2", "c.C1", "c.C2")


class _Io2(NamedTuple):
    x1: fr.Device
    x4: fr.Device


class _Io3(NamedTuple):
    x1: fr.Device
    x4: fr.Device
    x7: fr.Device


def _joined_connectors(u: fr.Design, pairs: tuple[tuple[str, str], ...]) -> tuple[fr.Device, ...]:
    """Each (interface, inner) connector pair of `pairs` wired pin for pin to an inner one, which the parent's plug mates through."""
    outer: list[fr.Device] = []
    for name, inner_name in pairs:
        outer.append(u.device(name, "MATE-CONN-6", interface=True))
        inner = u.device(inner_name, "MATE-CONN-6")
        for pin in "123456":
            u.series(outer[-1][pin], inner[pin], wire=(BU, 0.5))
    return tuple(outer)


@fr.unit("mate-child", **_REL)
def _child(u: fr.Design) -> _Io2:
    return _Io2(*_joined_connectors(u, (("X1", "X2"), ("X4", "X5"))))


@fr.unit("mate-child-three", **_REL)
def _child_three(u: fr.Design) -> _Io3:
    return _Io3(*_joined_connectors(u, (("X1", "X2"), ("X4", "X5"), ("X7", "X8"))))


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


@cache
def _built(*, plugs: int, pins: int) -> fr.BuildResult:
    @fr.unit("mate-parent", **_REL)
    def parent(u: fr.Design) -> _Open:
        child = u.add(_child_three if plugs == 3 else _child, "U2")
        multi = u.device("U9", "MATE-MULTI")
        for n, end in enumerate(child[:plugs]):
            plug = u.device(None, "MATE-CONN-6", name=f"plug{n}")
            u.mate(plug, end)
            for pin, spec in enumerate(_ORDER[:pins], 1):
                fn, port = spec.split(".")
                u.series(plug[str(pin)], getattr(multi, fn)[port], wire=(BU, 0.5))
        return _Open()

    d = fr.design("demo_parts", "mate_parts")
    top = d.add(parent, "U1")
    return fr.build(d, unit_document(top))


def _undrawn(*, plugs: int, pins: int) -> list[str]:
    return [f.message for f in _built(plugs=plugs, pins=pins).findings if f.code == "CONNECTION_NOT_DRAWN"]


@pytest.mark.parametrize(("plugs", "pins"), [(2, 3), (2, 5), (2, 6), (3, 2), (3, 3)])
def test_mated_plugs_wired_to_the_same_pins_of_one_device_draw_every_end(plugs: int, pins: int) -> None:
    """KI-1069 (R2578, R2580): the ends of every sibling plug are drawn, and no stub names a far end that has no conductor."""
    codes = {f.code for f in _built(plugs=plugs, pins=pins).findings}
    assert codes.isdisjoint({"CONNECTION_NOT_DRAWN", "PLACEMENT_PROBLEM"})


def test_a_forced_loss_of_one_plug_pin_leaves_no_dangling_wire_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """R2618: the router loses the first pin of plug0 in round 1 (2 plugs x 2 pins); the wires and the markers of the next round agree."""
    real = widen.route_pages

    def lose_one(placement, cut, problem, options, laid):
        routes = real(placement, cut, problem, options, laid)
        net = problem.nets[0]
        if lost_key(net.id, net.pins[:1]) in laid.lost:
            return routes
        return replace(routes, failed=(*routes.failed, Refused(net.id, net.pins[:1])))

    monkeypatch.setattr(widen, "route_pages", lose_one)
    codes = {f.code for f in _built.__wrapped__(plugs=2, pins=2).findings}
    assert "DANGLING_WIRE_END" not in codes
