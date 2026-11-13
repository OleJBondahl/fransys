"""The lanes of a bundle across a cut, joined by their order (READ-LANES, S2b, R1957).

One arrow stands for a bundle; its other lanes run on to the same cut end (RAIL-LANES). A reader pairs the k-th lane
below one read marker with the k-th lane below the next. A foot's net is the model's net of a port its own ink reaches
(`Netlist.net`), never a wire's label. The feet pair only where both sides read the same nets in the same order.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.kernel import Id
    from fransys_model.layout import Page

    from .drawn_graph import Union
    from .drawn_netlist import PagePart
    from .drawn_references import References

__all__ = ["Lanes", "join_lanes", "lane_chain"]

XY = tuple[int, int]
type _Node = tuple[Id[Page], XY]
_TRUNK = "trunk"  # the layout's only fact for a lane wire (DrawnWire has no role field): a Core candidate
_SHORT = ""  # the net of a piece that holds ports of two nets: already a short, so it joins nothing


@dataclass(frozen=True)
class Lanes:
    """The feet the order check joined, and the feet whose piece holds no port of the page."""

    joined: set[_Node] = field(default_factory=set)
    bare: set[_Node] = field(default_factory=set)


def lane_chain(part: PagePart, y: int, pitch: int) -> set[int]:
    """The rows of the trunk lanes one pitch apart in a chain from row `y`: the lanes one arrow stands for (R903)."""
    rows = {w.points[0][1] for w in part.drawing.wires if w.style == _TRUNK}
    chain, grown = {y}, True
    while grown:
        near = {r for r in rows if any(abs(r - row) <= pitch for row in chain)} - chain
        chain, grown = chain | near, bool(near)
    return chain


def _feet(part: PagePart, at: XY, pitch: int) -> list[XY]:
    """The nearest end of each lane of the arrow's trunk, then each other wire end on its column; each group top to bottom (R903, R1664)."""
    chain = lane_chain(part, at[1], pitch)
    lanes: set[XY] = set()
    for wire in part.drawing.wires:
        first, last = wire.points[0], wire.points[-1]
        if wire.style == _TRUNK and first[1] in chain:
            lanes.add(first if abs(first[0] - at[0]) <= abs(last[0] - at[0]) else last)
    ends = {
        end
        for wire in part.drawing.wires
        for end in (wire.points[0], wire.points[-1])
        if end[0] == at[0] and (wire.style != _TRUNK or end[1] in chain)
    }
    return sorted(lanes | ends, key=lambda e: (e not in lanes, e[1], e[0]))


def _held(page: Id[Page], part: PagePart, union: Union) -> dict[object, set[str]]:
    """The ports of `page`, by the piece that holds them."""
    held: dict[object, set[str]] = defaultdict(set)
    for port, at in part.ports.items():
        held[union.find((page, at))].add(port)
    return held


def _read(held: Mapping[object, set[str]], union: Union, page: Id[Page], feet: Iterable[XY]) -> list[tuple[XY, set[str]]]:
    """Each foot with the ports its piece holds on the page."""
    return [(end, held.get(union.find((page, end)), set())) for end in feet]


def _net(ports: set[str], nets: Mapping[str, str]) -> str | None:
    """The one net of `ports`: None for none (a bare foot) or two (a short, already found)."""
    found = {nets[p] for p in ports}
    return next(iter(found)) if len(found) == 1 else None


def _order(page: Id[Page], feet: list[tuple[XY, set[str]]], nets: Mapping[str, str], through: Mapping[_Node, str]) -> dict[str, XY]:
    """The first foot of each net, top to bottom; a passing lane's foot has the net of its arrows."""
    found: dict[str, XY] = {}
    for end, ports in feet:
        if (net := through.get((page, end)) or _net(ports, nets)) is not None:
            found.setdefault(net, end)
    return found


