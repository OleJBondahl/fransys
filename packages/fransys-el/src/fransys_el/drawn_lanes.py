"""The lanes of a bundle across a cut, joined by their order (READ-LANES, S2b, R1957).

One arrow stands for a bundle; its other lanes run on to the same cut end (RAIL-LANES). A reader pairs the k-th lane
below one read marker with the k-th lane below the next. A foot's net is the model's net of a port its own ink reaches
(`Netlist.net`), never a wire's label. The feet pair only where both sides read the same nets in the same order.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from electrical_symbols import MARKER_SLOT

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from fransys_layout.core import Box
    from fransys_model.kernel import Id
    from fransys_model.layout import Page

    from .drawn_graph import Union
    from .drawn_netlist import PagePart
    from .drawn_references import References

__all__ = ["Lanes", "join_lanes", "lane_chain", "on_flag_edge"]

XY = tuple[int, int]
type _Node = tuple[Id[Page], XY]
_TRUNK = "trunk"  # the layout's only fact for a lane wire (DrawnWire has no role field): a Core candidate
_STEP = 2  # pitches between two lanes of one bundle: a net with no lane leaves a row empty (R3372)
_SHORT = ""  # the net of a piece that holds ports of two nets: already a short, so it joins nothing


@dataclass(frozen=True)
class Lanes:
    """The feet the order check joined, and the feet whose piece holds no port of the page."""

    joined: set[_Node] = field(default_factory=set)
    bare: set[_Node] = field(default_factory=set)


def on_flag_edge(box: Box, at: XY, point: XY) -> bool:
    """True when `point` lies on the flat edge of the flag at `at` (its port) with outline `box` (R3568).

    On the port's x, at the port or strictly in its y span: a point on the outline's end other than the port is off it.
    """
    return point[0] == at[0] and (point == at or box.y < point[1] < box.y + box.h)


def lane_chain(part: PagePart, at: XY, pitch: int) -> set[int]:
    """The rows of the lanes that end at the arrow's x, in a chain of at most two pitches from row `at[1]`: the lanes one arrow stands for (R3372).

    A lane another bundle runs elsewhere on the page, or that stops short of this x, is not in it.
    """
    rows = {end[1] for w in part.drawing.wires if w.style == _TRUNK for end in (w.points[0], w.points[-1]) if end[0] == at[0]}
    chain, grown = {at[1]}, True
    while grown:
        near = {r for r in rows if any(abs(r - row) <= _STEP * pitch for row in chain)} - chain
        chain, grown = chain | near, bool(near)
    return chain


def _feet(part: PagePart, at: XY, pitch: int) -> list[XY]:
    """The end of each lane in the arrow's chain at its x, then each other wire end on its column; each group top to bottom (R903, R1664, R3372).

    A lane that stops short of its arrow has no foot there: it is not read as passing.
    """
    chain = lane_chain(part, at, pitch)
    ends = [(end, wire.style == _TRUNK) for wire in part.drawing.wires for end in (wire.points[0], wire.points[-1]) if end[0] == at[0]]
    lanes = {end for end, trunk in ends if trunk and end[1] in chain}
    return sorted(lanes | {end for end, trunk in ends if not trunk}, key=lambda e: (e not in lanes, e[1], e[0]))


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
    sides: list[tuple[Id[Page], list[tuple[XY, set[str]]]]],
    nets: Mapping[str, str],
    through: Mapping[_Node, str],
    on_ink: Callable[[_Node], bool],
) -> list[tuple[_Node, _Node]]:
    """The feet of the first side paired with those of each later side that read the same nets in the same order, both on the arrow's ink."""
    (page, feet), *rest = sides
    pairs: list[tuple[_Node, _Node]] = []
    for there, others in rest:
        ours, theirs = _order(page, feet, nets, through), _order(there, others, nets, through)
        common = [net for net in ours if net in theirs]
        if common == [net for net in theirs if net in ours]:
            pairs.extend(((page, ours[net]), (there, theirs[net])) for net in common if on_ink((page, ours[net])) and on_ink((there, theirs[net])))
    return pairs


type _Kth = tuple[_Node, set[str]] | None


def _kth(others: list[tuple[Id[Page], list[tuple[XY, set[str]]]]], k: int) -> list[_Kth]:
    """The k-th lane under each other end of a reference, with the ports of its piece; None where an end has no k-th lane."""
    return [((page, feet[k][0]), feet[k][1]) if k < len(feet) else None for page, feet in others]


