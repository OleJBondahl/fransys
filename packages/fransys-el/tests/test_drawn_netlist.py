"""The drawn netlist is checked against the model (DRAWN-NETLIST, el-0052).

A clean build raises none of the sweep's codes. Each class is planted as a small patch to a
finished drawing: join two nets, move a wire end to a neighbour port, drop a junction dot, unpair a
"""

from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, NamedTuple, cast

import fransys as fr
import pytest
from _card_case import card_case_drafts
from _expected_codes import expect_codes
from _model_build_cover import unit_document
from conventions_fixtures import house
from fransys.colours import GNYE
from fransys_el import build, drawn_identity_marks, drawn_power, drawn_rails, lay_out_core, lay_out_drawn, symbol_kit
from fransys_el import drawn_netlist as drawn_netlist_module
from fransys_el.drawn_graph import Union
from fransys_el.drawn_netlist import Netlist, drawn_netlist, is_marker, with_lines
from fransys_el.drawn_nets import _ends, _pairs, _stubs, _unmarked, _verdict, not_drawn_findings
from fransys_el.drawn_pairs import dangling_findings
from fransys_el.drawn_power import join_power, power_findings
from fransys_el.drawn_rails import rail_findings
from fransys_el.drawn_shorts import ink_findings, short_findings
from fransys_el.drawn_sweep import drawing_sweep
from fransys_el.placement_ids import net_key
from ring_cases import bank_model, box_kit

from electrical_symbols import LIBRARY, power_symbol_key
from fransys_layout.core import Box, page_graph
from fransys_layout.drawing import DrawnSymbol, DrawnWire
from fransys_model.derive import PowerKind, net_of, port_power_kind, required_groups
from fransys_model.kernel import Id, make_id
from fransys_model.layout import LinkMarker, MarkerPair, MarkerSide, Page, Side, StarKind
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.drawing import Drawing

CODES = {
    "CONNECTION_NOT_DRAWN",
    "DRAWING_SHORTS_NETS",
    "ROUTE_WRONG_PORT",
    "MARKER_UNPAIRED",
    "CONNECTION_DRAWN_TWICE",
    "WIRE_NOT_ORTHOGONAL",
    "MISSING_JUNCTION_DOT",
    "DANGLING_WIRE_END",
}


@dataclass(frozen=True)
class Built:
    """What the sweep of one build was given: the model, kit, drawings and marker records."""

    model: Any
    kit: Any
    drawings: dict[Any, Any]
    markers: Any
    lines: Any

    def codes(self, drawings: dict[Any, Any] | None = None) -> set[str]:
        """The sweep's codes (and OVERLAP) over `drawings`, or the build's own."""
        got = drawing_sweep(self.model, self._net(drawings or self.drawings))
        return {f.code for f in got}

    def count(self, code: str, drawings: dict[Any, Any] | None = None) -> int:
        """How many findings of `code` the sweep gives over `drawings`, or the build's own."""
        return len(self.messages(code, drawings or self.drawings))

    def messages(self, code: str, drawings: dict[Any, Any]) -> list[str]:
        return [f.message for f in drawing_sweep(self.model, self._net(drawings)) if f.code == code]

    def _net(self, drawings: dict[Any, Any]):
        return with_lines(drawn_netlist(self.model, self.kit, drawings, self.markers, LIBRARY), self.model, self.kit, self.lines)

    def netlist(self):
        return self._net(self.drawings)

    def patched(self, page, **fields) -> dict[Any, Any]:
        """The drawings with `page`'s drawing replaced by the same with `fields` changed."""
        return {**self.drawings, page: replace(self.drawings[page], **fields)}


def _built(bank: int, monkeypatch: pytest.MonkeyPatch, *, symbols: bool = False) -> Built:
    model = fr.build(*card_case_drafts(bank)).model if symbols else bank_model(bank)
    return _built_of(model, symbol_kit(model, LIBRARY) if symbols else box_kit(model), monkeypatch)


def _built_of(model: Any, kit: Any, monkeypatch: pytest.MonkeyPatch) -> Built:
    conventions = house()
    problem, _ = build(model, kit, conventions, LIBRARY)
    caught: list[tuple[Any, ...]] = []
    original, lines_of = lay_out_core.drawn_netlist, lay_out_core.with_lines

    def spy(*args):
        caught.append(args)
        return original(*args)

    def spy_lines(net, laid, kit, lines):
        caught.append(lines)
        return lines_of(net, laid, kit, lines)

    monkeypatch.setattr(lay_out_core, "drawn_netlist", spy)
    monkeypatch.setattr(lay_out_core, "with_lines", spy_lines)
    lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    (laid, _, drawings, markers, _), lines = caught
    return Built(laid, kit, dict(drawings), markers, lines)


@pytest.fixture(scope="module")
def bank8():
    with pytest.MonkeyPatch.context() as patch:
        return _built(8, patch)


@pytest.fixture(scope="module")
def card16():
    with pytest.MonkeyPatch.context() as patch:
        return _built(16, patch, symbols=True)


@pytest.fixture(scope="module")
def bank40():
    with pytest.MonkeyPatch.context() as patch:
        return _built(40, patch)


def _at(part, point) -> str | None:
    return next((str(p) for p, at in part.ports.items() if at == point), None)


def _wire_between_ports(built: Built):
    """(page, index) of a one-lane wire with a port at each end, found in the build."""
    for page, part in built.netlist().pages.items():
        for i, wire in enumerate(part.drawing.wires):
            ends = (_at(part, wire.points[0]), _at(part, wire.points[-1]))
            if all(ends) and ends[0] != ends[1]:
                return page, i
    pytest.fail("no wire between two ports")


