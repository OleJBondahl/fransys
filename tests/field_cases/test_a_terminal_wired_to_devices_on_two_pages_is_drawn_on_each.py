"""Field case: a strip terminal wired to devices on two pages is drawn on each page.

The engineering shape: one unit holds a run of relays in one function, so many that, on a
coarse sheet module, the function spans several pages. Interface strip terminal X1:1 feeds every
coil, so its conductors end on different pages; X1:2 feeds the other coil pin
of K3 from one side and of K12 from the other, two nets of two ports each.
A second build chains the relays' other coil pins in a row, so a device-to-device conductor
crosses a page break.

The bug: layout stood one copy of the terminal and drew the conductor to a relay on another page
as a pair of link markers, a reference where a terminal symbol should stand. A reader follows a
reference to find the terminal.

The rule, decision layout-0216: there is never a reason to place a reference instead of a
terminal symbol. A conductor of a terminal whose far end is on a page is a route on that page,
and the terminal is drawn there. A device-to-device conductor between pages keeps its markers.
Decision model-0220 finishes it on one page: X1:1 stands at each coil it feeds, a copy per wire.
"""

import itertools
import tempfile
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.layout import (
    Label,
    LabelKind,
    LinkMarker,
    Route,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import conductors, functions, ports

_COUNT = 12
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
            u.detail.wire(terminal, relay.coil["A1"], wire=("WH", 0.75))
        if not chained:  # two two-port nets, one per side of X1:2
            u.detail.wire(feed[2], relays[2].coil["A2"], wire=("WH", 0.75))
            u.detail.wire(feed[2].outer, relays[-1].coil["A2"], wire=("WH", 0.75))
        if chained:
            for a, b in itertools.pairwise(relays):
                u.detail.wire(a.coil["A2"], b.coil["A2"], wire=("BU", 0.75))
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


def test_the_terminal_is_drawn_on_the_page_of_each_relay() -> None:
    model = _model()
    terminal = _x1_1_functions(model)
    stood = {p.page for p in layout_of(model, SymbolPlacement).values() if p.function in terminal}
    assert {_coil_page(model, 1), _coil_page(model, _far_relay(model))} <= stood


def test_each_conductor_of_the_terminal_is_a_route_on_its_relays_page() -> None:
    model = _model()
    routed = {(r.conductor, r.page) for r in layout_of(model, Route).values()}
    for n, conductor in _x1_conductors(model).items():
        assert (conductor.id, _coil_page(model, n)) in routed


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
    """X1:2's two nets end at K3 and K12, on two pages: the terminal stands on both, and each
    wire is a route on its relay's page with no marker at either end."""
    model = _model()
    terminal = {
        p.function for p in ports(model).values() if p.key[:4] == ("U1", "X1", "terminal", "2")
    }
    stood = {p.page for p in layout_of(model, SymbolPlacement).values() if p.function in terminal}
    routed = {(r.conductor, r.page) for r in layout_of(model, Route).values()}
    marked = {m.port for m in layout_of(model, LinkMarker).values()}
    assert _coil_page(model, 3) != _coil_page(model, 12)
    for n in (3, 12):
        pin = _coil(model, n, "A2")
        (conductor,) = (c for c in conductors(model).values() if pin in (c.a, c.b))
        assert _coil_page(model, n) in stood
        assert (conductor.id, _coil_page(model, n)) in routed
        assert not {conductor.a, conductor.b} & marked


def _copies(model: Any, page: Any) -> list[Any]:
    """The placements of X1:1's function on `page`."""
    terminal = _x1_1_functions(model)
    return [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if p.function in terminal and p.page == page
    ]


def test_k1s_page_draws_several_copies_of_x1_1() -> None:
    model = _model()
    assert len(_copies(model, _coil_page(model, 1))) >= 2


def test_each_copy_of_x1_1_has_its_own_tag() -> None:
    model = _model()
    page = _coil_page(model, 1)
    terminal = _x1_1_functions(model)
    tags = [
        t
        for t in layout_of(model, Label).values()
        if t.page == page and t.kind is LabelKind.TAG and t.function in terminal
    ]
    assert len(tags) == len(_copies(model, page)) >= 2


def _end_at(route: Any, port_ids: set[Any]) -> Any:
    """The route's end point at the one of `port_ids` it joins."""
    return route.points[0] if route.a in port_ids else route.points[-1]


def test_each_coil_a1_wire_ends_at_a_copy_beside_it() -> None:
    model = _model()
    terminal = _x1_1_functions(model)
    x1_ports = {p.id for p in ports(model).values() if p.function in terminal}
    routes = list(layout_of(model, Route).values())
    for n in range(1, _COUNT + 1):
        page, pin = _coil_page(model, n), _coil(model, n, "A1")
        (conductor,) = (c for c in conductors(model).values() if pin in (c.a, c.b))
        (route,) = (r for r in routes if r.conductor == conductor.id and r.page == page)
        end = _end_at(route, x1_ports)
        beside = [
            p
            for p in _copies(model, page)
            if abs(p.x - end.x) + abs(p.y - end.y) <= 12  # a copy, or the home at K1's pin
        ]
        assert beside, (n, end)


def test_every_drawn_id_is_a_model_id() -> None:
    """Guards stage-only handles from leaking into records."""
    model = _model()
    known_functions, known_ports = set(functions(model)), set(ports(model))
    assert {p.function for p in layout_of(model, SymbolPlacement).values()} <= known_functions
    routes = layout_of(model, Route).values()
    assert {r.a for r in routes} | {r.b for r in routes} <= known_ports
    assert {m.port for m in layout_of(model, LinkMarker).values()} <= known_ports
    for label in layout_of(model, Label).values():
        assert label.function is None or label.function in known_functions
        assert label.port is None or label.port in known_ports
        assert label.conductor is None or label.conductor in set(conductors(model))
