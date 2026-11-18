"""Field case: two plugs mated to a nested unit's connectors, pins 1-3 of both wired to the same pins of one device (KI-1069).
The bug: CONNECTION_NOT_DRAWN on the plugs' pins and the device pin, though each mated pin owes an OFF stub.
Fixed by model-0473 (R2529): a fallback reference joins the stub at its pin; a bare stub names every conductor that leaves."""

from functools import cache
from types import SimpleNamespace
from typing import NamedTuple, TypedDict

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU
from fransys_el.write_markers import _ends

from fransys_model.derive import far_pins
from fransys_model.vocab.tables import ports


class _Release(TypedDict):
    revision: int
    interface_version: int
    date: str
    text: str
    by: str


_REL: _Release = {"revision": 1, "interface_version": 1, "date": "2026-11-16", "text": "First", "by": "XX"}
_ORDER = ("a.A1", "a.A2", "b.B1", "b.B2", "c.C1", "c.C2")


class _Io(NamedTuple):
    x1: fr.Device
    x4: fr.Device


@fr.unit("mate-child", **_REL)
def _child(u: fr.Design) -> _Io:
    x1 = u.device("X1", "MATE-CONN-6", interface=True)
    x4 = u.device("X4", "MATE-CONN-6", interface=True)
    x2 = u.device("X2", "MATE-CONN-6")
    x5 = u.device("X5", "MATE-CONN-6")
    for a, b in ((x1, x2), (x4, x5)):
        for pin in "123456":
            u.series(a[pin], b[pin], wire=(BU, 0.5))
    return _Io(x1, x4)


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


@cache
def _built(*, plugs: int, pins: int) -> fr.BuildResult:
    @fr.unit("mate-parent", **_REL)
    def parent(u: fr.Design) -> _Open:
        child = u.add(_child, "U2")
        multi = u.device("U9", "MATE-MULTI")
        for n, end in enumerate((child.x1, child.x4)[:plugs]):
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


@pytest.mark.rule("STUB-FAR-POSITION")
def test_two_mated_plugs_wired_to_the_same_three_pins_of_one_device_draw_every_end() -> None:
    assert _undrawn(plugs=2, pins=3) == []


@pytest.mark.parametrize(("plugs", "pins"), [(2, 2)])
def test_two_pins_of_each_plug_draw_every_end(plugs: int, pins: int) -> None:
    assert _undrawn(plugs=plugs, pins=pins) == []


@pytest.mark.rule("STUB-FAR-POSITION")
def test_a_stub_with_no_named_far_names_every_conductor_that_leaves_its_pin() -> None:
    model = _built(plugs=2, pins=3).model
    a1 = next(p for p, port in ports(model).items() if port.name == "A1")
    marker = SimpleNamespace(end="A1", also=(), far=())
    named = {far for _, far, _ in _ends(SimpleNamespace(model=model, pin_ports={"A1": [a1]}), marker)}  # ty: ignore[invalid-argument-type] a two-field stand-in for the writer's context
    assert len(named) == 2
    assert named == {far for _, far in far_pins(model, [a1])}
