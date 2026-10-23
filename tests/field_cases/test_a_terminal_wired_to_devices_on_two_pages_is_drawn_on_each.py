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
from _drawn_pages import drawn_pages

from fransys_model.layout import LinkMarker, StarKind, layout_of
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


def _tagged(model: Any, text: str) -> list[tuple[Any, Any]]:
    """Each (page, drawing) that prints the tag `text` (`-U1-K3`)."""
    return [
        (page, drawing)
        for page, drawing in drawn_pages(model).items()
        if any(t.kind == "TAG" and t.text == text for t in drawing.texts)
    ]


def _coil_page(model: Any, n: int) -> Any:
    """The page that prints the tag of relay K`n`."""
    ((page, _),) = _tagged(model, f"-U1-K{n}")
    return page


def _owned(drawing: Any, text: str) -> list[Any]:
    """The symbols of `drawing` whose nearest tag is `text`."""
    tags = [t for t in drawing.texts if t.kind == "TAG"]
    return [
        one
        for one in drawing.symbols
        if tags
        and min(tags, key=lambda t: abs(t.box.x - one.x) + abs(t.box.y - one.y)).text == text
    ]


def _ends_near(drawing: Any, one: Any, slack: int = 24) -> list[tuple[Any, Any]]:
    """The (wire, other end) pairs whose one end is within `slack` of symbol `one`."""
    found = []
    for wire in drawing.wires:
        first, last = wire.points[0], wire.points[-1]
        for here, other in ((first, last), (last, first)):
            if abs(here[0] - one.x) + abs(here[1] - one.y) <= slack:
                found.append((wire, other))
    return found


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
    stood = {page for page, _ in _tagged(model, "-U1-X1:1")}
    assert {_coil_page(model, 1), _coil_page(model, _far_relay(model))} <= stood


def test_each_conductor_of_the_terminal_is_a_route_on_its_relays_page() -> None:
    model = _model()
    for n in _x1_conductors(model):
        drawing = drawn_pages(model)[_coil_page(model, n)]
        relay = _owned(drawing, f"-U1-K{n}")
        assert any(_ends_near(drawing, one) for one in relay)


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
    stood = {page for page, _ in _tagged(model, "-U1-X1:2")}
    marked = {m.port for m in layout_of(model, LinkMarker).values()}
    assert _coil_page(model, 3) != _coil_page(model, 12)
    for n in (3, 12):
        pin = _coil(model, n, "A2")
        (conductor,) = (c for c in conductors(model).values() if pin in (c.a, c.b))
        drawing = drawn_pages(model)[_coil_page(model, n)]
        assert _coil_page(model, n) in stood
        assert any(_ends_near(drawing, one) for one in _owned(drawing, f"-U1-K{n}"))
        assert not {conductor.a, conductor.b} & marked


def _copies(model: Any, page: Any) -> list[Any]:
    """The terminal symbols of X1:1 on `page`."""
    return [one for one in _owned(drawn_pages(model)[page], "-U1-X1:1") if one.key == "terminal"]


def test_k1s_page_draws_several_copies_of_x1_1() -> None:
    model = _model()
    assert len(_copies(model, _coil_page(model, 1))) >= 2


def test_each_copy_of_x1_1_has_its_own_tag() -> None:
    model = _model()
    page = _coil_page(model, 1)
    tags = [t for t in drawn_pages(model)[page].texts if t.kind == "TAG" and t.text == "-U1-X1:1"]
    assert len(tags) == len(_copies(model, page)) >= 2


def test_each_coil_a1_wire_ends_at_a_copy_beside_it() -> None:
    model = _model()
    for n in range(1, _COUNT + 1):
        page = _coil_page(model, n)
        drawing = drawn_pages(model)[page]
        copies = _copies(model, page)
        ends = [
            other for one in _owned(drawing, f"-U1-K{n}") for _, other in _ends_near(drawing, one)
        ]
        beside = [
            c
            for c in copies
            for x, y in ends
            if abs(c.x - x) + abs(c.y - y) <= 12  # a copy, or the home at K1's pin
        ]
        assert beside, n


def test_every_drawn_id_is_a_model_id() -> None:
    """Guards stage-only handles from leaking into records."""
    model = _model()
    known_ports = set(ports(model))
    assert {m.port for m in layout_of(model, LinkMarker).values()} <= known_ports
