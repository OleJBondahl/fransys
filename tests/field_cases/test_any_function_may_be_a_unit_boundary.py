"""Field case: a cabinet unit's field cables land straight on a PLC channel, a relay coil or a supply output, with no strip between.
The bug: BOUNDARY_KIND (ERROR) rejected any non-terminal, non-connector boundary, and UNIT_BOUNDARY_BYPASSED followed without the mark.
Fixed by model-0188 (amending model-0038 U3), any function may be a unit's boundary."""

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.derive import item_of_port, item_unit, port_designation, printed_designation
from fransys_model.vocab.tables import conductors, ports, units
lazy from fransys_model.vocab.core import Unit

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

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
    c.series(field["1"], io.AI1.ai_1["1"], wire=("WH", 0.5))
    c.series(field["2"], io.AI1.ai_1["2"], wire=("WH", 0.5))


def _wire_relay(c: Any, io: _Relay) -> None:
    field = c.device("J1", "DEMO-CONN-2P")
    c.series(field["1"], io.K1.coil["A1"], wire=("WH", 0.5))
    c.series(field["2"], io.K1.coil["A2"], wire=("WH", 0.5))


def _wire_supply(c: Any, io: _Supply) -> None:
    lamp = c.device("H1", "DEMO-LAMP-24")
    c.series(lamp["1"], io.T1.output["+"], wire=("WH", 0.5))
    c.series(lamp["2"], io.T1.output["-"], wire=("WH", 0.5))


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
    assert [f.code for f in fr.build(_container(unit, wire)).findings if f.severity.name == "ERROR"] == []


@pytest.mark.parametrize("case", ["plc channel", "nested plc channel"])
def test_a_pin_column_hanging_under_a_framed_box_clears_the_frame(case: str) -> None:
    """The column stands off the box's grown footprint, so the unit's frame has room (place_y._attach_y)."""
    unit, wire = _CASES[case]
    assert "OUTLINE_NO_ROOM" not in {f.code for f in fr.build(_container(unit, wire)).findings}


# the container page's texts: the unit's title, the field device and, for the boundary ports,
# only their pin cells (a connector's, model-0188): never the item box or the symbol
_TITLE = {"plc channel": "demo-plc-cab", "relay coil": "demo-relay-cab", "supply output": "demo-supply-cab", "nested plc channel": "demo-plc-cab"}


def _page_texts(model: Model, container: Id[Unit]) -> list[str]:
    """Each conductor port's pin name, the container-relative designation of a field port, and each boundary item's once."""
    texts: list[str] = []
    for c in conductors(model).values():
        for end in (c.a, c.b):
            texts.append(ports(model)[end].name)
            item = item_of_port(model, end)
            if item_unit(model, item) == container:
                texts.append(port_designation(model, end, unit=container))
            else:
                texts.append(printed_designation(model, item, unit=container))
    boundary = {t for t in texts if t.startswith("-") and ":" not in t}
    return [t for t in texts if t not in boundary] + sorted(boundary)


@pytest.mark.parametrize("case", sorted(_CASES))
def test_the_container_page_draws_the_boundary_ports_as_pin_cells(case: str) -> None:
    """The container's own page prints each boundary port as a pin cell, no box, no symbol."""
    unit, wire = _CASES[case]
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-container", cover=root / "c.md")
    result = fr.build(_container(unit, wire), cover)
    fr.write(result, root / "out", intermediates=root / "inter")
    title = _TITLE[case]
    model = result.model
    (container,) = (u.id for u in units(model).values() if u.parent is None)
    expected = _page_texts(model, container)
    pages = [re.findall(r">([^<>]+)</text>", svg.read_text("utf-8")) for svg in (root / "inter").glob("layout.page-*.svg")]
    holding = [page for page in pages if f"{title} rev 1.1" in page]
    assert len(holding) == 1, f"expected one page printing the unit frame title '{title} rev 1.1', found {len(holding)}: no unit frame is drawn"
    texts = [t for t in holding[0] if t != f"{title} rev 1.1"]  # One per outline run
    assert sorted(texts) == sorted(expected)
