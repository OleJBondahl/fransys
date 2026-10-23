"""The netlist the `Drawing`s of a set draw, read from geometry alone (DRAWN-NETLIST, el-0052).

A page's wires, junction dots and port points give a strict point graph (`page_graph`); a reference
marker joins its partner's page node. A port is reached when a wire end, a dot or a marker stands
on its point. Net identity is the model's: the first port's value of `net_of`, never a wire label.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from electrical_symbols import power_symbol_key
from fransys_layout.drawing import port_points
from fransys_model.derive import link_groups, net_of
from fransys_model.layout import StarKind

from .drawn_graph import PageGraph, Union, page_graph
from .drawn_ids import symbol_id
from .placement_ids import pin_names, symbol_ids

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from electrical_symbols import Library
    from fransys_layout.drawing import Drawing, DrawnSymbol
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import LinkMarker, Page
    from fransys_model.vocab import Port

    from .placement_kit import SymbolKit

__all__ = ["Netlist", "PagePart", "drawn_netlist"]

XY = tuple[int, int]
Node = tuple[object, XY]
_DOT = "junction-dot"


@dataclass(frozen=True)
class PagePart:
    """One page: its drawing, port points (port value to point), graph and node set."""

    drawing: Drawing
    ports: dict[str, XY]
    graph: PageGraph
    nodes: frozenset[XY]


@dataclass(frozen=True)
class Netlist:
    """The pages' parts, one union of all nodes, and each marker's node by record id suffix.

    `owner` is the drawn symbol of each port: pins of one symbol are joined by the symbol itself.
    """

    pages: dict[Id[Page], PagePart]
    union: Union
    placed: dict[str, tuple[Id[Page], XY]]
    ids: dict[str, Id[Port]]
    markers: dict[str, tuple[Id[Page], XY] | None]
    records: dict[str, LinkMarker]
    linked: dict[str, str] = field(default_factory=dict)
    owner: dict[str, str] = field(default_factory=dict)

    def reached(self, port: str) -> bool:
        """True when a wire end, a dot or a marker stands on the port's point, or on its link's."""
        page, at = self.placed[port]
        return at in self.pages[page].nodes or port in self.linked

    def root(self, port: str) -> object:
        """The component of the port's point (of its linked port when it has no wire)."""
        page, at = self.placed[self.linked.get(port, port)]
        return self.union.find((page, at))

    def net(self, model: Model, port: str) -> str:
        """The physical net of the port: its first port's value."""
        found = net_of(model, self.ids[port])
        return found.ports[0].value if found else port


def is_marker(symbol: DrawnSymbol) -> bool:
    """True for a reference marker: it draws a port's net and is no junction dot."""
    return bool(symbol.ports and symbol.net and symbol.key != _DOT)


def _pin_ports(
    model: Model, kit: SymbolKit
) -> tuple[dict[str, dict[str, str]], dict[str, Id[Port]]]:
    """Port value by (drawn symbol id, symbol port name), and each port's Id by value."""
    by: dict[str, dict[str, str]] = defaultdict(dict)
    ids = {}
    for port, pin in pin_names(model, kit, symbol_ids(model, kit)).items():
        by[symbol_id("layout", "core", "drawn_symbol", pin.sym)][pin.pin] = port.value
        ids[port.value] = port
    return by, ids


def _port_map(
    drawing: Drawing, by: Mapping[str, Mapping[str, str]], library: Library
) -> dict[str, XY]:
    found = {}
    for symbol in drawing.symbols:
        if names := by.get(symbol.id):
            for at, pin in port_points(symbol, library):
                if pin in names:
                    found[names[pin]] = at
    return found


def _part(drawing: Drawing, by: Mapping[str, Mapping[str, str]], library: Library) -> PagePart:
    ports = _port_map(drawing, by, library)
    dots = {(s.x, s.y) for s in drawing.symbols if s.key == _DOT}
    pitch = round(library.grid.wire_pitch)
    graph = page_graph([w.points for w in drawing.wires], dots, set(ports.values()), {}, pitch)
    nodes = {p for edge in graph.edges for p in edge}
    nodes.update(
        (s.x, s.y) for s in drawing.symbols if is_marker(s) and (s.x, s.y) in ports.values()
    )
    return PagePart(drawing, ports, graph, frozenset(nodes))


