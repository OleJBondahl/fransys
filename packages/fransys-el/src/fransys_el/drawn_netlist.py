"""The netlist the `Drawing`s of a set draw, read from geometry alone (DRAWN-NETLIST, el-0052).

A page's wires, junction dots and port points give a strict point graph (`page_graph`); a reference
marker joins its partner's page node. A port is reached when a wire end, a dot or a marker stands
on its point. Net identity is the model's: the first port's value of `net_of`, never a wire label.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fransys_layout.core import PageGraph, page_graph
from fransys_layout.drawing import port_points
from fransys_model.derive import (
    build_indexes,
    conductor_ends,
    function_scopes,
    is_bridge,
    link_groups,
    mate_ports,
    port_function,
    set_unit,
)
from fransys_model.layout import DrawingSet, Page, StarKind, layout_of

from .drawn_graph import Union
from .drawn_identity_marks import declared_marks
from .drawn_ids import core_symbol_id, symbol_id
from .drawn_power import POWER_KEYS, join_power, port_nets
from .placement_ids import pin_names, symbol_ids

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.core import PinRef
    from fransys_layout.drawing import Drawing, DrawnSymbol
    from fransys_model.derive import LinkGroup
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import LinkMarker
    from fransys_model.vocab import Port

    from .placement_kit import SymbolKit

__all__ = ["Netlist", "PagePart", "drawn_netlist", "pin_owner", "with_lines"]

XY = tuple[int, int]
_DOT = "junction-dot"


@dataclass(frozen=True)
class PagePart:
    """One page: its drawing, port points (by port value), graph, node set, anchors (where symbols offer a wire end) and power symbols' points."""

    drawing: Drawing
    ports: dict[str, XY]
    graph: PageGraph
    nodes: frozenset[XY]
    anchors: frozenset[XY]
    powers: dict[str, XY] = field(default_factory=dict)


@dataclass(frozen=True)
class Netlist:
    """The pages' parts, one union of all nodes, each port's drawn points (a copy adds one) and each marker's node by record id suffix."""

    pages: dict[Id[Page], PagePart]
    union: Union
    placed: dict[str, tuple[tuple[Id[Page], XY], ...]]
    ids: dict[str, Id[Port]]
    markers: dict[str, tuple[Id[Page], XY] | None]
    records: dict[str, LinkMarker]
    linked: dict[str, str] = field(default_factory=dict)
    live: set[object] = field(default_factory=set)
    lined: dict[str, str] = field(default_factory=dict)
    stub_lines: set[tuple[Id[Page], str]] = field(default_factory=set)
    home: dict[str, frozenset[Id[Page]]] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)
    texted: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)  # ports of a set whose layout failed: no drawing, not expected drawn (KI-779)
    pitch: int = 0
    nets: dict[str, str] = field(default_factory=dict)
    marks: dict[str, str] = field(default_factory=dict)

    def reached(self, port: str) -> bool:
        """True when a wire end, a dot or a marker stands on a point of the port, or on its link's."""
        return port in self.linked or any(at in self.pages[page].nodes for page, at in self.placed[port])

    def at_home(self, port: str) -> list[tuple[Id[Page], XY]]:
        """The port's drawn points on the pages of its own scope: its copies are left out."""
        return [(page, at) for page, at in self.placed.get(port, ()) if page in self.home.get(port, ())]

    def roots(self, port: str) -> set[object]:
        """The components with a wire end, a dot or a marker that hold a point of the port (of its linked port's when it has none)."""
        found = {self.union.find(place) for place in self.placed[self.linked.get(port, port)]}
        return found & self.live

    def net(self, port: str) -> str:
        """The physical net of the port, spelled as `Net.id` is (`net_key`)."""
        return self.nets[port]


def is_marker(symbol: DrawnSymbol) -> bool:
    """True for a reference marker: it draws a port's net and is no junction dot."""
    return bool(symbol.ports and symbol.net and symbol.key != _DOT)