def test_a_clean_build_raises_none_of_the_sweeps_codes(bank8, bank40):
    """The bank of 8 raises no code of the sweep since ROUTING's guard (R439)."""
    assert bank8.codes() & CODES == set()
    assert bank40.codes() & {"ROUTE_WRONG_PORT", "MARKER_UNPAIRED", "CONNECTION_DRAWN_TWICE"} == set()


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_that_joins_two_nets_is_a_short(bank8):
    net = bank8.netlist()
    page, part = next(iter(net.pages.items()))
    first = next(iter(part.ports))
    other = next(p for p in part.ports if net.net(p) != net.net(first))
    (ax, ay), (bx, by) = part.ports[first], part.ports[other]
    bridge = DrawnWire("bridge", ((ax, ay), (ax, by), (bx, by)), part.drawing.wires[0].style)
    planted = bank8.patched(page, wires=(*part.drawing.wires, bridge))
    assert bank8.count("DRAWING_SHORTS_NETS", planted) > bank8.count("DRAWING_SHORTS_NETS")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_moved_to_a_neighbour_port_is_a_wrong_port(bank8):
    page, i = _wire_between_ports(bank8)
    part = bank8.netlist().pages[page]
    wire = part.drawing.wires[i]
    mine = bank8.netlist().net(_at(part, wire.points[-1]))
    other = next(at for p, at in part.ports.items() if bank8.netlist().net(p) != mine)
    moved = replace(wire, points=(*wire.points[:-1], other))
    wires = tuple(moved if k == i else w for k, w in enumerate(part.drawing.wires))
    assert bank8.count("ROUTE_WRONG_PORT", bank8.patched(page, wires=wires)) > bank8.count("ROUTE_WRONG_PORT")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_dropped_leaves_its_connection_missing(bank8):
    page, i = _wire_between_ports(bank8)
    wires = tuple(w for k, w in enumerate(bank8.drawings[page].wires) if k != i)
    assert bank8.count("CONNECTION_NOT_DRAWN", bank8.patched(page, wires=wires)) > bank8.count("CONNECTION_NOT_DRAWN")


