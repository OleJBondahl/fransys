"""Field case: a cabinet unit's field cables land straight on a PLC channel, a relay coil or a
supply output, with no strip between (model-0188).

The engineering shape: a cabinet unit holds a device, and its container wires a field device to
a channel, a coil pin or a supply output of that device. The unit marks the device an interface
(`interface=True`, or `interface=("coil",)` for one function). A nested case passes the boundary
up through a skid unit that holds the cabinet.

The bug: the build gave `BOUNDARY_KIND` (ERROR) for every function that was not a terminal or a
connector, and without the interface mark `UNIT_BOUNDARY_BYPASSED` once the cable was wired.
The rule (decision model-0188, amending model-0038 U3): any function may be a unit's boundary.
"""

import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}
_BAD = {"BOUNDARY_KIND", "UNIT_BOUNDARY_BYPASSED"}


class _Open(NamedTuple):
    pass


class _Plc(NamedTuple):
    AI1: Any


class _Relay(NamedTuple):
    K1: Any


class _Supply(NamedTuple):
    T1: Any


@fr.unit("demo-plc-cab", **_UNIT)
def _plc_cab(u: Any) -> _Plc:
    return _Plc(u.device("AI1", "DEMO-PLC-AI-4", interface=("ai_1",)))


@fr.unit("demo-relay-cab", **_UNIT)
def _relay_cab(u: Any) -> _Relay:
    return _Relay(u.device("K1", "DEMO-RLY-2CO-24", interface=("coil",)))


@fr.unit("demo-supply-cab", **_UNIT)
def _supply_cab(u: Any) -> _Supply:
    return _Supply(u.device("T1", "DEMO-PSU-24", interface=("output",)))


@fr.unit("demo-skid", **_UNIT)
def _skid(u: Any) -> _Plc:
    return _Plc(u.add(_plc_cab, "U2").AI1)


def _wire_plc(c: Any, io: _Plc) -> None:
    field = c.device("J1", "DEMO-CONN-2P")
    c.wire(field["1"], io.AI1.ai_1["1"], wire=("WH", 0.5))
    c.wire(field["2"], io.AI1.ai_1["2"], wire=("WH", 0.5))


def _wire_relay(c: Any, io: _Relay) -> None:
    field = c.device("J1", "DEMO-CONN-2P")
    c.wire(field["1"], io.K1.coil["A1"], wire=("WH", 0.5))
    c.wire(field["2"], io.K1.coil["A2"], wire=("WH", 0.5))


def _wire_supply(c: Any, io: _Supply) -> None:
    lamp = c.device("H1", "DEMO-LAMP-24")
    c.wire(lamp["1"], io.T1.output["+"], wire=("WH", 0.5))
    c.wire(lamp["2"], io.T1.output["-"], wire=("WH", 0.5))


_CASES = {
    "plc channel": (_plc_cab, _wire_plc),
    "relay coil": (_relay_cab, _wire_relay),
    "supply output": (_supply_cab, _wire_supply),
    "nested plc channel": (_skid, _wire_plc),
}


def _container(unit: Any, wire: Any) -> fr.Design:
    @fr.unit("demo-container", **_UNIT)
    def container(c: Any) -> _Open:
        wire(c, c.add(unit, "U1"))
        return _Open()

    d = fr.design("demo_parts")
    d.add(container, "C1", place=None)
    return d


@pytest.mark.parametrize("case", sorted(_CASES))
def test_a_direct_landing_on_any_function_builds_clean(case: str) -> None:
    unit, wire = _CASES[case]
    codes = {f.code for f in fr.build(_container(unit, wire)).findings}
    assert codes & _BAD == set()
    assert [
        f.code for f in fr.build(_container(unit, wire)).findings if f.severity.name == "ERROR"
    ] == []


# the container page's texts: the unit's title, the field device and, for the boundary ports,
# only their pin cells (a connector's, model-0188): never the item box or the symbol
_PAGE = {
    "plc channel": ("demo-plc-cab", ["-U1-AI1", "1", "2", "1", "2", "-J1"]),
    "relay coil": ("demo-relay-cab", ["-U1-K1", "A1", "A2", "1", "2", "-J1"]),
    "supply output": ("demo-supply-cab", ["-U1-T1:+", "-U1-T1:-", "-H1", "1", "2"]),
    "nested plc channel": ("demo-skid", ["-U1-U2-AI1", "1", "1", "2", "2", "-J1"]),
}


@pytest.mark.parametrize("case", sorted(_CASES))
def test_the_container_page_draws_the_boundary_ports_as_pin_cells(case: str) -> None:
    """The container's own page prints each boundary port as a pin cell, no box, no symbol."""
    unit, wire = _CASES[case]
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-container", cover=root / "c.md")
    result = fr.build(_container(unit, wire), cover)
    fr.write(result, root / "out", intermediates=root / "inter")
    title, expected = _PAGE[case]
    pages = [
        re.findall(r">([^<>]+)</text>", svg.read_text("utf-8"))
        for svg in (root / "inter").glob("layout.page-*.svg")
    ]
    (texts,) = (page for page in pages if f"{title} rev 1.1" in page)
    texts = [t for t in texts if t != f"{title} rev 1.1"]  # One per outline run
    assert sorted(texts) == sorted(expected)