def pin_owner(model: Model, kit: SymbolKit) -> dict[str, dict[str, Id[Port]]]:
    """Each drawn symbol's ports by its pin name: the symbol's pins are joined by the symbol itself."""
    by: dict[str, dict[str, Id[Port]]] = defaultdict(dict)
    for port, pin in pin_names(model, kit, symbol_ids(model, kit)).items():
        by[symbol_id("layout", "core", "drawn_symbol", pin.sym)][pin.pin] = port
    return by


def _port_map(drawing: Drawing, by: Mapping[str, Mapping[str, Id[Port]]], library: Library) -> tuple[dict[str, XY], frozenset[XY], dict[str, XY]]:
    """The model ports' points, every symbol's own port points (a power symbol's wires end on its own) and those of the power symbols by port."""
    found: dict[str, XY] = {}
    powers: dict[str, XY] = {}
    anchors: set[XY] = set()
    for symbol in drawing.symbols:
        names = by.get(symbol.id, {})
        for at, pin in () if is_marker(symbol) else port_points(symbol, library):
            anchors.add(at)
            if symbol.key in POWER_KEYS and symbol.ports:
                powers.setdefault(symbol.ports[0], at)
            if pin in names:
                found[names[pin].value] = at
    return found, frozenset(anchors), powers


def _part(drawing: Drawing, by: Mapping[str, Mapping[str, Id[Port]]], library: Library) -> PagePart:
    ports, anchors, powers = _port_map(drawing, by, library)
    dots = {(s.x, s.y) for s in drawing.symbols if s.key == _DOT}
    graph = page_graph([w.points for w in drawing.wires], dots, list(ports.values()))
    marks = {(s.x, s.y) for s in drawing.symbols if is_marker(s)}
    nodes = {p for edge in graph.edges for p in edge} | graph.joints | (marks & set(ports.values()))
    return PagePart(drawing, ports, graph, frozenset(nodes), anchors | dots | marks, powers)


def _marker_nodes(pages: Mapping[Id[Page], PagePart]) -> dict[str, tuple[Id[Page], XY] | None]:
    """Each marker's (page, point) by the text of its record id; None when it joins nothing."""
    found: dict[str, tuple[Id[Page], XY] | None] = {}
    for page, part in pages.items():
        for symbol in part.drawing.symbols:
            if is_marker(symbol):
                at = (symbol.x, symbol.y)
                found[symbol.id.rpartition(":")[2]] = (page, at) if at in part.nodes else None
    return found


def _join(pages: Mapping[Id[Page], PagePart]) -> Union:
    """One union of every page's wire edges."""
    union = Union()
    for page, part in pages.items():
        for edge in part.graph.edges:
            a, b = tuple(edge)
            union.join((page, a), (page, b))
    return union


def lane_chain(part: PagePart, y: int, pitch: int) -> set[int]:
    """The rows of the trunk lanes one pitch apart in a chain from row `y`: the lanes one arrow stands for (R903)."""
    lanes = [w for w in part.drawing.wires if w.net and w.style == "trunk"]
    chain, grown = {y}, True
    while grown:
        near = {w.points[0][1] for w in lanes if any(abs(w.points[0][1] - row) <= pitch for row in chain)} - chain
        chain, grown = chain | near, bool(near)
    return chain


def _ends_at(part: PagePart, at: XY, pitch: int) -> dict[str, XY]:
    """The end point of each net's wire that ends on column `at.x`, and of each lane of the arrow's trunk (R903).

    The arrow's lane runs past the other lanes' cut end; its trunk is the chain of lane wires one pitch apart from `at`'s y.
    """
    lanes = [w for w in part.drawing.wires if w.net and w.style == "trunk"]
    chain = lane_chain(part, at[1], pitch)
    found: dict[str, XY] = {}
    for wire in lanes:
        if wire.points[0][1] in chain:
            first, last = wire.points[0], wire.points[-1]
            found.setdefault(wire.net, first if abs(first[0] - at[0]) <= abs(last[0] - at[0]) else last)
    for wire in part.drawing.wires:
        for end in (wire.points[0], wire.points[-1]):
            if wire.net and end[0] == at[0] and (wire.style != "trunk" or end[1] in chain):
                found.setdefault(wire.net, end)
    return found


