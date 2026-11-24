"""The drawn netlist is checked against the model (DRAWN-NETLIST, el-0052).

A clean build raises none of the sweep's codes. Each class is planted as a small patch to a
finished drawing: join two nets, move a wire end to a neighbour port, drop a junction dot, unpair a
"""

import importlib
import os
from dataclasses import dataclass, replace
from functools import cache
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, NamedTuple, cast

import fransys as fr
import pytest
import test_two_mated_plugs_wired_to_one_device_draw_every_end as mated
from _card_case import card_case_drafts
from _expected_codes import expect_codes
from _model_build_cover import unit_document
from conventions_fixtures import house
from fransys.colours import BK, BU, GNYE
from fransys_el import build, drawn_power, drawn_printed, drawn_rails, drawn_references, lay_out_core, lay_out_drawn, symbol_kit
from fransys_el import draw_power as draw_power_module
from fransys_el import drawn_ends as drawn_ends_module
from fransys_el import drawn_identity as drawn_identity_module
from fransys_el import drawn_netlist as drawn_netlist_module
from fransys_el import drawn_nets as drawn_nets_module
from fransys_el import read_markers as read_markers_module
from fransys_el.drawn_ends import ink_without_conductor
from fransys_el.drawn_finding import drawn_finding
from fransys_el.drawn_identity import net_text
from fransys_el.drawn_lanes import Lanes
from fransys_el.drawn_netlist import Netlist, drawn_netlist, is_marker, with_lines
from fransys_el.drawn_nets import _carried, _lined, _pairs, _stubs, _unmarked, not_drawn_findings
from fransys_el.drawn_pairs import dangling_findings
from fransys_el.drawn_power import join_power, power_findings
from fransys_el.drawn_rails import rail_findings
from fransys_el.drawn_shorts import ink_findings, short_findings
from fransys_el.drawn_sweep import drawing_sweep
from fransys_el.kit_keys import function_of
from fransys_el.placement_ids import net_key
from fransys_el.placement_joins import node_joins
from fransys_el.placement_kit import Pick
from ring_cases import bank_model, box_kit
from test_a_clean_relay_loop_builds_with_every_net_and_function_drawn import _built as relay_loop_built

from electrical_symbols import LIBRARY, MARKER_SLOT, marking_slot, power_symbol_key
from fransys_layout.core import Box, page_graph
from fransys_layout.core.outputs import Refused
from fransys_layout.core.route_env import lost_key
from fransys_layout.drawing import DrawnSymbol, DrawnText, DrawnWire
from fransys_layout.symbols import frame_cell
from fransys_model.derive import (
    PowerKind,
    drawn_net_of,
    drawn_physical_nets,
    far_pins,
    link_groups,
    net_of,
    port_power_kind,
    reference_targets,
    required_groups,
    terminal_items,
)
from fransys_model.kernel import Id, UnionFind, make_id
from fransys_model.layout import LinkMarker, MarkerPair, MarkerSide, Page, Side, StarKind, layout_of, sheet_format_of
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from fransys_layout.drawing import Drawing
    from fransys_model.vocab import Port

loop_stage = importlib.import_module("fransys_layout.core.route_loop")