def _off_stub(net, port: str, far: str, at) -> tuple[dict[Any, Any], dict[Any, Any]]:
    """`net`'s records and markers with an off stub at `port` naming `far`, drawn at `at`."""
    ident = make_id(LinkMarker, ("t", port))
    stub = LinkMarker(
        id=ident, key=("t", port), page=at[0], port=net.ids[port], side=MarkerSide.OWNER, partner=ident, x=0, y=0,
        width=1, height=1, produced_by="t", star=StarKind.OFF, pairs=(MarkerPair(port=net.ids[port], far=net.ids[far]),), facing=Side.N,
    )  # fmt: skip
    return {**net.records, ident.value: stub}, {**net.markers, ident.value: at}


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_pair_with_an_end_off_the_document_is_drawn_only_when_its_near_end_shows_the_stub(bank8):
    """R685: the stub's data (port, far) is compared, not its text."""
    net = bank8.netlist()
    near, far, *_ = next(g for g in required_groups(bank8.model) if len(g) == 2 and all(p.value in net.placed for p in g))
    near, far = near.value, far.value
    other = next(p for p in net.placed if p not in (near, far))
    cut = replace(net, placed={p: v for p, v in net.placed.items() if p != far})

    def count(n) -> int:
        return len(not_drawn_findings(bank8.model, n))

    right, wrong = (
        replace(cut, **dict(zip(("records", "markers"), _off_stub(cut, near, f, cut.placed[near][0]), strict=True))) for f in (far, other)
    )
    assert count(right) < count(cut) == count(wrong)

    # R1573, R1611: a far port drawn in no piece is covered only by a stub at the near end naming it
    owed = [(near, far) in _unmarked(bank8.model, n, s := _stubs(n), _pairs(n, s)) for n in (net, cut, right, wrong)]
    assert owed == [False, True, False, True]


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_second_path_between_two_ports_is_a_connection_drawn_twice(bank8):
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (ax, ay), (bx, by) = wire.points[0], wire.points[-1]
    detour = DrawnWire("again", ((ax, ay), (ax + 8, ay), (ax + 8, by), (bx, by)), wire.style)
    planted = bank8.patched(page, wires=(*bank8.drawings[page].wires, detour))
    assert bank8.count("CONNECTION_DRAWN_TWICE", planted) > bank8.count("CONNECTION_DRAWN_TWICE")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_cut_short_ends_on_nothing(bank8):
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (x1, y1), (x2, y2) = wire.points[-2:]
    cut = DrawnWire(wire.net, (*wire.points[:-1], ((x1 + x2) // 2, (y1 + y2) // 2)), wire.style)
    wires = tuple(cut if j == i else w for j, w in enumerate(bank8.drawings[page].wires))
    assert bank8.messages("DANGLING_WIRE_END", bank8.patched(page, wires=wires)) == [f"wire end at {(x1 + x2) // 2}, {(y1 + y2) // 2}"]


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_lying_along_another_wire_is_not_met_by_it(bank8):
    """KI-365: a wire laid collinear over part of another wire ends on nothing; only a wire end on its interior across, or a dot, meets."""
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (x1, y1), (x2, y2) = wire.points[-2:]
    a, b = (x1 + (x2 - x1) // 4, y1 + (y2 - y1) // 4), (x1 + (x2 - x1) * 3 // 4, y1 + (y2 - y1) * 3 // 4)
    along = DrawnWire(wire.net, (a, b), wire.style)
    planted = bank8.patched(page, wires=(*bank8.drawings[page].wires, along))
    assert sorted(bank8.messages("DANGLING_WIRE_END", planted)) == sorted(f"wire end at {x}, {y}" for x, y in (a, b))


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_lying_along_another_wire_is_met_where_a_dot_lies_on_the_run(bank8):
    """R1665: the same overlap with a junction dot on the shared run is a joined bus, so both ends are met."""
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (x1, y1), (x2, y2) = wire.points[-2:]
    a, b = (x1 + (x2 - x1) // 4, y1 + (y2 - y1) // 4), (x1 + (x2 - x1) * 3 // 4, y1 + (y2 - y1) * 3 // 4)
    x, y = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
    dot = DrawnSymbol("planted-dot", "junction-dot", x, y, "R0", outline=Box(x - 1, y - 1, 2, 2))
    drawing = bank8.drawings[page]
    planted = bank8.patched(page, wires=(*drawing.wires, DrawnWire(wire.net, (a, b), wire.style)), symbols=(*drawing.symbols, dot))
    assert bank8.messages("DANGLING_WIRE_END", planted) == []


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_lying_along_another_wire_needs_a_dot_at_the_end_itself(bank8):
    """R1861 (CORRECTNESS-PROOF S0 R6, T needs a dot): a dot further along the shared run does not meet the start of the overlap."""
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (x1, y1), (x2, y2) = wire.points[-2:]
    a, b = (x1 + (x2 - x1) // 4, y1 + (y2 - y1) // 4), (x1 + (x2 - x1) * 3 // 4, y1 + (y2 - y1) * 3 // 4)
    x, y = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
    dot = DrawnSymbol("planted-dot", "junction-dot", x, y, "R0", outline=Box(x - 1, y - 1, 2, 2))
    drawing = bank8.drawings[page]
    planted = bank8.patched(page, wires=(*drawing.wires, DrawnWire(wire.net, (a, b), wire.style)), symbols=(*drawing.symbols, dot))
    assert sorted(bank8.messages("DANGLING_WIRE_END", planted)) == sorted(f"wire end at {px}, {py}" for px, py in (a, b))


def _drop_first(built: Built, wanted, code: str) -> None:
    """Dropping the first symbol `wanted` picks on any page raises `code` over the build's own count."""
    for page, part in built.netlist().pages.items():
        found = [s for s in part.drawing.symbols if wanted(s)]
        if found:
            kept = tuple(s for s in part.drawing.symbols if s is not found[0])
            assert built.count(code, built.patched(page, symbols=kept)) > built.count(code)
            return
    pytest.fail(f"no symbol for {code} in the bank of 40")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_marker_whose_partner_is_not_drawn_is_unpaired(bank40):
    net = bank40.netlist()
    for page, part in net.pages.items():
        marks = [s for s in part.drawing.symbols if is_marker(s) and (r := net.records.get(s.id.rpartition(":")[2])) and r.star is not StarKind.OFF]
        if marks:
            kept = tuple(s for s in part.drawing.symbols if s is not marks[0])
            assert bank40.count("MARKER_UNPAIRED", bank40.patched(page, symbols=kept)) > bank40.count("MARKER_UNPAIRED")
            return
    pytest.fail("no paired reference marker in the bank of 40")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_junction_dot_dropped_leaves_a_dotless_t(bank40):
    _drop_first(bank40, lambda s: s.key == "junction-dot", "MISSING_JUNCTION_DOT")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_diagonal_segment_is_not_orthogonal(bank8):
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (ax, ay) = wire.points[0]
    bent = replace(wire, points=((ax, ay), (ax + 8, ay + 8), wire.points[-1]))
    wires = tuple(bent if k == i else w for k, w in enumerate(bank8.drawings[page].wires))
    assert bank8.count("WIRE_NOT_ORTHOGONAL", bank8.patched(page, wires=wires)) > bank8.count("WIRE_NOT_ORTHOGONAL")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_through_a_body_is_an_overlap(bank8):
    page = next(iter(bank8.drawings))
    drawing = cast("Drawing", bank8.drawings[page])
    body = next(s.outline for s in drawing.symbols if s.outline and s.outline.w > 8)
    y = body.y + body.h // 2
    across = DrawnWire("across", ((body.x - 8, y), (body.x + body.w + 8, y)), drawing.wires[0].style)
    planted = bank8.patched(page, wires=(*drawing.wires, across))
    before = len(bank8.messages("OVERLAP", bank8.drawings))
    assert len(bank8.messages("OVERLAP", planted)) == before + 1


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_stub_on_a_line_ends_every_port_of_that_line_on_its_page():
    """R481, R754: a stub is an end for each conductor of its line, so a port on the line needs none of its own."""
    p1, p2 = (Id[Page](kind="page", value=v) for v in ("p1", "p2"))
    places: dict[Any, Any] = {"a": ((p1, (0, 0)),), "b": ((p2, (0, 0)),), "c": ((p1, (1, 1)),)}
    home = {"a": frozenset({p1}), "b": frozenset({p2}), "c": frozenset({p1})}
    net = Netlist({}, Union(), places, {}, {}, {}, lined={"a": "L", "b": "L", "c": "M"}, stub_lines={(p1, "L")}, home=home)
    assert _ends(net, {"a"}, ["a", "z"], {})
    assert not _ends(net, {"b"}, ["b", "z"], {})
    assert not _ends(net, {"c"}, ["c", "z"], {})
    assert not _ends(net, {"a"}, ["a"], {})


def _homed(places: dict[Any, Any], joined: Sequence[Any] = (), bare: Sequence[Any] = ()) -> Netlist:
    """Ports `places` (first point of each is its home page, later ones copies) with every listed point a node; `joined` pairs are one piece."""
    pages: dict[Any, Any] = {}
    union = Union()
    for points in places.values():
        for page, at in points:
            pages.setdefault(page, SimpleNamespace(nodes=set())).nodes.add(at)
    for page, at in bare:
        pages[page].nodes.discard(at)
    for a, b in joined:
        union.join(a, b)
    net = Netlist(pages, union, places, {}, {}, {}, home={port: frozenset({points[0][0]}) for port, points in places.items()})
    net.live.update(union.find((p, at)) for p, part in pages.items() for at in part.nodes)
    return net


P1, P2 = (Id[Page](kind="page", value=v) for v in ("p1", "p2"))


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_port_drawn_on_two_pages_counts_where_it_is_wired():
    """R717: a copy is a second point of its port; the group is drawn when a piece holds every member."""
    places = {"s": ((P2, (2, 2)),), "t": ((P1, (5, 5)), (P2, (1, 1)))}
    assert _verdict(_homed(places, [((P2, (1, 1)), (P2, (2, 2)))]), ["s", "t"], {"t": {"s"}}) is None
    assert _verdict(_homed(places), ["s", "t"], {}) is not None


@pytest.mark.rule("G01-CONNECTED")
def test_a_wired_copy_does_not_cover_an_unwired_home_port():
    net = _homed({"s": ((P2, (4, 4)),), "t": ((P1, (1, 1)), (P2, (3, 3)))}, [((P2, (3, 3)), (P2, (4, 4)))], [(P1, (1, 1))])
    assert _verdict(net, ["s", "t"], {"s": {"t"}}) is not None


@pytest.mark.rule("G01-CONNECTED")
def test_a_complete_piece_on_a_copy_page_is_not_whole():
    places = {"s": ((P1, (1, 1)), (P2, (3, 3))), "t": ((P1, (2, 2)), (P2, (4, 4)))}
    assert _verdict(_homed(places, [((P2, (3, 3)), (P2, (4, 4)))]), ["s", "t"], {}) is not None


@pytest.mark.rule("G01-CONNECTED")
def test_a_group_with_every_member_drawn_nowhere_is_flagged():
    assert _verdict(_homed({}), ["s", "t"], {}) is not None


@pytest.mark.rule("G01-CONNECTED")
def test_a_member_drawn_in_another_document_counts_as_drawn():
    """R815: a conductor into another document stays a stub, so a group with a member drawn there is not drawn nowhere."""
    net = _homed({"s": ((P2, (1, 1)),)})
    net.home["s"] = frozenset()
    assert _verdict(net, ["s", "t"], {}) is None
    assert _verdict(_homed({}), ["s", "t"], {}) is not None


@pytest.mark.rule("DRAWN-NETLIST")
def test_pieces_chained_by_reference_pairs_are_one_piece():
    """R685: a group's two ends in pieces 1 and 3 are drawn when pairs 1-2 and 2-3 (the middle port is another group's) chain them."""
    p3 = Id[Page](kind="page", value="p3")
    net = _homed({"a": ((P1, (1, 1)),), "b": ((P2, (2, 2)),), "c": ((p3, (3, 3)),)})
    chained = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
    assert _verdict(net, ["a", "c"], chained) is None  # fails without _pairs: no stub names a member outside its piece
    assert _verdict(net, ["a", "c"], {"a": {"b"}, "b": {"a"}}) is not None  # no pair between pieces 2 and 3


@pytest.mark.rule("G01-CONNECTED")
def test_a_stub_counts_on_its_ports_home_page_only():
    """R815: counts are keyed on (page, port): a stub drawn on a copy page is no end of the home."""
    net = _homed({"t": ((P1, (1, 1)), (P2, (2, 2)))})
    far = SimpleNamespace(value="s")

    def stub(page):
        record = SimpleNamespace(
            star=StarKind.OFF, pairs=(SimpleNamespace(port=SimpleNamespace(value="t"), far=far),), port=SimpleNamespace(value="t"), page=page
        )
        return replace(net, records={"k": record}, markers={"k": (page, (1, 1))})

    assert _stubs(stub(P1)) == {"t": {"s"}}
    assert _stubs(stub(P2)) == {}


def test_a_bundle_stub_ends_each_listed_lane_that_is_drawn_joined_to_it():
    """BUNDLE (R1319, R1334): a stub's listed pair ends its port only when that port's ink is in the stub's piece."""
    places = {"t": ((P1, (1, 1)),), "u": ((P1, (2, 2)),), "w": ((P1, (3, 3)),), "v": ((P1, (4, 4)),)}
    net = _homed(places, [((P1, (1, 1)), (P1, (2, 2)))], [(P1, (3, 3))])
    pair = lambda port, far: SimpleNamespace(port=SimpleNamespace(value=port), far=SimpleNamespace(value=far))  # noqa: E731 - a one-line namespace
    record = SimpleNamespace(
        star=StarKind.OFF, pairs=(pair("t", "s"), pair("u", "r"), pair("w", "q"), pair("v", "p")), port=SimpleNamespace(value="t"), page=P1
    )
    found = _stubs(replace(net, records={"k": record}, markers={"k": (P1, (1, 1))}))
    # `w` has no ink, `v` has ink on the page but not joined to the stub: the plan names them, the drawing does not carry them
    assert found == {"t": {"s"}, "u": {"r"}}


@pytest.mark.rule("G01-CONNECTED")
@pytest.mark.parametrize("on_port", [True, False], ids=["on-its-port", "one-grid-off"])
def test_a_marker_on_a_port_is_a_drawn_node_with_no_wire_to_it(monkeypatch: pytest.MonkeyPatch, *, on_port: bool):
    """R916 W1, R1029: the wire stands on the near pin; a marker standing on the far pin is a node, one grid off the pin is none."""
    near, far = Id[Any](kind="port", value="near"), Id[Any](kind="port", value="far")
    terminal = SimpleNamespace(id="t", key="terminal", x=0, y=16, ports=(), net=None)
    marker = SimpleNamespace(id="m", key="marker-arrow-turned", x=0, y=32 if on_port else 40, ports=("p",), net="n")
    drawing = SimpleNamespace(symbols=(terminal, marker), wires=(SimpleNamespace(points=((0, 0), (0, 16))),))
    monkeypatch.setattr(drawn_netlist_module, "port_points", lambda s, _lib: [((0, 16), "1"), ((0, 32), "2")] if s is terminal else [])
    part = drawn_netlist_module._part(cast("Any", drawing), {"t": {"1": near, "2": far}}, LIBRARY)
    assert ((marker.x, marker.y) in part.nodes) is on_port


def _coincident(monkeypatch: pytest.MonkeyPatch, nets: dict[str, str]) -> Netlist:
    """One page with two symbols whose pins `a` and `b` stand at one point and carry no wire; `nets` names each port's net."""
    ids = {p: Id[Any](kind="port", value=p) for p in nets}
    syms = [SimpleNamespace(id=name, key="box", x=0, y=0, ports=(), net=None) for name in ("s1", "s2")]
    drawing = SimpleNamespace(symbols=tuple(syms), wires=())
    monkeypatch.setattr(drawn_netlist_module, "port_points", lambda _s, _lib: [((7, 7), "p")])
    part = drawn_netlist_module._part(cast("Any", drawing), {"s1": {"p": ids["a"]}, "s2": {"p": ids["b"]}}, LIBRARY)
    page = Id[Page](kind="page", value="p")
    net = Netlist({page: part}, Union(), drawn_netlist_module._placed({page: part}), ids, {}, {}, nets=nets)
    net.live.update(net.union.find((page, at)) for at in part.nodes)
    return net


@pytest.mark.rule("DRAWN-NETLIST")
def test_pins_at_one_point_are_one_node_and_a_short_when_their_nets_differ(monkeypatch: pytest.MonkeyPatch):
    """R922: two pins that coincide join with no wire between them; the same net is no finding, two nets are a short."""
    same = _coincident(monkeypatch, {"a": "n", "b": "n"})
    assert (7, 7) in next(iter(same.pages.values())).nodes
    assert short_findings(same) == ()
    apart = _coincident(monkeypatch, {"a": "n", "b": "m"})
    assert [f.code for f in short_findings(apart)] == ["DRAWING_SHORTS_NETS"]


@pytest.mark.rule("G01-CONNECTED")
@pytest.mark.parametrize("bridge", [True, False], ids=["bridge", "plain-conductor"])
def test_a_declared_bridge_joins_its_two_terminals_with_no_ink(monkeypatch: pytest.MonkeyPatch, *, bridge: bool):
    """R1009: two terminals one pitch apart, each a node of its own piece; only a bridge conductor joins them."""
    a, b = Id[Any](kind="port", value="a"), Id[Any](kind="port", value="b")
    net = _homed({"a": ((P1, (0, 0)),), "b": ((P1, (8, 0)),)})
    monkeypatch.setattr(drawn_netlist_module, "build_indexes", lambda _m: SimpleNamespace(conductors_by_port={a: ("c",), b: ("c",)}))
    monkeypatch.setattr(drawn_netlist_module, "conductor_ends", lambda _m, _c: (a, b))
    monkeypatch.setattr(drawn_netlist_module, "is_bridge", lambda _m, _c: bridge)
    monkeypatch.setattr(drawn_netlist_module, "mate_ports", lambda _m: ())
    drawn_netlist_module._link(net, cast("Any", None), ())
    assert (_verdict(net, ["a", "b"], {}) is None) is bridge


@pytest.mark.rule("G01-CONNECTED")
@pytest.mark.parametrize(
    ("bridge", "drawn", "page"),
    [(True, True, P1), (True, False, P1), (False, True, P1), (True, True, P2), (True, False, P2)],
    ids=["drawn", "undrawn-partner", "plain-conductor", "other-page", "other-page-undrawn"],
)
def test_linked_bridge_partners_join_when_neither_stands_on_a_node(monkeypatch: pytest.MonkeyPatch, *, bridge: bool, drawn: bool, page: Any):
    """R1063, R1064: a partner with no ink of its own is drawn through its linked port; a bridge joins two drawn partners on any pages."""
    a, b = Id[Any](kind="port", value="a"), Id[Any](kind="port", value="b")
    places = {"a": ((P1, (0, 0)),), "b": ((page, (8, 0)),), "ha": ((P1, (0, 8)),), "hb": ((page, (8, 8)),)}
    net = _homed(places, bare=[(P1, (0, 0)), (page, (8, 0))])
    net.linked.update({"a": "ha", "b": "hb"} if drawn else {})
    monkeypatch.setattr(drawn_netlist_module, "build_indexes", lambda _m: SimpleNamespace(conductors_by_port={a: ("c",), b: ("c",)}))
    monkeypatch.setattr(drawn_netlist_module, "conductor_ends", lambda _m, _c: (a, b))
    monkeypatch.setattr(drawn_netlist_module, "is_bridge", lambda _m, _c: bridge)
    monkeypatch.setattr(drawn_netlist_module, "mate_ports", lambda _m: ())
    drawn_netlist_module._link(net, cast("Any", None), ())
    assert (net.union.find((P1, (0, 8))) == net.union.find((page, (8, 8)))) is (bridge and drawn)
    assert net.union.find((P1, (0, 0))) != net.union.find((page, (8, 0)))


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_copy_pair_joins_through_its_where_text_and_not_without_it():
    """R1396: s is wired on P1 to a copy of t, t on P2 to a copy of s; the pieces are one only when both draw a where-text."""
    places = {"s": ((P1, (1, 1)), (P2, (3, 3))), "t": ((P2, (4, 4)), (P1, (2, 2)))}
    joined = [((P1, (1, 1)), (P1, (2, 2))), ((P2, (3, 3)), (P2, (4, 4)))]
    net = _homed(places, joined)
    assert _verdict(net, ["s", "t"], {}) is not None
    net.texted.update({"s", "t"})
    assert _verdict(net, ["s", "t"], {}) is None


@pytest.mark.rule("BUNDLE-ARROW")
def test_ends_at_prefers_the_trunk_lane_to_a_same_net_drop_on_the_column():
    """R1664: a pole drop of the net 128 below on the arrow's column is not the end; the trunk lane's end is."""
    drop = DrawnWire("drop", ((240, 228), (240, 300)), "wire", net="n")
    lane = DrawnWire("lane", ((200, 100), (240, 100)), "trunk", net="n")
    part = cast("Any", SimpleNamespace(drawing=SimpleNamespace(wires=(drop, lane))))
    assert drawn_netlist_module._ends_at(part, (240, 100), 10) == {"n": (240, 100)}


def _page(wires: tuple[DrawnWire, ...], ports: dict[str, tuple[int, int]], anchors: set[tuple[int, int]]) -> Any:
    edges = {frozenset(w.points): {i} for i, w in enumerate(wires)}
    return SimpleNamespace(
        drawing=SimpleNamespace(wires=wires, symbols=()),
        ports=ports,
        graph=SimpleNamespace(edges=edges, tees=()),
        anchors={*ports.values(), *anchors},
    )


def _lanes_under_arrow(short: int, listed: tuple[str, ...], far: str | None = None) -> list[str]:
    """The DANGLING_WIRE_END messages of two trunk lanes under one arrow: the lead ends on it, the other `short` G before it.

    `far` None: an off stub whose pairs list `listed`. Else a pair marker whose partner on P2 ends a lane chain of net `far`.
    """
    lead = DrawnWire("lead", ((200, 100), (240, 100)), "trunk", net="a")
    lane = DrawnWire("lane", ((200, 108), (240 - short, 108)), "trunk", net="b")
    ports = {"pa": (200, 100), "pb": (200, 108)}
    union = Union()
    union.join((P1, (200, 108)), (P1, (240 - short, 108)))
    pair = lambda port: SimpleNamespace(port=SimpleNamespace(value=port))  # noqa: E731 - a one-line namespace
    pages = {P1: _page((lead, lane), ports, {(240, 100)})}
    markers: dict[str, Any] = {"k": (P1, (240, 100))}
    star, partner = StarKind.OFF, None
    if far is not None:
        pages[P2] = _page(
            (DrawnWire("far", ((300, 100), (340, 100)), "trunk", net="a"), DrawnWire("far2", ((300, 108), (340, 108)), "trunk", net=far)),
            {},
            {(x, y) for x in (300, 340) for y in (100, 108)},
        )
        markers["j"], star, partner = (P2, (340, 100)), StarKind.BRANCH, SimpleNamespace(value="j")
    record = SimpleNamespace(pairs=tuple(map(pair, listed)), star=star, partner=partner)
    net = Netlist(cast("Any", pages), union, {}, {}, markers, {"k": cast("Any", record)}, pitch=8)
    return [f.message for f in dangling_findings(net)]


@pytest.mark.rule("BUNDLE-ARROW")
@pytest.mark.parametrize(
    ("short", "listed", "left"),
    [(8, ("pa", "pb"), []), (16, ("pa", "pb"), ["wire end at 224, 108"]), (8, ("pa",), ["wire end at 232, 108"])],
    ids=["one-pitch-short-is-met", "two-pitches-short-dangles", "port-not-listed-dangles"],
)
def test_a_lane_one_pitch_short_under_an_off_stub_is_met(short: int, listed: tuple[str, ...], left: list[str]):
    """R1666 (R1352): a trunk lane end within one pitch of the lead lane's end on the stub, whose pairs list the lane's port, is met."""
    assert _lanes_under_arrow(short, listed) == left


@pytest.mark.rule("BUNDLE-ARROW")
@pytest.mark.parametrize(
    ("far", "left"), [("b", []), ("c", ["wire end at 232, 108"])], ids=["partner-chain-carries-the-net", "partner-chain-carries-another-net"]
)
def test_a_lane_one_pitch_short_under_a_pair_marker_is_met_by_the_partner_chain(far: str, left: list[str]):
    """R1667: a pair marker's lane is met when its net also runs in the partner marker's lane chain on the partner's page."""
    assert _lanes_under_arrow(8, (), far) == left


_Stands = dict[str, tuple[str, str | None, str | None, str]]


def _powered(
    monkeypatch: pytest.MonkeyPatch,
    stands: _Stands,
    *,
    lead: bool = True,
    ends: tuple[tuple[Id[Any], Id[Any]], ...] | None = None,
    nets: dict[str, str] | None = None,
) -> Netlist:
    """One page per port of `stands` (port: symbol kind, printed text, cabinet, page): a pin at (0, 16), a power symbol at (0, 0), a lead or not."""
    ids = {p: Id[Any](kind="port", value=p) for p in stands}
    pages: dict[Any, Any] = {}
    at: dict[str, Any] = {}
    monkeypatch.setattr(drawn_netlist_module, "port_points", lambda s, _lib: at[s.id])
    for port, (kind, _, _, page) in stands.items():
        device = SimpleNamespace(id=f"d-{port}", key="box", x=0, y=16, ports=(), net=None)
        bar = SimpleNamespace(id=f"p-{port}", key=power_symbol_key(kind), x=0, y=0, ports=(port,), net=None)
        wires = (SimpleNamespace(points=((0, 16), (0, 0))),) if lead else ()
        at[bar.id], at[device.id] = [((0, 0), "1")], [((0, 16), "p")]
        pages[Id[Page](kind="page", value=page)] = drawn_netlist_module._part(
            cast("Any", SimpleNamespace(symbols=(device, bar), wires=wires)), {device.id: {"p": ids[port]}}, LIBRARY
        )
    monkeypatch.setattr(drawn_power, "port_power_text", lambda _m, port: stands[port.value][1])
    monkeypatch.setattr(drawn_power, "_scope", lambda _m, port: stands[port.value][2])
    monkeypatch.setattr(drawn_power, "_identity", lambda _m, _port, _key, text: text)
    monkeypatch.setattr(drawn_power, "required_groups", lambda _m: tuple(ends or ()))
    monkeypatch.setattr(drawn_power, "rail_flagged", lambda _m, _joined: True)
    monkeypatch.setattr(drawn_rails, "unit_label", lambda _m, unit: str(unit))
    parts = {Id[Page](kind="page", value=v[3]): pages[Id[Page](kind="page", value=v[3])] for v in stands.values()}
    return Netlist(parts, drawn_netlist_module._join(parts), drawn_netlist_module._placed(parts), ids, {}, {}, nets=nets or {})


def _same_piece(net: Netlist, one: str, other: str) -> bool:
    first, second = (next(iter(net.placed[p])) for p in (one, other))
    return net.union.find(first) == net.union.find(second)


@pytest.mark.rule("READ-RAILS")
@pytest.mark.parametrize(
    ("other", "joined"),
    [
        (("supply", "24V", "A", "p2"), True),
        (("supply", "12V", "A", "p2"), False),
        (("supply", "24V", "B", "p2"), False),
        (("ground", "24V", "A", "p2"), False),
        (("supply", "24V", None, "p2"), False),
    ],
    ids=["same-text-and-cabinet", "other-text", "other-cabinet", "other-symbol", "no-cabinet"],
)
def test_two_power_symbols_join_iff_they_print_one_potential_in_one_cabinet(
    monkeypatch: pytest.MonkeyPatch, other: tuple[str, str, str, str], *, joined: bool
):
    """R3 first half: the join key is (cabinet, symbol, printed text), never the model's hidden net."""
    net = _powered(monkeypatch, {"a": ("supply", "24V", "A", "p1"), "b": other})
    join_power(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    assert _same_piece(net, "a", "b") is joined


@pytest.mark.rule("READ-RAILS")
def test_a_model_conductor_between_two_inked_power_symbols_joins_them_across_cabinets(monkeypatch: pytest.MonkeyPatch):
    """R1937 Q2: a conductor ending on two inked power symbols is the cross-cabinet join (interim, KI-770)."""
    stands: _Stands = {"a": ("ground", None, "A", "p1"), "b": ("ground", None, None, "p2")}
    ends = ((Id[Any](kind="port", value="a"), Id[Any](kind="port", value="b")),)
    net = _powered(monkeypatch, stands, ends=ends)
    join_power(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    assert _same_piece(net, "a", "b")


@pytest.mark.rule("READ-RAILS")
@pytest.mark.parametrize("kind", ["pe", "ground"])
@pytest.mark.parametrize(
    ("nets", "shared"), [({"a": "PE:A", "b": "PE:A", "c": "PE:A"}, False), ({"a": "n1", "b": "n2", "c": "n1"}, True)], ids=["bonded", "unbonded"]
)
def test_unbonded_nets_printing_one_identity_in_a_flagged_cabinet_are_rail_identity_shared(
    monkeypatch: pytest.MonkeyPatch, kind: str, nets: dict[str, str], *, shared: bool
):
    """R3 second half: three symbols of one flagged cabinet pass when their nets are one bonded class, and fail when two nets are not."""
    stands: _Stands = {p: (kind, None, "A", f"p{p}") for p in "abc"}
    net = _powered(monkeypatch, stands, nets=nets)
    found = rail_findings(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    if shared:
        expect_codes(SimpleNamespace(findings=found), "RAIL_IDENTITY_SHARED")
    else:
        assert found == ()


@pytest.mark.rule("READ-RAILS")
@pytest.mark.parametrize(
    ("kind", "nets", "shared"),
    [("ground", {"a": "n1", "b": "n2"}, True), ("pe", {"a": "n1", "b": "n2"}, True), ("ground", {"a": "n1", "b": "n1"}, False)],
)
def test_with_no_flagged_rail_two_unbonded_nets_of_one_cabinet_share_an_identity_and_one_net_does_not(
    monkeypatch: pytest.MonkeyPatch, kind: str, nets: dict[str, str], *, shared: bool
):
    """R1955: a missing flag alone raises nothing; two nets under the cabinet plus potential raise, naming both remedies."""
    net = _powered(monkeypatch, {"a": (kind, None, "A", "p1"), "b": (kind, None, "A", "p2")}, nets=nets)
    monkeypatch.setattr(drawn_power, "rail_flagged", lambda _m, _joined: False)
    found = rail_findings(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    if shared:
        expect_codes(SimpleNamespace(findings=found), "RAIL_IDENTITY_SHARED")
        assert "put a fuse or breaker between them" in found[0].message
    else:
        assert found == ()
    join_power(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    assert not _same_piece(net, "a", "b")


@pytest.mark.rule("READ-POWER-INK")
@pytest.mark.parametrize("lead", [True, False], ids=["lead", "no-ink"])
def test_a_power_symbol_with_no_ink_to_its_pin_is_power_symbol_not_joined(monkeypatch: pytest.MonkeyPatch, *, lead: bool):
    """R4: a power symbol is joined to its pin by a lead; one off its pin with no wire is an ERROR."""
    net = _powered(monkeypatch, {"a": ("ground", None, "A", "p1")}, lead=lead)
    found = power_findings(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    if lead:
        assert found == ()
    else:
        expect_codes(SimpleNamespace(findings=found), "POWER_SYMBOL_NOT_JOINED")
        assert "report it" in found[0].message


@pytest.mark.rule("READ-POWER-INK")
def test_a_power_symbol_standing_on_its_pin_is_inked_with_no_wire(monkeypatch: pytest.MonkeyPatch):
    """R4: a zero-length lead (the symbol's port point is the pin point) counts as ink."""
    net = _powered(monkeypatch, {"a": ("ground", None, "A", "p1")}, lead=False)
    part = next(iter(net.pages.values()))
    zero = replace(part, powers={"a": part.ports["a"]})
    assert power_findings(replace(net, pages={next(iter(net.pages)): zero}), None) == ()  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model


def _marked(built: Built) -> tuple[Any, Any, list[int]]:
    """A page, the first placed symbol that prints two marking texts, and nothing else."""
    for page, drawing in built.drawings.items():
        for symbol in drawing.symbols:
            marks = [i for i, (slot, text) in enumerate(symbol.slots) if slot.startswith("marking.") and text]
            if len(marks) > 1:
                return page, symbol, marks
    missing = "no symbol with two markings"
    raise AssertionError(missing)


@pytest.mark.rule("READ-IDENTITY")
def test_a_drawing_printing_every_pin_marking_as_the_model_gives_it_has_no_pin_marking_wrong(card16):
    assert "PIN_MARKING_WRONG" not in card16.codes()
    assert card16.netlist().marks


@pytest.mark.rule("READ-IDENTITY")
def test_two_pins_with_their_marking_texts_swapped_are_pin_marking_wrong(card16):
    page, symbol, (a, b) = _marked(card16)
    slots = list(symbol.slots)
    (sa, ta), (sb, tb) = slots[a], slots[b]
    slots[a], slots[b] = (sa, tb), (sb, ta)
    swapped = replace(symbol, slots=tuple(slots))
    drawing = card16.drawings[page]
    patched = card16.patched(page, symbols=tuple(swapped if s.id == symbol.id else s for s in drawing.symbols))
    found = drawing_sweep(card16.model, card16._net(patched))
    expect_codes(SimpleNamespace(findings=found), "PIN_MARKING_WRONG")
    assert sum(f.code == "PIN_MARKING_WRONG" for f in found) == 2


@pytest.mark.rule("READ-IDENTITY")
def test_a_pin_the_sheets_leave_off_is_not_read_for_its_marking(card16, monkeypatch):
    monkeypatch.setattr(drawn_identity_marks, "hidden_pins", lambda _model: set(card16.netlist().ids.values()))
    page, symbol, (a, _) = _marked(card16)
    gone = replace(symbol, slots=tuple(s for i, s in enumerate(symbol.slots) if i != a))
    drawing = card16.drawings[page]
    patched = card16.patched(page, symbols=tuple(gone if s.id == symbol.id else s for s in drawing.symbols))
    assert card16.count("PIN_MARKING_WRONG", patched) == 0


H, V = [(-20, 0), (20, 0)], [(0, -20), (0, 20)]
FOUR = [[(-20, 0), (0, 0)], [(0, 0), (20, 0)], [(0, 0), (0, 20)], [(0, 0), (0, -20)]]


def _rule(rule: str, code: str, geometry: Any) -> Any:
    return pytest.param(code, geometry, marks=pytest.mark.rule(rule), id=code)


INK_CASES = [
    _rule("READ-T-DOT", "MISSING_JUNCTION_DOT", (FOUR, set(), [])),
    _rule("READ-DOT-CROSSING", "DOT_ON_CROSSING", ([H, V], {(0, 0)}, [])),
    _rule("READ-WIRE-OVER-TIP", "WIRE_OVER_PIN_TIP", ([H], set(), [(0, 0)])),
]
INK_CLEAN = [
    pytest.param((FOUR, {(0, 0)}, []), marks=pytest.mark.rule("READ-T-DOT"), id="four-way-with-dot"),
    pytest.param(([H, V], set(), []), marks=pytest.mark.rule("READ-DOT-CROSSING"), id="crossing-no-dot"),
    pytest.param(([[(-20, 0), (0, 0)]], set(), [(0, 0)]), marks=pytest.mark.rule("READ-WIRE-OVER-TIP"), id="wire-ends-at-tip"),
]


def _ink(wires: list[list[tuple[int, int]]], dots: set[tuple[int, int]], tips: list[tuple[int, int]]) -> tuple[Any, ...]:
    page = Id[Page](kind="page", value="p")
    return ink_findings(cast("Any", SimpleNamespace(pages={page: SimpleNamespace(graph=page_graph(wires, dots, tips))})))


@pytest.mark.parametrize(("code", "geometry"), INK_CASES)
def test_ink_the_page_graph_lists_is_an_error_of_its_code(code: str, geometry: Any):
    """R5, R6, R7: a four-way with no dot, a dot on a crossing and a wire over a pin tip each give one finding."""
    expect_codes(SimpleNamespace(findings=_ink(*geometry)), code)
    assert len(_ink(*geometry)) == 1


@pytest.mark.parametrize("geometry", INK_CLEAN)
def test_ink_that_is_drawn_right_gives_no_finding(geometry: Any):
    assert _ink(*geometry) == ()


@pytest.mark.rule("READ-T-DOT")
def test_a_dotless_three_way_is_reported_once_by_the_sweep_side_of_tees_only():
    """R6: a dotless T is a tee, which short_findings reports; ink_findings leaves it to avoid a second finding."""
    assert _ink([H, [(0, 0), (0, 20)]], set(), []) == ()


def _ports_of(model, port):
    """The ports of the physical net `port` stands on."""
    physical = net_of(model, port)
    assert physical is not None
    return physical.ports


def _pe_model():
    """A pump cabinet with a flagged PE strip: M1 earthed by `d.earth`, M2 by a conductor to the strip, so two PE nets meet only there."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        pe = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", 2, bridged=True, rail=True)
        m1, m2 = d.device("M1", "DEMO-MOTOR-4KW"), d.device("M2", "DEMO-MOTOR-4KW")
    d.earth(pe[1].inner, m1.motor["PE"])
    d.series(pe[2].outer, m2.motor["PE"], wire=(GNYE, 2.5))
    return fr.build(d, unit_document(cab)).model


@pytest.mark.rule("READ-RAILS")
def test_two_pe_nets_a_conductor_reaches_from_a_flagged_strip_are_one_net_and_no_short(monkeypatch: pytest.MonkeyPatch):
    """R1937: a real model, no patched net keys: the PE bond merges the nets, so the drawn PE symbols do not short."""
    model = _pe_model()
    ids = {p.value: p for p in ports(model)}
    pe = [key for key, one in ids.items() if port_power_kind(model, one) is PowerKind.PE]
    assert len({net_key(model, _ports_of(model, ids[k])) for k in pe}) == 2
    assert len({drawn_power.port_nets(model, ids)[k] for k in pe}) == 1
    built = _built_of(model, symbol_kit(model, LIBRARY), monkeypatch)
    assert "DRAWING_SHORTS_NETS" not in built.codes()


class _Io(NamedTuple):
    X1: fr.TerminalStrip
    X2: fr.TerminalStrip


def _earthed_cabinets(cabinets: int):
    """`cabinets` units, each with two strips earthed by their own function's `b.earth` and no flagged rail."""
    d = fr.design("demo_parts")
    names = [f"cab-{n}" for n in range(1, cabinets + 1)]
    for n, name in enumerate(names, 1):

        def body(b: fr.Design, n: int = n) -> _Io:
            strips = []
            for k in (1, 2):
                with b.function(f"G{n}{k}", "Group"):
                    strips.append(b.terminal_strip(f"X{n}{k}", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5"))
                    b.earth(strips[-1].run("PE", 1)[1])
            return _Io(*strips)

        unit = fr.unit(name, revision=1, interface_version=1, date="2026-10-15", text="First issue", by="XX", title=name, number=f"C-{n}")
        d.add(unit(body), f"U{n}")
    return fr.build(d, *(unit_document(name) for name in names)).model


@pytest.mark.rule("READ-RAILS")
@pytest.mark.parametrize("cabinets", [1, 2])
def test_earth_declared_pe_is_one_bond_class_per_cabinet_with_no_flag(monkeypatch: pytest.MonkeyPatch, cabinets: int):
    """R1962: each cabinet's earth-declared PE nets are one class, two cabinets two; no RAIL_IDENTITY_SHARED."""
    model = _earthed_cabinets(cabinets)
    ids = {p.value: p for p in ports(model)}
    pe = [key for key, one in ids.items() if port_power_kind(model, one) is PowerKind.PE]
    assert len({net_key(model, _ports_of(model, ids[k])) for k in pe}) == 2 * cabinets
    assert len({drawn_power.port_nets(model, ids)[k] for k in pe}) == cabinets
    built = _built_of(model, symbol_kit(model, LIBRARY), monkeypatch)
    assert "RAIL_IDENTITY_SHARED" not in built.codes()