def _lanes(
    union: Union,
    pages: Mapping[Id[Page], PagePart],
    markers: Mapping[str, tuple[Id[Page], XY] | None],
    records: Mapping[str, LinkMarker],
    pitch: int,
) -> None:
    """Join, across each reference (a pair or a star), the lanes of a bundle that reach its markers.

    One arrow stands for the bundle; its other lanes run on to the same cut end (RAIL-LANES), each
    to be joined with the same net's end at the reference's other markers.
    """
    groups: dict[str | frozenset[str], list[tuple[Id[Page], XY]]] = defaultdict(list)
    for key, node in markers.items():
        record = records.get(key)
        if node is None or record is None:
            continue
        if record.star is StarKind.OFF:
            if record.pairs:
                groups[frozenset((record.port.value, record.pairs[0].far.value))].append(node)
            continue
        head = {StarKind.REF: key, StarKind.BRANCH: record.partner.value}.get(record.star)
        groups[head or min(key, record.partner.value)].append(node)
    for nodes in groups.values():
        first: dict[str, tuple[Id[Page], XY]] = {}
        for page, at in nodes:
            for net, end in _ends_at(pages[page], at, pitch).items():
                union.join(first.setdefault(net, (page, end)), (page, end))


def _pair(
    union: Union,
    markers: Mapping[str, tuple[Id[Page], XY] | None],
    records: Mapping[str, LinkMarker],
) -> None:
    """Join each pairing marker (not an off stub) to its partner's node."""
    for key, node in markers.items():
        record = records.get(key)
        if node is None or record is None or record.star is StarKind.OFF:
            continue
        if (other := markers.get(record.partner.value)) is not None:
            union.join(node, other)


def _join_copies(union: Union, markers: Mapping[str, tuple[Id[Page], XY] | None], records: Mapping[str, LinkMarker]) -> None:
    """Join the two stubs that name each other on two pages: a copy and its hub stand for one device.

    A stub at a port that names a far port, and a stub at the far port that names it back (R567), both on a node.
    """
    shown: dict[tuple[str, str], list[tuple[Id[Page], XY]]] = defaultdict(list)
    for key, record in records.items():
        if record.star is StarKind.OFF and record.pairs and (node := markers.get(key)) is not None:
            shown[record.port.value, record.pairs[0].far.value].append(node)
    for (port, far), nodes in shown.items():
        for here in nodes:
            for there in shown.get((far, port), ()):
                if here[0] != there[0]:
                    union.join(here, there)


def _unite(net: Netlist, ports: Iterable[str]) -> None:
    """Join, page by page, the points of the ports where one is reached; a port with none rides on the first reached."""
    seen = [p for p in ports if p in net.placed]
    held = [p for p in seen if p in net.linked or any(at in net.pages[page].nodes for page, at in net.at_home(p))]
    on_page: dict[Id[Page], list[XY]] = defaultdict(list)
    for port in seen:
        for page, at in net.placed[port]:
            on_page[page].append(at)
    for page, points in on_page.items():
        if any(at in net.pages[page].nodes for at in points):
            for at in points[1:]:
                net.union.join((page, points[0]), (page, at))
    net.linked.update(dict.fromkeys((p for p in seen if p not in held), held[0]) if held else ())


def _inked(net: Netlist, port: str) -> tuple[Id[Page], XY] | None:
    """The first drawn point with ink of the port, or of the port it is linked to; None when no copy has ink (R1064)."""
    return next(((page, at) for page, at in net.placed.get(net.linked.get(port, port), ()) if at in net.pages[page].nodes), None)


