"""Field case: a strip terminal wired to devices on two pages is drawn on each page.

The engineering shape: one unit holds a run of relays in one function, so many that, on a
coarse sheet module, the function spans several pages. Interface strip terminal X1:1 feeds every
coil, so its conductors end on different pages; X1:2 feeds the other coil pin
of K3 from one side and of K8 from the other, two nets of two ports each.
A second build chains the relays' other coil pins in a row, so a device-to-device conductor
crosses a page break.

The bug: layout stood one copy of the terminal and drew the conductor to a relay on another page
as a pair of link markers, a reference where a terminal symbol should stand. A reader follows a
reference to find the terminal.

The rule, decision layout-0216: there is never a reason to place a reference instead of a
terminal symbol. A conductor of a terminal whose far end is on a page is a route on that page,
and the terminal is drawn there. A device-to-device conductor between pages keeps its markers.
"""

import itertools
import tempfile
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import LinkMarker, Route, StarKind, SymbolPlacement, layout_of
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import conductors, functions, ports

_COUNT = 12
_XFAIL = pytest.mark.xfail(strict=True, reason="layout-0216: a terminal is drawn, not referenced")
_SHEET = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
}


class _Io(NamedTuple):
    feed: fr.TerminalStrip


def _bank(*, chained: bool):
    @fr.unit(
        "demo-two-pages", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB"
    )
    def bank(u: fr.Design) -> _Io:
        if not chained:
            u.layout.profile(sheet=u.layout.sheet("S3", **_SHEET, module_mm=Decimal("3.0")))
        feed = u.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=True)
        with u.function("R", "Relays"):
            relays = [u.device(f"K{i + 1}", "DEMO-RLY-2CO-24") for i in range(_COUNT)]
        for i, relay in enumerate(relays):
            terminal = feed[1 + i % 4] if chained else feed[1]
            u.wire(terminal, relay.coil["A1"], wire=("WH", 0.75))
        if not chained:  # two two-port nets, one per side of X1:2
            u.wire(feed[2], relays[2].coil["A2"], wire=("WH", 0.75))
            u.wire(feed[2].outer, relays[-5].coil["A2"], wire=("WH", 0.75))
        if chained:
            for a, b in itertools.pairwise(relays):
                u.wire(a.coil["A2"], b.coil["A2"], wire=("BU", 0.75))
        return _Io(feed)

    return bank


@cache
def _model(*, chained: bool = False) -> Any:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Two pages\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.add(_bank(chained=chained), "U1")
        document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-two-pages", cover=cover)
        return fr.build(d, document).model


def _coil(model: Any, n: int, pin: str) -> Any:
    """The id of coil pin `pin` of relay K`n`."""
    key = ("U1", f"R/K{n}", "fn", "coil", "port", pin)
    (found,) = (p.id for p in ports(model).values() if p.key == key)
    return found


def _coil_page(model: Any, n: int) -> Any:
    """The page of the placement of the function that owns the A1 pin of relay K`n`."""
    function = ports(model)[_coil(model, n, "A1")].function
    (page,) = {p.page for p in layout_of(model, SymbolPlacement).values() if p.function == function}
    return page


def _far_relay(model: Any) -> int:
    """The first relay that stands on another page than K1."""
    return next(n for n in range(2, _COUNT + 1) if _coil_page(model, n) != _coil_page(model, 1))


def _x1_1_functions(model: Any) -> set[Any]:
    """The terminal function of strip terminal X1:1."""
    return {p.function for p in ports(model).values() if p.key[:4] == ("U1", "X1", "terminal", "1")}


def _x1_conductors(model: Any) -> dict[int, Any]:
    """The conductor of terminal X1:1 to the A1 of K1 and of the far relay, by relay."""
    found = {}
    for n in (1, _far_relay(model)):
        (found[n],) = (c for c in conductors(model).values() if _coil(model, n, "A1") in (c.a, c.b))
    return found


def test_two_relays_fed_from_x1_1_stand_on_different_pages() -> None:
    model = _model()
    assert _coil_page(model, 1) != _coil_page(model, _far_relay(model))


@_XFAIL
def test_the_terminal_is_drawn_on_the_page_of_each_relay() -> None:
    model = _model()
    terminal = _x1_1_functions(model)
    stood = {p.page for p in layout_of(model, SymbolPlacement).values() if p.function in terminal}
    assert {_coil_page(model, 1), _coil_page(model, _far_relay(model))} <= stood


@_XFAIL
def test_each_conductor_of_the_terminal_is_a_route_on_its_relays_page() -> None:
    model = _model()
    routed = {(r.conductor, r.page) for r in layout_of(model, Route).values()}
    for n, conductor in _x1_conductors(model).items():
        assert (conductor.id, _coil_page(model, n)) in routed


@_XFAIL
def test_no_marker_stands_on_a_terminals_path() -> None:
    model = _model()
    terminals = {f.id for f in functions(model).values() if f.kind is FunctionKind.TERMINAL}
    markers = layout_of(model, LinkMarker)
    on_path = [
        m
        for m in markers.values()
        if m.star is not StarKind.OFF
        and terminals
        & {ports(model)[m.port].function, ports(model)[markers[m.partner].port].function}
    ]
    assert on_path == []


def test_a_device_to_device_conductor_across_pages_keeps_its_marker_pair() -> None:
    """Passes today and must keep passing: a mutation that draws every cross-page wire as a
    route, or drops the marker pair of a device wire, fails it."""
    model = _model(chained=True)
    markers = layout_of(model, LinkMarker)
    pairs = [
        (m, markers[m.partner])
        for m in markers.values()
        if m.star is None
        and ports(model)[m.port].key[-1] == ports(model)[markers[m.partner].port].key[-1] == "A2"
    ]
    assert pairs
    assert all(b.star is None and a.page != b.page for a, b in pairs)


def test_a_terminal_wired_to_one_device_on_another_page_is_drawn_and_routed_there() -> None:
    """X1:2's two nets end at K3 and K8, on two pages: the terminal stands on both, and each
    wire is a route on its relay's page with no marker at either end."""
    model = _model()
    terminal = {
        p.function for p in ports(model).values() if p.key[:4] == ("U1", "X1", "terminal", "2")
    }
    stood = {p.page for p in layout_of(model, SymbolPlacement).values() if p.function in terminal}
    routed = {(r.conductor, r.page) for r in layout_of(model, Route).values()}
    marked = {m.port for m in layout_of(model, LinkMarker).values()}
    assert _coil_page(model, 3) != _coil_page(model, 8)
    for n in (3, 8):
        pin = _coil(model, n, "A2")
        (conductor,) = (c for c in conductors(model).values() if pin in (c.a, c.b))
        assert _coil_page(model, n) in stood
        assert (conductor.id, _coil_page(model, n)) in routed
        assert not {conductor.a, conductor.b} & marked