def _pairs(
    sides: list[tuple[Id[Page], list[tuple[XY, set[str]]]]], nets: Mapping[str, str], through: Mapping[_Node, str]
) -> list[tuple[_Node, _Node]]:
    """The feet of the first side paired with the feet of each later side that read the same nets in the same order."""
    (page, feet), *rest = sides
    pairs: list[tuple[_Node, _Node]] = []
    for there, others in rest:
        ours, theirs = _order(page, feet, nets, through), _order(there, others, nets, through)
        common = [net for net in ours if net in theirs]
        if common == [net for net in theirs if net in ours]:
            pairs.extend(((page, ours[net]), (there, theirs[net])) for net in common)
    return pairs


def _kth(others: list[list[tuple[XY, set[str]]]], k: int, nets: Mapping[str, str]) -> str | None:
    """The one net of the k-th lane under every other end of a reference; None when one has no k-th lane, no port there, or they differ."""
    found = {_net(feet[k][1], nets) if k < len(feet) else None for feet in others}
    return next(iter(found)) if len(found) == 1 else None


@dataclass(frozen=True)
class _Reader:
    """What reads a foot: the pages, the piece each page's ports are in, the union and the pitch."""

    pages: Mapping[Id[Page], PagePart]
    held: Mapping[Id[Page], Mapping[object, set[str]]]
    union: Union
    pitch: int

    def feet(self, page: Id[Page], at: XY) -> list[tuple[XY, set[str]]]:
        """The feet of the arrow at `at` with the ports of their pieces."""
        return _read(self.held[page], self.union, page, _feet(self.pages[page], at, self.pitch))

    def targets(self, refs: References, nets: Mapping[str, str]) -> dict[_Node, tuple[_Node, str | None]]:
        """Each portless foot under an arrow whose reference is read at both ends: the arrow, and the net of the k-th lane at its other ends."""
        found: dict[_Node, tuple[_Node, str | None]] = {}
        for arrows in (a for a in refs.groups.values() if len(a) > 1):
            feet = {arrow: self.feet(*arrow) for arrow in arrows}
            for arrow, mine in feet.items():
                others = [f for other, f in feet.items() if other != arrow]
                found.update({(arrow[0], end): (arrow, _kth(others, k, nets)) for k, (end, ports) in enumerate(mine) if not ports})
        return found

    def passing(self, refs: References, nets: Mapping[str, str]) -> dict[_Node, str]:
        """The feet of a lane between two arrows with no port on the page, each arrow read at both ends and the lane there of one net (R2065)."""
        by_piece: dict[object, list[tuple[_Node, _Node, str | None]]] = defaultdict(list)
        for foot, (arrow, net) in self.targets(refs, nets).items():
            by_piece[self.union.find(foot)].append((foot, arrow, net))
        return {
            foot: lane[0][2]
            for lane in by_piece.values()
            if len({arrow for _, arrow, _ in lane}) > 1 and len({net for *_, net in lane}) == 1 and lane[0][2] is not None
            for foot, _, _ in lane
        }


def join_lanes(union: Union, pages: Mapping[Id[Page], PagePart], refs: References, nets: Mapping[str, str], pitch: int) -> Lanes:
    """Join, across each read reference, the lane feet whose nets stand in one order on both sides; meet the feet a read stub lists (R1957).

    A pair or star side that reads other nets in the other order joins nothing: its feet stay unmet. A stub meets the feet whose
    piece holds a port its text lists. A foot with no port is a fault.
    """
    reader = _Reader(pages, {page: _held(page, part, union) for page, part in pages.items()}, union, pitch)
    read = [[(page, reader.feet(page, at)) for page, at in nodes] for nodes in refs.groups.values()]
    passing = reader.passing(refs, nets)
    pairs = [pair for sides in read if len(sides) > 1 for pair in _pairs(sides, nets, passing)]
    listed = {(page, end) for (page, at), ports in refs.stubs.items() for end, held in reader.feet(page, at) if held & ports}
    alone = [[(page, reader.feet(page, at))] for page, at in refs.stubs]
    bare = {(page, end) for side in (*read, *alone) for page, found in side for end, ports in found if not ports} - passing.keys()
    for a, b in pairs:  # after every read: a join moves the roots the readings are keyed by
        union.join(a, b)
    return Lanes({node for pair in pairs for node in pair} | listed | passing.keys(), bare)