def _link(net: Netlist, model: Model, groups: Iterable[LinkGroup]) -> None:
    """Join the reached ports of each link group (a terminal's sides), of each bridge and of each mated pair on one page (R685, R1009).

    A declared bridge is joined by the terminal table: it draws no ink and no mate stub. Its two drawn partners join
    whether or not either stands on a node (R1009, R1061).
    """
    for group in groups:
        _unite(net, (p.value for p in group.ports))
    bridges = {conductor_ends(model, c) for cs in build_indexes(model).conductors_by_port.values() for c in cs if is_bridge(model, c)}
    for a, b in bridges:
        _unite(net, (a.value, b.value))
        if (here := _inked(net, a.value)) is not None and (there := _inked(net, b.value)) is not None:
            net.union.join(here, there)
    for a, b in mate_ports(model):
        if a.value in net.placed and b.value in net.placed:
            _unite(net, (a.value, b.value))


def _placed(pages: Mapping[Id[Page], PagePart]) -> dict[str, tuple[tuple[Id[Page], XY], ...]]:
    """Every drawn point of each port, in page order: a terminal copy adds one."""
    placed: dict[str, list[tuple[Id[Page], XY]]] = defaultdict(list)
    for page, part in pages.items():
        for port, at in part.ports.items():
            placed[port].append((page, at))
    return {port: tuple(points) for port, points in placed.items()}


def _homes(model: Model, ids: Mapping[str, Id[Port]], placed: Mapping[str, object]) -> dict[str, frozenset[Id[Page]]]:
    """The pages of each placed port's own scope: `function_scopes` gives it first, a page's scope is its set's (unit, place)."""
    sets = layout_of(model, DrawingSet)
    scope_pages: dict[object, set[Id[Page]]] = defaultdict(set)
    for page in layout_of(model, Page).values():
        unit = set_unit(sets[page.drawing_set])
        scope_pages[unit, None if unit is not None else sets[page.drawing_set].location].add(page.id)
    found: dict[str, frozenset[Id[Page]]] = {}
    for port in placed:
        function = port_function(model, ids[port])
        found[port] = frozenset(scope_pages[function_scopes(model, function)[0]]) if function is not None else frozenset()
    return found


def drawn_netlist(
    model: Model,
    kit: SymbolKit,
    drawings: Mapping[Id[Page], Drawing],
    links: Iterable[LinkMarker] | Sequence[LinkMarker],
    library: Library,
) -> Netlist:
    """The `Netlist` of `drawings`; `links` are the marker records the drawings stand for."""
    by = pin_owner(model, kit)
    ids = {p.value: p for pins in by.values() for p in pins.values()}
    groups = tuple(link_groups(model, lambda role: role.joins_net))
    pages = {page: _part(drawing, by, library) for page, drawing in drawings.items()}
    union = _join(pages)
    records = {m.id.value: m for m in links}
    markers = _marker_nodes(pages)
    _pair(union, markers, records)
    _join_copies(union, markers, records)
    placed = _placed(pages)
    _lanes(union, pages, markers, records, library.grid.wire_pitch)
    found = Netlist(
        pages,
        union,
        placed,
        ids,
        markers,
        records,
        home=_homes(model, ids, placed),
        owners={p.value: sym for sym, pins in by.items() for p in pins.values()},
        pitch=library.grid.wire_pitch,
        nets=port_nets(model, ids),
        marks=declared_marks(drawings, by, library),
    )
    _link(found, model, groups)
    join_power(found, model)
    found.live.update(union.find((page, at)) for page, part in pages.items() for at in part.nodes)
    return found


def with_lines(net: Netlist, model: Model, kit: SymbolKit, lines: Mapping[PinRef, str]) -> Netlist:
    """`net` with each port's `cut_lines` line, and the lines an OFF stub stands on (R481, R754.3)."""
    line_of = {(core_symbol_id(ref.sym), ref.pin): line for ref, line in lines.items()}
    net.lined.update(
        {port.value: line_of[sid, pin] for sid, pins in pin_owner(model, kit).items() for pin, port in pins.items() if (sid, pin) in line_of}
    )
    net.stub_lines.update(
        (r.page, net.lined[r.port.value])
        for k, r in net.records.items()
        if r.star is StarKind.OFF and net.markers.get(k) is not None and r.port.value in net.lined
    )
    return net