CODES = {
    "CONNECTION_NOT_DRAWN",
    "DRAWING_SHORTS_NETS",
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
    alone: frozenset[Any] = frozenset()
    titles: Any = None

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
        net = with_lines(drawn_netlist(self.model, self.kit, drawings, self.markers, LIBRARY), self.model, self.kit, self.lines)
        net.alone.update(self.alone)
        net.titles.update(self.titles or {})
        return net

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
    nets: list[Any] = []
    original, lines_of = lay_out_core.drawn_netlist, lay_out_core.with_lines

    def spy(*args):
        caught.append(args)
        return original(*args)

    def spy_lines(net, laid, kit, lines):
        caught.append(lines)
        nets.append(net)
        return lines_of(net, laid, kit, lines)

    monkeypatch.setattr(lay_out_core, "drawn_netlist", spy)
    monkeypatch.setattr(lay_out_core, "with_lines", spy_lines)
    lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    (laid, _, drawings, markers, _), lines = caught
    return Built(laid, kit, dict(drawings), markers, lines, frozenset(nets[0].alone), dict(nets[0].titles))


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
    assert bank40.codes() & {"CONNECTION_DRAWN_TWICE"} == set()


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
    # S2b: a stub at the far end naming the near end is no mark of the near end (the either-end clause is gone)
    far_only = replace(cut, **dict(zip(("records", "markers"), _off_stub(cut, far, near, cut.placed[near][0]), strict=True)))
    owed = [(near, far) in _unmarked(bank8.model, n, s := _stubs(n), _pairs(n, s)) for n in (net, cut, right, wrong, far_only)]
    assert owed == [False, True, False, True, True]


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


def _overlap(bank8, *, dot: bool):
    """The build with a wire laid collinear over part of a wire between ports (and a junction dot on the run if `dot`), and its two ends."""
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (x1, y1), (x2, y2) = wire.points[-2:]
    a, b = (x1 + (x2 - x1) // 4, y1 + (y2 - y1) // 4), (x1 + (x2 - x1) * 3 // 4, y1 + (y2 - y1) * 3 // 4)
    drawing = bank8.drawings[page]
    symbols = drawing.symbols
    if dot:
        x, y = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
        symbols = (*symbols, DrawnSymbol("planted-dot", "junction-dot", x, y, "R0", outline=Box(x - 1, y - 1, 2, 2)))
    return bank8.patched(page, wires=(*drawing.wires, DrawnWire(wire.net, (a, b), wire.style)), symbols=symbols), a, b


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_lying_along_another_wire_is_not_met_by_it(bank8):
    """KI-365: a wire laid collinear over part of another wire ends on nothing; only a wire end on its interior across, or a dot, meets."""
    planted, a, b = _overlap(bank8, dot=False)
    assert sorted(bank8.messages("DANGLING_WIRE_END", planted)) == sorted(f"wire end at {x}, {y}" for x, y in (a, b))


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_lying_along_another_wire_needs_a_dot_at_the_end_itself(bank8):
    """R1861 (CORRECTNESS-PROOF S0 R6, T needs a dot): a dot further along the shared run does not meet the start of the overlap."""
    planted, a, b = _overlap(bank8, dot=True)
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
def test_a_marker_whose_partner_is_not_drawn_is_unreadable(bank40):
    net = bank40.netlist()
    for page, part in net.pages.items():
        marks = [s for s in part.drawing.symbols if is_marker(s) and (r := net.records.get(s.id.rpartition(":")[2])) and r.star is not StarKind.OFF]
        if marks:
            kept = tuple(s for s in part.drawing.symbols if s is not marks[0])
            assert bank40.count("REFERENCE_NOT_READABLE", bank40.patched(page, symbols=kept)) > bank40.count("REFERENCE_NOT_READABLE")
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
    pages: dict[Any, Any] = {p1: SimpleNamespace(nodes={(0, 0), (1, 1)}), p2: SimpleNamespace(nodes={(0, 0)})}
    net = Netlist(pages, UnionFind(), places, {}, {}, {}, lined={"a": "L", "b": "L", "c": "M"}, stub_lines={(p1, "L")}, home=home)
    assert _lined(net, "a")
    assert not _lined(net, "b")
    assert not _lined(net, "c")
    pages[p1].nodes.discard((0, 0))
    assert not _lined(net, "a")  # A2: the line's stub belongs to another port; a pin with no wire or stub of its own is not ended by it


def _homed(places: dict[Any, Any], joined: Sequence[Any] = (), bare: Sequence[Any] = ()) -> Netlist:
    """Ports `places` (first point of each is its home page, later ones copies) with every listed point a node; `joined` pairs are one piece."""
    pages: dict[Any, Any] = {}
    union = UnionFind()
    for points in places.values():
        for page, at in points:
            pages.setdefault(page, SimpleNamespace(nodes=set())).nodes.add(at)
    for page, at in bare:
        pages[page].nodes.discard(at)
    for a, b in joined:
        union.union(a, b)
    net = Netlist(pages, union, places, {}, {}, {}, home={port: frozenset({points[0][0]}) for port, points in places.items()})
    net.live.update(union.find((p, at)) for p, part in pages.items() for at in part.nodes)
    return net


P1, P2 = (Id[Page](kind="page", value=v) for v in ("p1", "p2"))


def _drawn(net: Netlist, near: str, far: str, stubs: dict[str, set[str]] | None = None) -> bool:
    """True when the end of `near` at `far` is carried: ink, a stub naming `far`, its line or its where-text (R1573)."""
    held = stubs or {}
    return _carried(net, held, _pairs(net, held), (near, far))


@pytest.mark.rule("DRAWN-NETLIST")
@pytest.mark.rule("G01-CONNECTED")
def test_a_group_is_drawn_where_a_piece_holds_every_member_at_its_home():
    """R717: a copy is a second point of its port; a wired copy covers no unwired home port and a complete piece on a copy page is not whole."""
    two = {"s": ((P2, (2, 2)),), "t": ((P1, (5, 5)), (P2, (1, 1)))}
    wired = {"s": ((P2, (4, 4)),), "t": ((P1, (1, 1)), (P2, (3, 3)))}
    copies = {"s": ((P1, (1, 1)), (P2, (3, 3))), "t": ((P1, (2, 2)), (P2, (4, 4)))}
    pair = [((P2, (3, 3)), (P2, (4, 4)))]
    assert _drawn(_homed(two, [((P2, (1, 1)), (P2, (2, 2)))]), "t", "s", {"t": {"s"}})
    assert not _drawn(_homed(two), "t", "s")
    assert not _drawn(_homed(wired, pair, [(P1, (1, 1))]), "t", "s", {"s": {"t"}})
    assert not _drawn(_homed(copies, pair), "s", "t")


@pytest.mark.rule("DRAWN-NETLIST")
def test_pieces_chained_by_reference_pairs_are_one_piece():
    """R685: a group's two ends in pieces 1 and 3 are drawn when pairs 1-2 and 2-3 (the middle port is another group's) chain them."""
    p3 = Id[Page](kind="page", value="p3")
    net = _homed({"a": ((P1, (1, 1)),), "b": ((P2, (2, 2)),), "c": ((p3, (3, 3)),)})
    chained = {"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}
    assert _drawn(net, "a", "c", chained)  # fails without _pairs: no stub names a member outside its piece
    assert not _drawn(net, "a", "c", {"a": {"b"}, "b": {"a"}})  # no pair between pieces 2 and 3


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


@pytest.mark.rule("DRAWN-NETLIST")
@pytest.mark.parametrize(
    ("foot_x", "far_names_back", "credited"),
    [(1, True, True), (1, False, False), (2, True, False)],
    ids=["foot-on-ink-and-named-back", "far-end-does-not-name-it", "foot-off-the-stub"],
)
def test_a_bundle_lane_on_a_read_foot_ends_when_the_far_marker_names_it_back(foot_x: int, *, far_names_back: bool, credited: bool):
    """R3541: the stub's lane `v` has no ink in its piece; its end is a read foot at the stub's x, and its far marker lists the pair back."""
    net = _homed({"t": ((P1, (1, 1)),), "v": ((P1, (1, 4)),), "p": ((P1, (9, 9)),)}, [((P1, (1, 4)), (P1, (foot_x, 5)))])
    pair = lambda port, far: SimpleNamespace(port=SimpleNamespace(value=port), far=SimpleNamespace(value=far))  # noqa: E731 - a one-line namespace
    stub = lambda port, *pairs: SimpleNamespace(star=StarKind.OFF, pairs=pairs, port=SimpleNamespace(value=port), page=P1)  # noqa: E731 - a one-line namespace
    records, markers = {"k": stub("t", pair("t", "s"), pair("v", "p"))}, {"k": (P1, (1, 1))}
    if far_names_back:
        records["j"], markers["j"] = stub("p", pair("p", "v")), (P1, (9, 9))
    found = _stubs(replace(net, records=records, markers=markers, lanes=Lanes(joined={(P1, (foot_x, 5))})))
    assert ("p" in found.get("v", set())) is credited  # fails without the foot rule: the lane has no ink in the stub's piece


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
    net = Netlist({page: part}, UnionFind(), drawn_netlist_module._placed({page: part}), ids, {}, {}, nets=nets)
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
@pytest.mark.parametrize(("pair", "page", "joined"), [(True, P1, True), (False, P1, False), (True, P2, False)], ids=["pair", "no-pair", "other-page"])
def test_a_join_pair_joins_its_two_ports_on_a_page_with_no_ink_between_them(*, pair: bool, page: Any, joined: bool):
    """R685, R2079 G2: two ports one pitch apart, each a node of its own piece; only a `Netlist.joins` pair joins them, on a page with both."""
    a, b = Id[Any](kind="port", value="a"), Id[Any](kind="port", value="b")
    net = replace(_homed({"a": ((P1, (0, 0)),), "b": ((page, (8, 0)),)}), joins=((a, b),) if pair else ())
    drawn_netlist_module._link(net)
    assert (net.union.find((P1, (0, 0))) == net.union.find((page, (8, 0)))) is joined


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_copy_pair_joins_through_its_where_text_and_not_without_it():
    """R1396: s is wired on P1 to a copy of t, t on P2 to a copy of s; the pieces are one only when both draw a where-text."""
    places = {"s": ((P1, (1, 1)), (P2, (3, 3))), "t": ((P2, (4, 4)), (P1, (2, 2)))}
    joined = [((P1, (1, 1)), (P1, (2, 2))), ((P2, (3, 3)), (P2, (4, 4)))]
    net = _homed(places, joined)
    assert not _drawn(net, "s", "t")
    net.texted.update({"s", "t"})
    assert _drawn(net, "s", "t")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_where_text_alone_draws_no_end():
    """A1: a where-text names a copy, so two texted pins with no ink between them are not drawn."""
    net = _homed({"s": ((P1, (1, 1)),), "t": ((P1, (2, 2)),)})
    net.texted.update({"s", "t"})
    assert not _drawn(net, "s", "t")


@pytest.fixture(scope="module")
def relay_loop():
    model = relay_loop_built().model
    with pytest.MonkeyPatch.context() as patch:
        return _built_of(model, symbol_kit(model, LIBRARY), patch)


@pytest.mark.rule("READ-POWER-INK")
def test_a_pin_whose_power_symbol_is_removed_leaves_its_conductor_undrawn_while_its_partner_keeps_a_symbol(relay_loop):
    """A3: a conductor between two powered pins is drawn only while both stand on their symbols; the bare pin's end is CONNECTION_NOT_DRAWN."""
    net = relay_loop.netlist()
    powered = {port for part in net.pages.values() for port in part.powers}
    ends = [(n.value, f.value) for n, f in far_pins(relay_loop.model, [net.ids[p] for p in net.placed if net.at_home(p)])]
    bare = next(f for n, f in ends if n in powered and f in powered and all(m in powered for m, g in ends if g == f))
    page, part = next((pg, pt) for pg, pt in net.pages.items() if bare in pt.powers)
    sym, pin = part.powers[bare], part.ports[bare]
    leads = {w.id for w in part.drawing.wires if {w.points[0], w.points[-1]} == {pin, sym}}
    kept = tuple(s for s in part.drawing.symbols if not (s.key in drawn_power.POWER_KEYS and s.ports[:1] == (bare,)))
    wires = tuple(w for w in part.drawing.wires if w.id not in leads)
    planted = relay_loop.patched(page, symbols=kept, wires=wires)
    assert relay_loop.count("CONNECTION_NOT_DRAWN", planted) > relay_loop.count("CONNECTION_NOT_DRAWN")


def _page(wires: tuple[DrawnWire, ...], ports: dict[str, tuple[int, int]], anchors: set[tuple[int, int]]) -> Any:
    edges = {frozenset(w.points): {i} for i, w in enumerate(wires)}
    return SimpleNamespace(
        drawing=SimpleNamespace(wires=wires, symbols=()),
        ports=ports,
        graph=SimpleNamespace(edges=edges, tees=()),
        anchors={*ports.values(), *anchors},
    )


@pytest.mark.rule("BUNDLE-ARROW")
def test_a_lane_foot_whose_piece_holds_no_port_is_a_dangling_end_even_where_an_anchor_stands():
    """R2014: a foot with no port is never skipped silently; it raises DANGLING_WIRE_END where the wire end alone would be met."""
    lane = DrawnWire("lane", ((200, 108), (240, 108)), "trunk")
    pages = cast("Any", {P1: _page((lane,), {}, {(200, 108), (240, 108)})})
    assert dangling_findings(Netlist(pages, UnionFind(), {}, {}, {}, {})) == ()
    bare = dangling_findings(Netlist(pages, UnionFind(), {}, {}, {}, {}, lanes=Lanes(bare={(P1, (240, 108))})))
    assert [f.message for f in bare] == ["wire end at 240, 108"]


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_on_a_marker_origin_is_met_only_by_the_marker_of_its_own_net():
    """R3401 (checker half of KI-411): the end at a marker's origin is met by that net's marker, and dangling at another net's."""
    wire = DrawnWire("w", ((0, 0), (40, 0)), "wire", net="a")
    marker = SimpleNamespace(x=40, y=0, ports=("p",), net="a", key="reference-marker")
    part = _page((wire,), {"p": (0, 0)}, set())
    for net, found in (("a", []), ("b", ["wire end at 40, 0"])):
        part.drawing.symbols = (replace_net(marker, net),)
        assert [f.message for f in dangling_findings(Netlist(cast("Any", {P1: part}), UnionFind(), {}, {}, {}, {}))] == found


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_marker_whose_net_text_is_empty_is_still_a_marker():
    """R3417: a marker is read by its key (`MARKER_KEYS`), so a net text of `""` never unmarks it; a junction dot with a net is no marker."""
    assert is_marker(cast("Any", SimpleNamespace(key="reference-marker", ports=("p",), net="")))
    assert not is_marker(cast("Any", SimpleNamespace(key="junction-dot", ports=("p",), net="a")))


def _hidden_pe_design(*, rail: bool = True) -> tuple[Any, Any]:
    """A motor cabled to a declared PE strip (a rail unless `rail` is off) and a 24 V lamp, built with `[export] hide_pe`: PE is in no drawn net."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5-TWIN")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    pe = d.terminal_strip("PE", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", 2, bridged=True, rail=rail)
    with d.function("FAN", "Fan"):
        q1, f1, m1 = (d.device(t, k) for t, k in (("Q1", "DEMO-CTR-3P-24"), ("F1", "DEMO-OVERLOAD-3P"), ("M1", "DEMO-MOTOR-4KW")))
        w1 = d.cable("W1", "DEMO-CBL-4G1.5")
        d.series(ac, q1.main, f1.main, wire=(BK, 2.5))
        w1.core(GNYE, pe[1].outer, m1.motor.PE)
        d.series(f1.main, w1, m1.motor)
    d.earth(pe[1].inner)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    live, zero = x1.run("24V", 2, bridged=True, rail=True), d.terminal_strip("X2", "DEMO-TB-2.5", 4).run("0V", 2, bridged=True, rail=True)
    dc = d.dc_supply("24VDC", plus=live[1], minus=zero[1], voltage=24)
    d.series(dc.plus, d.device("H1", "DEMO-LAMP-24").lamp, dc.minus, wire=(BU, 0.75))
    return d, cab


@pytest.mark.rule("DRAWN-NETLIST")
def test_every_port_the_reader_spells_is_in_a_drawn_net_with_pe_hidden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """el-0136: a marker or a power lead is spelled only for a port of a drawn net, with `[export] hide_pe` leaving the PE ports in no drawn net."""
    asked: list[tuple[Any, Id[Port]]] = []
    spell = drawn_identity_module.net_text
    for module in (read_markers_module, draw_power_module):
        monkeypatch.setattr(module, "net_text", lambda m, p: (asked.append((m, p)), spell(m, p))[1])
    (tmp_path / "fransys.toml").write_text("[export]\nhide_pe = true\n")
    d, cab = _hidden_pe_design()
    fr.build(d, unit_document(cab), settings=fr.settings(tmp_path / "fransys.toml"))
    assert asked
    assert [p for m, p in asked if drawn_net_of(m, p) is None] == []


def replace_net(marker: SimpleNamespace, net: str) -> SimpleNamespace:
    return SimpleNamespace(**{**vars(marker), "net": net})


@pytest.mark.rule("READ-REFERENCES")
def test_an_off_stub_whose_printed_text_differs_by_one_character_is_not_read(bank40):
    """S2b: a stub counts only where its whole text is drawn at its port; one character off is REFERENCE_NOT_READABLE and the stub is unread."""
    net = bank40.netlist()
    for page, part in net.pages.items():
        for i, symbol in enumerate(part.drawing.symbols):
            record = next(
                (
                    r
                    for k, r in net.records.items()
                    if r.star is StarKind.OFF and r.page == page and net.markers.get(k) == (page, (symbol.x, symbol.y))
                ),
                None,
            )
            if record is None or dict(symbol.slots).get(MARKER_SLOT) is None:
                continue
            slots = tuple((k, v + "x") if k == MARKER_SLOT else (k, v) for k, v in symbol.slots)
            symbols = tuple(replace(s, slots=slots) if j == i else s for j, s in enumerate(part.drawing.symbols))
            planted = bank40.patched(page, symbols=symbols)
            assert bank40.count("REFERENCE_NOT_READABLE", planted) > bank40.count("REFERENCE_NOT_READABLE")
            assert record.id.value not in bank40._net(planted).markers
            return
    pytest.fail("no read off stub in the bank of 40")


_Stands = dict[str, tuple[str, str | None, str | None, str]]
NONE = cast("Any", None)  # the monkeypatched reads take no model


def _powered(
    monkeypatch: pytest.MonkeyPatch,
    stands: _Stands,
    *,
    wiring: str = "lead",
    nets: dict[str, str] | None = None,
) -> Netlist:
    """One page per port of `stands` (port: symbol kind, printed text, cabinet, page): a pin at (0, 16), a power symbol at (0, 0), a lead or not."""
    ids = {p: Id[Any](kind="port", value=p) for p in stands}
    pages: dict[Any, Any] = {}
    at: dict[str, Any] = {}
    monkeypatch.setattr(drawn_netlist_module, "port_points", lambda s, _lib: at[s.id])
    for port, (kind, _, _, page) in stands.items():
        device = SimpleNamespace(id=f"d-{port}", key="box", x=0, y=16, ports=(), net=None)
        slots = ((marking_slot("1"), stands[port][1]),) if stands[port][1] else ()  # the text the page prints
        bar = SimpleNamespace(id=f"p-{port}", key=power_symbol_key(kind), x=0, y=0, ports=(port,), net=None, slots=slots)
        wires = tuple(SimpleNamespace(points=p) for p in {"lead": [((0, 16), (0, 0))], "stub": [((0, 16), (16, 16))]}.get(wiring, ()))
        at[bar.id], at[device.id] = [(((0, 16) if wiring == "zero" else (0, 0)), "1")], [((0, 16), "p")]
        pages[Id[Page](kind="page", value=page)] = drawn_netlist_module._part(
            cast("Any", SimpleNamespace(symbols=(device, bar), wires=wires)), {device.id: {"p": ids[port]}}, LIBRARY
        )
    monkeypatch.setattr(drawn_power, "item_unit", lambda _m, port: stands[port][2])
    monkeypatch.setattr(drawn_power, "page_unit", lambda _m, page: next(v[2] for v in stands.values() if v[3] == page.value))
    monkeypatch.setattr(drawn_power, "power_identity", lambda _m, _port, _kind, text: text)
    monkeypatch.setattr(drawn_power, "port_power_kind", lambda _m, port: PowerKind(stands[port.value][0]))
    monkeypatch.setattr(drawn_power, "item_of_port", lambda _m, port: port.value)
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
        (("supply", None, "A", "p2"), False),
    ],
    ids=["same-text-and-cabinet", "other-text", "other-cabinet", "other-symbol", "no-cabinet", "no-printed-text"],
)
def test_two_power_symbols_join_iff_they_print_one_potential_in_one_cabinet(
    monkeypatch: pytest.MonkeyPatch, other: tuple[str, str, str, str], *, joined: bool
):
    """R3 first half (KI-1364): the join key is (cabinet, symbol, printed slot text), never the model's; a supply printing none names no potential."""
    net = _powered(monkeypatch, {"a": ("supply", "24V", "A", "p1"), "b": other})
    join_power(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    assert _same_piece(net, "a", "b") is joined


@pytest.mark.rule("READ-RAILS")
@pytest.mark.parametrize("kind", ["pe", "ground", "supply"])
@pytest.mark.parametrize(
    ("nets", "shared"), [({"a": "PE:A", "b": "PE:A", "c": "PE:A"}, False), ({"a": "n1", "b": "n2", "c": "n1"}, True)], ids=["bonded", "unbonded"]
)
def test_unbonded_nets_printing_one_identity_in_a_flagged_cabinet_are_rail_identity_shared(
    monkeypatch: pytest.MonkeyPatch, kind: str, nets: dict[str, str], *, shared: bool
):
    """R3 second half: three symbols of one flagged cabinet pass when their nets are one bonded class, and fail when two nets are not."""
    stands: _Stands = {p: (kind, "24V" if kind == "supply" else None, "A", f"p{p}") for p in "abc"}
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
    found = rail_findings(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    if shared:
        expect_codes(SimpleNamespace(findings=found), "RAIL_IDENTITY_SHARED")
        assert ("bond the nets" in found[0].message) is (kind == "ground")
    else:
        assert found == ()


@pytest.mark.rule("READ-RAILS")
def test_a_ground_identity_carries_its_source_and_two_sources_are_two_classes(monkeypatch: pytest.MonkeyPatch):
    """R2590: two unbonded sources in one cabinet are two ground classes; each joins its own symbols by ink and never the other's."""
    rails = frozenset({"0V"})
    ident = {"a": (rails, "U1"), "b": (rails, "U1"), "c": (rails, "U2"), "d": (rails, "U2")}
    net = _powered(monkeypatch, {p: ("ground", None, "A", f"p{p}") for p in ident})
    monkeypatch.setattr(drawn_power, "power_identity", lambda _m, port, _kind, _text: ident[port.value])
    join_power(net, None)  # ty: ignore[invalid-argument-type] the monkeypatched reads take no model
    assert _same_piece(net, "a", "b")
    assert _same_piece(net, "c", "d")
    assert not _same_piece(net, "a", "c")


@pytest.mark.rule("READ-RAILS")
@pytest.mark.parametrize(("scope", "drawn"), [("A", True), ("B", False)], ids=["one-scope", "two-scopes"])
def test_a_conductor_between_two_inked_power_symbols_is_drawn_only_when_one_scope_holds_both(
    monkeypatch: pytest.MonkeyPatch, scope: str, *, drawn: bool
):
    """R3699 (W3): symbols of two drawing sets are two pieces, so their conductor is undrawn unless a wire or stub carries it."""
    net = _powered(monkeypatch, {"a": ("ground", None, "A", "p1"), "b": ("ground", None, scope, "p2")})
    join_power(net, NONE)
    net.home.update({port: frozenset(page for page, _ in at) for port, at in net.placed.items()})
    net.live.update(net.union.find((page, node)) for page, part in net.pages.items() for node in part.nodes)
    assert _carried(net, {}, _pairs(net, {}), ("a", "b")) is drawn


@pytest.mark.rule("READ-POWER-INK")
@pytest.mark.parametrize("wiring", ["lead", "none", "stub", "zero"], ids=["lead", "no-ink", "off-a-pin-with-another-wire", "stands-on-its-pin"])
def test_a_power_symbol_is_joined_to_its_pin_by_ink_alone(monkeypatch: pytest.MonkeyPatch, wiring: str):
    """R4 over ink (KI-1363): a lead, or the symbol standing on its pin, joins it; one off its pin is an ERROR, even on a pin with another wire."""
    found = power_findings(_powered(monkeypatch, {"a": ("ground", None, "A", "p1")}, wiring=wiring), NONE)
    if wiring in ("lead", "zero"):
        assert found == ()
    else:
        expect_codes(SimpleNamespace(findings=found), "POWER_SYMBOL_NOT_JOINED")
        assert "report it" in found[0].message


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
def test_a_drawing_printing_every_pin_marking_as_the_model_gives_it_has_no_printed_text_wrong(card16):
    assert "PRINTED_TEXT_WRONG" not in card16.codes()
    assert card16.netlist().marks


@pytest.mark.rule("READ-POWER-INK")
@pytest.mark.parametrize(("kind", "found"), [("ground", False), ("supply", True), ("pe", True)], ids=["same-kind", "pin-is-supply", "pin-is-pe"])
def test_a_power_symbol_of_another_kind_than_its_pin_is_power_symbol_wrong_kind(monkeypatch: pytest.MonkeyPatch, kind: str, *, found: bool):
    """A5: the symbol key is the key of the pin's potential kind; ground drawn as protective earth is an ERROR."""
    net = _powered(monkeypatch, {"a": ("ground", None, "A", "p1")})
    monkeypatch.setattr(drawn_power, "port_power_kind", lambda _m, _port: PowerKind(kind))
    codes = {f.code for f in power_findings(net, NONE)}
    assert (codes == {"POWER_SYMBOL_WRONG_KIND"}) is found
    assert found or codes == set()


@pytest.mark.rule("READ-IDENTITY")
def test_two_pins_with_their_marking_texts_swapped_are_printed_text_wrong(card16):
    page, symbol, (a, b) = _marked(card16)
    slots = list(symbol.slots)
    (sa, ta), (sb, tb) = slots[a], slots[b]
    slots[a], slots[b] = (sa, tb), (sb, ta)
    swapped = replace(symbol, slots=tuple(slots))
    drawing = card16.drawings[page]
    patched = card16.patched(page, symbols=tuple(swapped if s.id == symbol.id else s for s in drawing.symbols))
    found = drawing_sweep(card16.model, card16._net(patched))
    expect_codes(SimpleNamespace(findings=found), "PRINTED_TEXT_WRONG")
    assert sum(f.code == "PRINTED_TEXT_WRONG" for f in found) == 2


@pytest.mark.rule("READ-IDENTITY")
def test_a_pin_the_sheets_leave_off_is_not_read_for_its_marking(card16, monkeypatch):
    monkeypatch.setattr(drawn_printed, "hidden_pins", lambda _model: set(card16.netlist().ids.values()))
    page, symbol, (a, _) = _marked(card16)
    gone = replace(symbol, slots=tuple(s for i, s in enumerate(symbol.slots) if i != a))
    drawing = card16.drawings[page]
    patched = card16.patched(page, symbols=tuple(gone if s.id == symbol.id else s for s in drawing.symbols))
    assert card16.count("PRINTED_TEXT_WRONG", patched) == 0


def _wrong(built: Built, page, **fields) -> list[str]:
    """The PRINTED_TEXT_WRONG messages over `built` with `page`'s drawing changed by `fields`."""
    return built.messages("PRINTED_TEXT_WRONG", built.patched(page, **fields))


@pytest.mark.rule("READ-IDENTITY")
def test_two_tags_swapped_are_printed_text_wrong(card16):
    """T2: the TAG texts of two symbols swapped; each prints the other's tag."""
    page, drawing = next((p, d) for p, d in card16.drawings.items() if sum(t.kind == "TAG" for t in d.texts) > 1)
    a, b = [i for i, t in enumerate(drawing.texts) if t.kind == "TAG" and t.owner][:2]
    texts = list(drawing.texts)
    texts[a], texts[b] = replace(texts[a], text=texts[b].text), replace(texts[b], text=texts[a].text)
    assert len(_wrong(card16, page, texts=tuple(texts))) == 2


@pytest.mark.rule("READ-IDENTITY")
def test_a_table_head_not_the_coils_contact_table_is_printed_text_wrong(card16):
    """T4: a head symbol standing for a coil whose cells are not `coil_table_texts` of it."""
    page, drawing = next(iter(card16.drawings.items()))
    net = card16.netlist()
    coil = function_of(card16.model, next(iter(net.keys.values())))
    head = replace(drawing.symbols[0], texts=(("k.no", "p9"),))
    net.heads[head.id] = coil
    found = list(drawn_printed._tables(card16.model, replace(net, pages={page: replace(net.pages[page], drawing=replace(drawing, symbols=(head,)))})))
    assert len(found) == 1


@pytest.mark.rule("READ-IDENTITY")
def test_a_where_line_naming_no_other_placement_is_printed_text_wrong(card16):
    """T5: a terminal placed once owes no where-line, so any WHERE text under its tag is wrong."""
    page, drawing = next(iter(card16.drawings.items()))
    tag = next(t for t in drawing.texts if t.kind == "TAG" and t.owner)
    where = replace(tag, kind="WHERE", text="p9 A1")
    assert len(_wrong(card16, page, texts=(*drawing.texts, where))) == 1


@pytest.mark.rule("READ-IDENTITY")
def test_a_frame_label_not_its_units_title_is_printed_text_wrong(card16):
    """T6: the frame of the build prints a label other than its title."""
    page, outline = next((p, o) for p, d in card16.drawings.items() for o in d.outlines)
    label = DrawnText("x", Box(0, 0, 8, 2), "TAG", "NW", outline.id)
    other = replace(card16.drawings[page], outlines=(replace(outline, label=label),))
    assert len(card16.messages("PRINTED_TEXT_WRONG", {**card16.drawings, page: other})) == 1


@pytest.mark.rule("READ-IDENTITY")
def test_a_power_symbol_printing_another_potential_is_printed_text_wrong(card16, monkeypatch):
    """A5: a symbol that prints `5V` stands on a net whose potential is `24V` (card16 prints no potential, so the net's is given)."""
    page, symbol = next((p, s) for p, d in card16.drawings.items() for s in d.symbols if s.key in drawn_power.POWER_KEYS)
    monkeypatch.setattr(drawn_printed, "port_power_text", lambda _model, _port: "24V")
    drawing = card16.drawings[page]

    def swapped(text: str) -> list[str]:
        marked = replace(symbol, slots=(("marking.supply", text),))
        return _wrong(card16, page, symbols=tuple(marked if s.id == symbol.id else s for s in drawing.symbols))

    assert (len(swapped("5V")), len(swapped("24V"))) == (1, 0)


H, V = [(-20, 0), (20, 0)], [(0, -20), (0, 20)]
FOUR = [[(-20, 0), (0, 0)], [(0, 0), (20, 0)], [(0, 0), (0, 20)], [(0, 0), (0, -20)]]


def _rule(rule: str, code: str | None, geometry: Any) -> Any:
    return pytest.param(code, geometry, marks=pytest.mark.rule(rule), id=f"{rule}-{code or 'drawn-right'}")


INK_CASES = [
    _rule("READ-T-DOT", "MISSING_JUNCTION_DOT", (FOUR, set(), [])),
    _rule("READ-T-DOT", None, (FOUR, {(0, 0)}, [])),
    _rule("READ-DOT-CROSSING", "DOT_ON_CROSSING", ([H, V], {(0, 0)}, [])),
    _rule("READ-DOT-CROSSING", None, ([H, V], set(), [])),
    _rule("READ-WIRE-OVER-TIP", "WIRE_OVER_PIN_TIP", ([H], set(), [(0, 0)])),
    _rule("READ-WIRE-OVER-TIP", None, ([[(-20, 0), (0, 0)]], set(), [(0, 0)])),
]


def _ink(wires: list[list[tuple[int, int]]], dots: set[tuple[int, int]], tips: list[tuple[int, int]]) -> tuple[Any, ...]:
    page = Id[Page](kind="page", value="p")
    return ink_findings(cast("Any", SimpleNamespace(pages={page: SimpleNamespace(graph=page_graph(wires, dots, tips))})))


@pytest.mark.parametrize(("code", "geometry"), INK_CASES)
def test_ink_the_page_graph_lists_is_an_error_of_its_code_and_ink_drawn_right_gives_none(code: str | None, geometry: Any):
    """R5, R6, R7: a four-way with no dot, a dot on a crossing and a wire over a pin tip each give one finding; the same drawn right, none."""
    found = _ink(*geometry)
    assert len(found) == (code is not None)
    if code:
        expect_codes(SimpleNamespace(findings=found), code)


@pytest.mark.rule("READ-T-DOT")
def test_a_dotless_three_way_is_reported_once_by_the_sweep_side_of_tees_only():
    """R6: a dotless T is a tee, which short_findings reports; ink_findings leaves it to avoid a second finding."""
    assert _ink([H, [(0, 0), (0, 20)]], set(), []) == ()


def _ports_of(model, port):
    """The ports of the physical net `port` stands on."""
    physical = net_of(model, port)
    assert physical is not None
    return physical.ports


def _pe_build():
    """A pump cabinet with a flagged PE strip: M1 earthed by `d.earth`, M2 by a conductor to the strip, so two PE nets meet only there."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        pe = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", 2, bridged=True, rail=True)
        m1, m2 = d.device("M1", "DEMO-MOTOR-4KW"), d.device("M2", "DEMO-MOTOR-4KW")
    d.earth(pe[1].inner, m1.motor["PE"])
    d.series(pe[2].outer, m2.motor["PE"], wire=(GNYE, 2.5))
    return fr.build(d, unit_document(cab))


def _pe_model():
    return _pe_build().model


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


def _reference_symbol(built: Built) -> tuple[Any, Any]:
    """The page and drawn symbol of the first reference marker `reference_targets` names."""
    markers = layout_of(built.model, LinkMarker)
    for (page, _), ends in reference_targets(built.model).items():
        for marker, _, _, text in ends:
            for symbol in built.drawings[page].symbols:
                if symbol.ports[:1] == (markers[marker].port.value,) and (MARKER_SLOT, text) in symbol.slots:
                    return page, symbol
    pytest.fail("no drawn reference marker in the bank of 40")


def _with(built: Built, page: Any, old: Any, **fields: Any) -> dict[Any, Any]:
    return built.patched(page, symbols=tuple(replace(s, **fields) if s is old else s for s in built.drawings[page].symbols))


@pytest.mark.rule("READ-REFERENCES")
def test_a_marker_printing_another_text_than_derives_is_reference_not_readable(bank40):
    """R2: the drawn text is compared whole with `marker_text`; any other text is REFERENCE_NOT_READABLE."""
    page, symbol = _reference_symbol(bank40)
    assert bank40.count("REFERENCE_NOT_READABLE") == 0
    assert bank40.count("REFERENCE_NOT_READABLE", _with(bank40, page, symbol, slots=((MARKER_SLOT, dict(symbol.slots)[MARKER_SLOT] + " x"),))) == 1


@pytest.mark.rule("READ-REFERENCES")
def test_a_marker_drawn_in_another_frame_cell_than_the_stored_one_is_reference_not_readable(bank40):
    """R2: the stored cell must equal `frame_cell` of the drawn point."""
    page, symbol = _reference_symbol(bank40)
    sheet = sheet_format_of(bank40.model, layout_of(bank40.model, Page)[page].sheet_format)
    moved = symbol.x + 480
    assert frame_cell(LIBRARY, sheet, moved, symbol.y) != frame_cell(LIBRARY, sheet, symbol.x, symbol.y)
    assert bank40.count("REFERENCE_NOT_READABLE", _with(bank40, page, symbol, x=moved)) == 1


@pytest.mark.rule("READ-REFERENCES")
def test_one_number_naming_two_groups_in_one_drawing_set_is_reference_not_readable(bank40, monkeypatch: pytest.MonkeyPatch):
    """R2: every `#n` of a set names one group; here all ends claim number 1, so each set's other groups collide with it."""
    real = reference_targets(bank40.model)
    renumbered = {key: tuple((marker, 1, group, text) for marker, _, group, text in ends) for key, ends in real.items()}
    monkeypatch.setattr(drawn_references, "reference_targets", lambda _: renumbered)
    assert bank40.count("REFERENCE_NOT_READABLE") > 0
    assert any("names" in message for message in bank40.messages("REFERENCE_NOT_READABLE", bank40.drawings))


def _group_roots(built: Built) -> dict[Any, list[Any]]:
    """The roots of the drawn reference markers on a node, by reference group, in a union holding only `join_references`' joins."""
    net, markers, union = built.netlist(), layout_of(built.model, LinkMarker), UnionFind()
    drawn_references.join_references(built.model, net.pages, LIBRARY, union)
    found: dict[Any, list[Any]] = {}
    for (page, _), ends in reference_targets(built.model).items():
        for marker, _, group, text in ends:
            for s in net.pages[page].drawing.symbols:
                if s.ports[:1] == (markers[marker].port.value,) and (MARKER_SLOT, text) in s.slots and (s.x, s.y) in net.pages[page].nodes:
                    found.setdefault(group, []).append(union.find((page, (s.x, s.y))))
    return found


@pytest.mark.rule("READ-REFERENCES")
def test_the_references_join_the_markers_through_reference_targets_alone(bank40, monkeypatch: pytest.MonkeyPatch):
    """R2: the drawn markers of one reference group are one piece; with no candidate ends the lexicon joins nothing."""
    joined = _group_roots(bank40)
    assert any(len(roots) > 1 for roots in joined.values())
    assert all(len(set(roots)) == 1 for roots in joined.values())
    monkeypatch.setattr(drawn_references, "reference_targets", lambda _: {})
    assert all(len(set(roots)) == len(roots) for roots in _group_roots(bank40).values())


@pytest.mark.rule("G01-CONNECTED")
def test_a_terminals_sides_are_joined_by_their_symbol_and_the_poles_of_an_overload_are_not():
    """R2079 G1: both ports at one node of one symbol join; a conductive pole link of a switch stands at two nodes and joins nothing."""
    d = fr.design("demo_parts")
    f1, x1 = d.device("F1", "DEMO-OVERLOAD-3P"), d.terminal_strip("X1", "DEMO-TB-2.5")
    runs = [x1.run(phase, 1) for phase in ("L1", "L2", "L3")]
    d.series(f1.main, tuple(run[1] for run in runs), wire=(fr.colours.BK, 2.5))
    model = fr.build(d).model
    groups = tuple(link_groups(model, lambda role: role.joins_net))
    terminals = terminal_items(model)
    joins = node_joins(symbol_kit(model, LIBRARY), LIBRARY)
    assert {g.item for g in groups} - set(terminals)  # the overload's three pole links are conductive
    assert len(joins) == sum(g.item in terminals for g in groups) > 0


@pytest.mark.rule("G01-CONNECTED")
def test_two_kit_mapped_nets_drawn_on_one_node_are_joined_by_ink():
    """W5 (KI-1365): a terminal symbol draws its pins n and s at one node; the kit maps them to ports of two nets no link group names: one piece."""
    a, b, c = (Id[Any](kind="port", value=v) for v in "abc")
    assert node_joins({"lead": Pick("terminal", 1, frozendict({a: "n", b: "s", c: "e"}))}, LIBRARY) == ((a, b), (a, c))  # ty: ignore[invalid-argument-type] a hand kit keyed by a plain name


@pytest.mark.rule("G01-CONNECTED")
@pytest.mark.parametrize(("bridged", "pairs"), [((2, 6), 4), (False, 0)], ids=["bridged", "plain"])
def test_each_declared_bridge_of_a_strip_is_a_join_pair_and_a_plain_strip_has_none(*, bridged: tuple[int, int] | bool, pairs: int):
    """R1009, R2079 G2: terminals 2 to 6 bridged give four consecutive pairs from `is_bridge` and the conductor's ends; no bridge gives none."""
    d = fr.design("demo_parts")
    d.terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=bridged)
    assert len(drawn_netlist_module._bridges(fr.build(d).model)) == pairs


@pytest.mark.rule("DRAWN-NETLIST")
def test_the_reader_spells_two_drawn_nets_a_bridge_joins_as_two_nets():
    """el-0136: a bridged run is one `net_of` net and two drawn nets; `net_text` names each by its own drawn net, as the core's wires do."""
    d = fr.design("demo_parts", place="HALL")
    d.location("HALL", "Pump hall")
    feed = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5").run("0V", bridged=True)
    for tag in ("S1", "S2"):
        d.series(feed, d.device(tag, "DEMO-MCB-C6").element, zero, wire=(BU, 0.5))
    built = fr.build(d)
    assert "FUNCTION_HALF_CONNECTED" not in {f.code for f in built.findings}
    model = built.model
    for port in ports(model):
        if drawn := drawn_net_of(model, port):
            assert net_text(model, port) == net_key(model, drawn.ports)
    joined = {n.ports for p in ports(model) if (n := net_of(model, p))}
    assert any(len({net_text(model, p) for p in net} - {""}) > 1 for net in joined)


class _Open(NamedTuple):
    pass


@fr.unit("demo-trace", revision=1, interface_version=1, date="2026-11-16", text="first", by="AB")
def _trace_board(u: Any) -> _Open:
    pcb = u.device("A1", "DEMO-PCB-IO")
    h1, h2 = (u.device(name, "DEMO-LAMP-24", parent=pcb) for name in ("H1", "H2"))
    u._engine.net("n1", h1["1"], h2["1"])  # a net with no conductor: the board's trace (KI-1041)
    u.series(h1["2"], h2["2"], wire=("BU", 0.5))  # a drawn page: the lamps stand at home
    return _Open()


def test_a_conductorless_board_net_is_drawn_by_the_standard_routing() -> None:
    """R2620, R1219: a board's trace between two drawn ports is routed or falls back to a reference, so none counts CONNECTION_NOT_DRAWN."""
    d = fr.design("demo_parts")
    d.add(_trace_board, "U1")
    built = fr.build(d, unit_document("demo-trace"))
    codes = [f.code for f in fr.check(built)]
    assert "CONNECTION_NOT_DRAWN" not in codes
    assert "INK_WITHOUT_CONDUCTOR" not in codes  # a board trace is a conductor (R2626)
    assert "SET_WITHOUT_PAGE" not in codes
    assert len(drawn_physical_nets(built.model)) == 2  # the trace and the series wire are both nets the drawing joins


def _ink_net(
    monkeypatch: pytest.MonkeyPatch, edges: list[tuple[tuple[int, int], tuple[int, int]]], pairs: list[tuple[str, str]], **kw: Any
) -> list[str]:
    """INK_WITHOUT_CONDUCTOR messages of one page: ports a, b, c, h stand at fixed points, `edges` join points, `pairs` are the model's conductors."""
    at = {"a": (0, 0), "b": (16, 0), "c": (8, 16), "h": (8, 0)}
    ids = {p: Id[Any](kind="port", value=p) for p in at}
    mark = [SimpleNamespace(x=x, y=y, key="marker-arrow", ports=("p",), net="n") for x, y in kw.get("markers", ())]
    part = _page(tuple(DrawnWire("n", e, "w") for e in edges), at, set())
    part.powers, part.drawing.symbols = kw.get("powers", {}), mark
    union = UnionFind()
    for a, b in edges:
        union.union((P1, a), (P1, b))
    for x, y in kw.get("markers", ()) if kw.get("partner") else ():  # the marker's far piece holds port h
        union.union((P1, (x, y)), (P1, at["h"]))
    placed = {p: ((P1, xy),) for p, xy in at.items()}
    net = SimpleNamespace(
        pages={P1: part}, ids=ids, joins=kw.get("joins", ()), lanes=Lanes(bare={(P1, f) for f in kw.get("feet", ())}), union=union, placed=placed
    )
    monkeypatch.setattr(drawn_ends_module, "far_pins", lambda _m, _near: tuple((ids[x], ids[y]) for x, y in pairs))
    monkeypatch.setattr(drawn_ends_module, "port_designation", lambda _m, i: i.value)
    monkeypatch.setattr(drawn_ends_module, "port_joins", lambda _m: tuple((ids[x], ids[y]) for x, y in kw.get("header", ())))
    return [f.message for f in ink_without_conductor(cast("Any", None), cast("Any", net))]


_DOT = (8, 8)
_STAR = [((0, 0), _DOT), ((16, 0), _DOT), ((8, 16), _DOT)]  # a, b, c joined by a dot
_HUB = [("a", "h"), ("b", "h"), ("c", "h")]


@pytest.mark.rule("DRAWN-NETLIST")
@pytest.mark.parametrize(
    ("edges", "pairs", "kw", "found"),
    [
        ([((0, 0), (16, 0))], [("a", "b")], {}, 0),
        ([((0, 0), (16, 0))], [("a", "h"), ("b", "h")], {}, 1),
        ([((0, 0), (16, 0))], [("a", "b"), ("a", "b")], {}, 0),  # twin conductors: one run certifies the set
        ([((0, 0), (16, 0))], [], {"joins": ((Id[Any](kind="port", value="a"), Id[Any](kind="port", value="b")),)}, 0),
        (_STAR, [("a", "b"), ("b", "c")], {}, 0),
        (_STAR, [("a", "b")], {}, 1),
        ([((0, 0), (16, 0))], [], {"header": [("a", "b")]}, 0),  # a part's own join (`joins =`) is no ink without a conductor
        ([((0, 0), (16, 0))], [], {}, 1),
        (_STAR, _HUB, {"feet": [_DOT]}, 0),  # a bundle lane foot: the arrow joins ports of one net
        (_STAR, [("a", "h"), ("b", "h")], {"feet": [_DOT]}, 1),  # R2298: ports of two nets at a foot
        ([*_STAR, ((8, 0), _DOT)], _HUB, {}, 0),  # the hub is a terminal of the dot: the pair graph is connected
        ([((0, 0), (16, 0))], [("a", "h"), ("b", "h")], {"markers": [(0, 0)]}, 1),  # a marker on a port point hides no piece
        ([((0, 0), (16, 4))], [("a", "h"), ("b", "h")], {"markers": [(16, 4)], "partner": True}, 0),  # a star onto the marker's far hub
        (_STAR, _HUB, {"markers": [_DOT]}, 1),  # a marker joins no ports of its piece: the hub is in no piece it reaches
        ([((0, 0), (16, 0))], [("a", "h"), ("b", "h")], {"powers": {"a": (0, 0)}}, 0),
        ([((0, 0), (16, 0))], [], {"powers": {"a": (0, 0)}}, 1),  # R2298: ports of two nets at a power symbol
        ([((0, 0), (8, 4)), ((8, 4), (16, 0))], [], {"markers": [(8, 4)]}, 1),  # R2298: ports of two nets through an off-port marker
    ],
    ids=[
        *("run", "run-via-hub", "twin", "node", "dot-tree", "dot-split", "part-join", "no-join"),
        *(
            "lane-foot",
            "foot-two-nets",
            "dot-with-hub",
            "marker-on-port",
            "marker-star",
            "marker-two-parts",
            "power",
            "power-two-nets",
            "marker-two-nets",
        ),
    ],
)
def test_ink_between_ports_is_a_model_conductor(monkeypatch: pytest.MonkeyPatch, edges: Any, pairs: Any, kw: Any, found: int):
    """CONDUCTOR-INK, R2297: a run needs a conductor or symbol node between its classes, a dot a connected pair graph; R2287 item 5 clauses."""
    assert len(_ink_net(monkeypatch, edges, pairs, **kw)) == found


def test_ink_without_conductor_is_a_warning_and_the_write_goes_on(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """R2323: a build with ink stock reports the code at WARNING, so `fr.write` is not refused."""
    monkeypatch.setattr(drawn_nets_module, "ink_without_conductor", lambda _m, _n: (drawn_finding("INK_WITHOUT_CONDUCTOR", (), "planted"),))
    expect_codes(result := _pe_build(), "INK_WITHOUT_CONDUCTOR")
    assert [f.severity.name for f in fr.check(result) if f.code == "INK_WITHOUT_CONDUCTOR"] == ["WARNING"]
    assert fr.write(result, tmp_path / "out")


@cache
def _forced_loss_case(plugs: int, pins: int) -> tuple[tuple[Any, ...], tuple[tuple[str, Any], ...]]:
    """The arguments of `lay_out_drawn` for `plugs` mated plugs wired to the first `pins` pins of one device, and every pin of that set.

    Built once per session by the KI-1069 field case's builder; the pins are those `lay_out_core` hands `solve` for the plugs' set.
    """

    args, parts = [], []
    with pytest.MonkeyPatch.context() as mp:
        for target, into in (("fransys._layout_core.lay_out_drawn", args), ("fransys_el.lay_out_core.solve", parts)):
            real = cast("Any", importlib.import_module(target.rpartition(".")[0]))
            real = getattr(real, target.rpartition(".")[2])
            mp.setattr(target, lambda *a, real=real, into=into: (into.append(a), real(*a))[1])
        mated._built.__wrapped__(plugs=plugs, pins=pins)
    own = next(a[0] for a in parts if any("/plug" in s.id for s in a[0].symbols))
    return args[0], tuple((n.id, pin) for n in own.nets for pin in n.pins)


def _lost(shape: tuple[int, int], net_id: str, pin: Any) -> list[str]:
    """The CND and CONNECTION_NOT_ACCOUNTED messages of `lay_out_drawn` after the router loses `pin` of net `net_id` (R2622, R2652)."""
    real = loop_stage.route_pages
    fired: list[Refused] = []

    def lose(placement: Any, cut: Any, prob: Any, options: Any, laid: Any) -> Any:
        routes = real(placement, cut, prob, options, laid)
        skip = pin.sym not in {s.id for s in prob.symbols} or lost_key(net_id, (pin,)) in laid.lost
        if skip:
            return routes
        fired.append(Refused(net_id, (pin,)))
        return replace(routes, failed=(*routes.failed, fired[-1]))

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(loop_stage, "route_pages", lose)
        found = [f.message for f in lay_out_drawn(*_forced_loss_case(*shape)[0])[1] if f.code in {"CONNECTION_NOT_DRAWN", "CONNECTION_NOT_ACCOUNTED"}]
    assert fired, f"the forced loss of {pin.sym}.{pin.pin} never fired: the patch missed the router the loop calls"
    return found


@pytest.mark.rule("ROUTE-FALLBACK-REFERENCE")
def test_a_lost_plug_pin_leaves_no_conductor_end_undrawn():
    """R2631, RR3: the CI witness, lone plug pin 6 of the 2x3 pool, fails with `withdrawn` emptied.
    P1: CND over far_pins, the one home of far_ends (placement_facts.py:95)."""
    assert _lost((2, 3), *next(c for c in _forced_loss_case(2, 3)[1] if "plug0/fn/x1 6" in c[0])) == []


@pytest.mark.rule("ROUTE-FALLBACK-REFERENCE")
@pytest.mark.skipif(not os.environ.get("FALLBACK_PROPERTY"), reason="run by `just fallback-property` and the daily sweep (R2624)")
@pytest.mark.parametrize("shape", [(2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (3, 2), (3, 3), (3, 4)])
def test_no_conductor_end_is_undrawn_after_any_single_lost_pin(shape: tuple[int, int]) -> None:
    """R2583(2), R2624(2): every single lost pin of the plugs' set, plug or device, of each pool shape."""
    cases = _forced_loss_case(*shape)[1]
    failed = [f"{shape} {net_id} {pin.sym}.{pin.pin}: {found}" for net_id, pin in cases if (found := _lost(shape, net_id, pin))]
    print("\n".join(["", f"FALLBACK-CASES {len(cases)}", *(f"FALLBACK-FAILED {line}" for line in failed)]))  # noqa: T201 - the recipe reads these
    assert failed == []


# TEXT_HIDES_TEXT: a falling stock of this file's builds, KI-1132 (R2647, TEXT-WIRE P0).


@pytest.mark.rule("READ-REFERENCES")
def test_an_off_stub_drawn_on_no_ink_is_reference_not_readable(monkeypatch: pytest.MonkeyPatch):
    """KI-1091: a stub printed at its port with no node on ink is a fault naming it, as a pair marker on no wire is; it is not silently unread."""

    class Name(NamedTuple):
        value: str

    pair = SimpleNamespace(far=Name("f"), port=Name("p"))
    stub = SimpleNamespace(id=SimpleNamespace(value="k"), pairs=[pair])
    monkeypatch.setattr(drawn_references, "_lexicon", lambda *_: {(P1, "p", "T"): [stub]})
    for nodes, faulty in (({}, True), ({(1, 1): 0}, False)):
        pages = cast("Any", {P1: SimpleNamespace(nodes=nodes)})
        read = drawn_references._read_stubs(cast("Any", None), {(P1, "p", "T"): [(1, 1)]}, pages, set())
        assert [m for _, _, m in read.faults] == (["stub prints 'T': on no wire of its net"] if faulty else [])
        assert ("k" in read.markers) is not faulty


@pytest.mark.rule("MATE-REFERENCE")
@pytest.mark.parametrize("on_mating", [True, False], ids=["at-the-mating-port", "one-grid-off"])
def test_a_marker_on_a_pins_mating_port_is_a_drawn_node_with_no_wire_to_it(monkeypatch: pytest.MonkeyPatch, *, on_mating: bool):
    """the reader keys each pin's mating point (`PagePart.mating`); a stub standing there is a node, one grid off it is none."""
    pin = Id[Any](kind="port", value="pin")
    connector = SimpleNamespace(id="c", key="connector-fixed", x=0, y=0, ports=(), net=None)
    marker = SimpleNamespace(id="m", key="marker-arrow-turned", x=0, y=16 if on_mating else 24, ports=("p",), net="n")
    drawing = SimpleNamespace(symbols=(connector, marker), wires=())
    points = [((0, -8), "in"), ((0, 8), "out"), ((0, 16), "mate")]
    monkeypatch.setattr(drawn_netlist_module, "port_points", lambda s, _lib: points if s is connector else [])
    part = drawn_netlist_module._part(cast("Any", drawing), {"c": {"in": pin}}, LIBRARY)
    assert part.mating == {"pin": (0, 16)}
    assert ((marker.x, marker.y) in part.nodes) is on_mating
