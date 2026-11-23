"""Field case: two plugs mated to a nested unit's connectors, pins 1-3 of both wired to the same pins of one device (KI-1069).
The bug: CONNECTION_NOT_DRAWN on the plugs' pins and the device pin, though each mated pin owes an OFF stub. Anchors KI-1090: INK_WITHOUT_CONDUCTOR.
Fixed at the root (R2578): `cut_loss.whole` and `restood`, called from `widen._stand` after the losses; up to three sibling plugs (R2580)."""

from functools import cache
from typing import NamedTuple, TypedDict

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU
from fransys_el import symbol_kit
from fransys_el.drawn_graph import Union
from fransys_el.drawn_netlist import drawn_netlist

from electrical_symbols import LIBRARY
from fransys_model.derive import port_designation


class _Release(TypedDict):
    revision: int
    interface_version: int
    date: str
    text: str
    by: str


_REL: _Release = {"revision": 1, "interface_version": 1, "date": "2026-11-16", "text": "First", "by": "XX"}
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


def test_the_child_page_joins_only_the_pins_its_own_conductors_join() -> None:
    """KI-1090 (R2578): on the child's page X1:1-X2:1 and X4:1-X5:1 are two wires; the plugs and U9 join them on the parent's page only."""
    result = _built(plugs=2, pins=3)
    net = drawn_netlist(result.model, symbol_kit(result.model, LIBRARY), result.drawings, (), LIBRARY)
    at = {port_designation(result.model, net.ids[key]): dict(placed) for key, placed in net.placed.items()}
    page = next(iter(at["-U1-U2-X2:1"]))
    ink = Union()
    for edge in net.pages[page].graph.edges:
        ink.join(*edge)
    root = {name: ink.find(at[f"-U1-U2-{name}:1"][page]) for name in ("X1", "X2", "X4", "X5")}
    assert root["X1"] == root["X2"] != root["X4"] == root["X5"]