def _marker_nodes(pages: Mapping[Id[Page], PagePart]) -> dict[str, tuple[Id[Page], XY] | None]:
    """Each marker's (page, point) by the text of its record id; None when it joins nothing."""
    found: dict[str, tuple[Id[Page], XY] | None] = {}
    for page, part in pages.items():
        for symbol in part.drawing.symbols:
            if is_marker(symbol):
                at = (symbol.x, symbol.y)
                found[symbol.id.rpartition(":")[2]] = (page, at) if at in part.nodes else None
    return found


def _join(union: Union, pages: Mapping[Id[Page], PagePart]) -> None:
    for page, part in pages.items():
        for edge in part.graph.edges:
            a, b = tuple(edge)
            union.join((page, a), (page, b))


def _ends_at(part: PagePart, x: int) -> dict[str, XY]:
    """The end point of each net's wire that ends on column x: the lanes that reach a cut end."""
    found: dict[str, XY] = {}
    for wire in part.drawing.wires:
        for at in (wire.points[0], wire.points[-1]):
            if wire.net and at[0] == x:
                found.setdefault(wire.net, at)
    return found


def _lanes(
    union: Union,
    pages: Mapping[Id[Page], PagePart],
    markers: Mapping[str, tuple[Id[Page], XY] | None],
    records: Mapping[str, LinkMarker],
) -> None:
    """Join, across each reference (a pair or a star), the lanes of a bundle that reach its markers.

    One arrow stands for the bundle; its other lanes run on to the same cut end (RAIL-LANES), each
    to be joined with the same net's end at the reference's other markers.
    """
    groups: dict[str, list[tuple[Id[Page], XY]]] = defaultdict(list)
    for key, node in markers.items():
        record = records.get(key)
        if node is not None and record is not None and record.star is not StarKind.OFF:
            star = record.star
            head = {StarKind.REF: key, StarKind.BRANCH: record.partner.value}.get(star)
            groups[head or min(key, record.partner.value)].append(node)
    for nodes in groups.values():
        first: dict[str, tuple[Id[Page], XY]] = {}
        for page, at in nodes:
            for net, end in _ends_at(pages[page], at[0]).items():
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


def _link(net: Netlist, model: Model) -> None:
    """Join the reached ports of each link group (a terminal's sides); the rest ride on them."""
    for group in link_groups(model, lambda role: role.joins_net):
        seen = [p.value for p in group.ports if p.value in net.placed]
        held = [p for p in seen if net.reached(p)]
        for port in held[1:]:
            net.union.join(net.placed[held[0]], net.placed[port])
        net.linked.update(
            dict.fromkeys((p for p in seen if p not in held), held[0]) if held else ()
        )


def _power(net: Netlist, model: Model) -> None:
    """Join the reached ports of one net that carry a power symbol: a rail is one net."""
    keys = {power_symbol_key(kind) for kind in ("supply", "ground", "pe")}
    first: dict[str, str] = {}
    for part in net.pages.values():
        for symbol in part.drawing.symbols:
            for port in symbol.ports if symbol.key in keys else ():
                if port in net.placed and net.reached(port):
                    head = first.setdefault(net.net(model, port), port)
                    net.union.join(net.placed[head], net.placed[port])


def drawn_netlist(
    model: Model,
    kit: SymbolKit,
    drawings: Mapping[Id[Page], Drawing],
    links: Iterable[LinkMarker] | Sequence[LinkMarker],
    library: Library,
) -> Netlist:
    """The `Netlist` of `drawings`; `links` are the marker records the drawings stand for."""
    by, ids = _pin_ports(model, kit)
    pages = {page: _part(drawing, by, library) for page, drawing in drawings.items()}
    union = Union()
    _join(union, pages)
    records = {m.id.value: m for m in links}
    markers = _marker_nodes(pages)
    _pair(union, markers, records)
    _lanes(union, pages, markers, records)
    placed = {v: (page, at) for page, p in pages.items() for v, at in p.ports.items()}
    owner = {port: sid for sid, pins in by.items() for port in pins.values()}
    found = Netlist(pages, union, placed, ids, markers, records, owner=owner)
    _link(found, model)
    _power(found, model)
    return found
