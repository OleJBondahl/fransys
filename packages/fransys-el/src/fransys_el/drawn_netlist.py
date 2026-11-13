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
    port_function,
    set_unit,
)
from fransys_model.layout import DrawingSet, Page, StarKind, layout_of

from .drawn_graph import Union
from .drawn_identity_marks import declared_marks
from .drawn_ids import core_symbol_id, symbol_id
from .drawn_lanes import Lanes, join_lanes
from .drawn_power import POWER_KEYS, join_power, port_nets
from .drawn_references import join_references
from .placement_ids import pin_names, symbol_ids
from .placement_joins import node_joins

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.core import PinRef
    from fransys_layout.drawing import Drawing, DrawnSymbol
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
    """The pages' parts, one union of all nodes, each port's drawn points (a copy adds one) and the node of each marker read back, by record id.

    `joins` are the port pairs of a link that stand at one node of one symbol (`node_joins`); P1 of CP-S2c-2 reads them too.
    """

    pages: dict[Id[Page], PagePart]
    union: Union
    placed: dict[str, tuple[tuple[Id[Page], XY], ...]]
    ids: dict[str, Id[Port]]
    markers: dict[str, tuple[Id[Page], XY] | None]
    records: dict[str, LinkMarker]
    joins: tuple[tuple[Id[Port], Id[Port]], ...] = ()
    live: set[object] = field(default_factory=set)
    lined: dict[str, str] = field(default_factory=dict)
    stub_lines: set[tuple[Id[Page], str]] = field(default_factory=set)
    home: dict[str, frozenset[Id[Page]]] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)
    texted: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)  # ports of a set whose layout failed: no drawing, not expected drawn (KI-779)
    lanes: Lanes = field(default_factory=Lanes)
    nets: dict[str, str] = field(default_factory=dict)
    marks: dict[str, str] = field(default_factory=dict)
    unreadable: tuple[tuple[Id[Page], Id[LinkMarker], str], ...] = ()

    def reached(self, port: str) -> bool:
        """True when a wire end, a dot or a marker stands on a point of the port."""
        return any(at in self.pages[page].nodes for page, at in self.placed[port])

    def at_home(self, port: str) -> list[tuple[Id[Page], XY]]:
        """The port's drawn points on the pages of its own scope: its copies are left out."""
        return [(page, at) for page, at in self.placed.get(port, ()) if page in self.home.get(port, ())]

    def roots(self, port: str) -> set[object]:
        """The components with a wire end, a dot or a marker that hold a point of the port."""
        return {self.union.find(place) for place in self.placed[port]} & self.live

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


def _join(pages: Mapping[Id[Page], PagePart]) -> Union:
    """One union of every page's wire edges."""
    union = Union()
    for page, part in pages.items():
        for edge in part.graph.edges:
            a, b = tuple(edge)
            union.join((page, a), (page, b))
    return union


def _bridges(model: Model) -> tuple[tuple[Id[Port], Id[Port]], ...]:
    """The two ports of each declared bridge: the terminal table joins them, they draw no ink (R1009, R2079 G2)."""
    held = (c for cs in build_indexes(model).conductors_by_port.values() for c in cs if is_bridge(model, c))
    return tuple(dict.fromkeys(conductor_ends(model, c) for c in held))


def _link(net: Netlist) -> None:
    """Join, page by page, the two points of each joined pair: the symbol holds its pins at one node (R685, CP-S2c-1)."""
    for a, b in net.joins:
        there = dict(net.placed.get(b.value, ()))
        for page, at in net.placed.get(a.value, ()):
            if page in there:
                net.union.join((page, at), (page, there[page]))


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
    pages = {page: _part(drawing, by, library) for page, drawing in drawings.items()}
    union = _join(pages)
    records = {m.id.value: m for m in links}
    read = join_references(model, pages, library, union)
    placed = _placed(pages)
    nets = port_nets(model, ids)
    lanes = join_lanes(union, pages, read, nets, library.grid.wire_pitch)
    found = Netlist(
        pages,
        union,
        placed,
        ids,
        read.markers,
        records,
        home=_homes(model, ids, placed),
        owners={p.value: sym for sym, pins in by.items() for p in pins.values()},
        lanes=lanes,
        nets=nets,
        marks=declared_marks(drawings, by, library),
        unreadable=read.faults,
        joins=(*node_joins(model, kit, library, link_groups(model, lambda role: role.joins_net)), *_bridges(model)),
    )
    _link(found)
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