def _chains(links: Mapping[object, set[object]]) -> dict[object, object]:
    """Each piece with the first piece of its chain: portless lanes linked across arrows, k-th lane to k-th lane, are one chain."""
    out: dict[object, object] = {}
    for start in links:
        todo = [start]
        while todo:
            if (piece := todo.pop()) not in out:
                out[piece] = start
                todo.extend(links[piece])
    return out


def _one_net(read: list[str | None]) -> str | None:
    """The one net a chain's drawn lanes read; None for none, a missing lane or two nets."""
    found = set(read)
    return next(iter(found)) if len(found) == 1 else None


@dataclass(frozen=True)
class _Reader:
    """What reads a foot: the pages, the piece each page's ports are in, the union and the pitch."""

    pages: Mapping[Id[Page], PagePart]
    held: Mapping[Id[Page], Mapping[object, set[str]]]
    union: Union
    pitch: int

    def on_ink(self, node: _Node) -> bool:
        """True when the foot lies on the ink of a reference marker's flat edge (R3541, R3568)."""
        return any(
            MARKER_SLOT in dict(s.slots) and s.outline is not None and on_flag_edge(s.outline, (s.x, s.y), node[1])
            for s in self.pages[node[0]].drawing.symbols
        )

    def feet(self, page: Id[Page], at: XY) -> list[tuple[XY, set[str]]]:
        """The feet of the arrow at `at` with the ports of their pieces."""
        return _read(self.held[page], self.union, page, _feet(self.pages[page], at, self.pitch))

    def targets(self, refs: References) -> dict[_Node, tuple[_Node, list[_Kth]]]:
        """Each portless foot under an arrow whose reference is read at both ends: the arrow, and the k-th lane at its other ends."""
        found: dict[_Node, tuple[_Node, list[_Kth]]] = {}
        for arrows in (a for a in refs.groups.values() if len(a) > 1):
            feet = {arrow: self.feet(*arrow) for arrow in arrows}
            for arrow, mine in feet.items():
                others = [(other[0], f) for other, f in feet.items() if other != arrow]
                found.update({(arrow[0], end): (arrow, _kth(others, k)) for k, (end, ports) in enumerate(mine) if not ports})
        return found

    def passing(self, refs: References, nets: Mapping[str, str]) -> dict[_Node, str]:
        """The feet of a chain of lanes with no port on the page, arrow to arrow, whose drawn lanes at the chain's ends read one net (R2065).

        A chain meets two arrows or more, and each foot has a k-th lane at every other end of its arrow.
        """
        found = self.targets(refs)
        piece = {foot: self.union.find(foot) for foot in found}
        links: dict[object, set[object]] = {p: set() for p in piece.values()}
        for foot, (_, lanes) in found.items():
            for node, _ports in (k for k in lanes if k is not None and k[0] in piece):
                links[piece[foot]].add(piece[node])
                links[piece[node]].add(piece[foot])
        chain = _chains(links)
        arrows: dict[object, set[_Node]] = defaultdict(set)
        read: dict[object, list[str | None]] = defaultdict(list)
        for foot, (arrow, lanes) in found.items():
            arrows[chain[piece[foot]]].add(arrow)
            read[chain[piece[foot]]] += [None if k is None else _net(k[1], nets) for k in lanes if k is None or k[0] not in piece]
        return {foot: net for foot in found if len(arrows[c := chain[piece[foot]]]) > 1 and (net := _one_net(read[c])) is not None}


def join_lanes(union: Union, pages: Mapping[Id[Page], PagePart], refs: References, nets: Mapping[str, str], pitch: int) -> Lanes:
    """Join, across each read reference, the lane feet whose nets stand in one order on both sides; meet the feet a read stub lists (R1957).

    A pair or star side that reads other nets in the other order joins nothing: its feet stay unmet. A stub meets the feet whose
    piece holds a port its text lists. A foot with no port is a fault.
    """
    reader = _Reader(pages, {page: _held(page, part, union) for page, part in pages.items()}, union, pitch)
    read = [[(page, reader.feet(page, at)) for page, at in nodes] for nodes in refs.groups.values()]
    passing = reader.passing(refs, nets)
    pairs = [pair for sides in read if len(sides) > 1 for pair in _pairs(sides, nets, passing, reader.on_ink)]
    listed = {(page, end) for (page, at), ports in refs.stubs.items() for end, held in reader.feet(page, at) if held & ports}
    alone = [[(page, reader.feet(page, at))] for page, at in refs.stubs]
    bare = {(page, end) for side in (*read, *alone) for page, found in side for end, ports in found if not ports} - passing.keys()
    for a, b in pairs:  # after every read: a join moves the roots the readings are keyed by
        union.join(a, b)
    return Lanes({node for pair in pairs for node in pair} | listed | passing.keys(), bare)
