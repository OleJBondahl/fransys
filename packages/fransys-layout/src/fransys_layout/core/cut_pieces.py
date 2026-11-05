"""The cut's piece fact: which pins of a required group one drawn piece holds, read once as connectivity (layout-0508 A21).

A piece is joined to its group by ink, one page's trunk or routed link, a planned arrow, tag or copy pair, or a join wire.
A piece left apart is joined by a reference the loop stands, or ended by a stub.
"""

from __future__ import annotations

from itertools import pairwise, permutations
from typing import TYPE_CHECKING

from .errors import CoreError
from .unionfind import UnionFind
from .values import PinRef, RefKind

if TYPE_CHECKING:
    from collections.abc import Collection, Hashable, Iterable, Mapping, Sequence

    from .flow_values import Attach, Cell, FlowGraph
    from .values import Ref

__all__ = ("components", "hole_pin", "join", "joined", "key", "pairs", "split", "trunked")

type Pair = tuple[PinRef, PinRef]
_PAIR = 2


def key(pin: PinRef) -> str:
    """The union-find key of a pin."""
    return f"{pin.sym}\x00{pin.pin}"


def joined(pairs_: Iterable[Pair]) -> UnionFind:
    """The pins one drawn piece holds, transitively, over `pairs_`."""
    uf = UnionFind()
    for a, b in pairs_:
        uf.union(key(a), key(b))
    return uf


def components(group: Sequence[PinRef], where: Mapping[str, Hashable], piece: UnionFind, *, linked: bool) -> list[list[PinRef]]:
    """The placed pins of `group` in one drawn piece; a link or mate group also joins its pins by a row of a page (CL1, R676).

    A symbol's body joins nothing: each side of a terminal is its own conductor.
    """
    parts: list[list[PinRef]] = []
    for pin in (p for p in group if p.sym in where):
        mine = [pin]
        for part in [q for q in parts if any((linked and where[b.sym] == where[pin.sym]) or piece.same(key(pin), key(b)) for b in q)]:
            mine += part
            parts.remove(part)
        parts.append(mine)
    return parts


def pairs(refs: Sequence[Ref]) -> set[Pair]:
    """The pairs a planned arrow, tag or copy joins: its ends, two by two. A stub joins nothing: it ends a piece."""
    return {pair for r in refs if r.kind is not RefKind.STUB for pair in permutations([e.pin for e in r.ends if e.pin], 2)}


def _sides(attached: Iterable[Attach], where: Mapping[str, int]) -> list[list[PinRef]]:
    """The pins of `attached` per page: the ones a single wire of that page ties."""
    by_page: dict[int, list[PinRef]] = {}
    for a in attached:
        if (page := where.get(a.column or a.pin.sym)) is not None:
            by_page.setdefault(page, []).append(a.pin)
    return list(by_page.values())


def trunked(flow: FlowGraph, where: Mapping[str, int], net_of: Mapping[PinRef, str]) -> set[Pair]:
    """The pairs one page's wire joins besides the ink: a fan's attachments share its trunk, a routed link's ends its wire, a lane its cells.

    A column's lane passes its net from cell to cell: through a cell whose two pins are on one net, and by the lane wire between
    consecutive cells (route_wires `_lane`).
    """
    sides = [s for fan in flow.fans for s in _sides((*fan.drivers, *fan.legs), where)]
    sides += [s for link in flow.cross_links if not link.tagged for s in _sides(link.ends, where)]
    sides += [s for col in flow.columns if col.id in where for lane in col.lanes for s in _laned(lane.cells, net_of)]
    return {pair for side in sides for pair in permutations(side, 2)}


def _laned(cells: Sequence[Cell], net_of: Mapping[PinRef, str]) -> list[list[PinRef]]:
    """The pin pairs a lane joins on its page: a cell's top and bottom pins on one net, and the lane wire between two consecutive cells."""
    pins = [(PinRef(c.sym, c.top_pin) if c.top_pin else None, PinRef(c.sym, c.bottom_pin) if c.bottom_pin else None) for c in cells]
    pairs_ = [(t, b) for t, b in pins] + [(a[1], b[0]) for a, b in pairwise(pins)]
    return [[a, b] for a, b in pairs_ if a and b and a in net_of and net_of[a] == net_of.get(b)]


def split(group: Sequence[PinRef], where: Mapping[str, Hashable], piece: UnionFind, conductors: Collection[Pair]) -> list[list[PinRef]]:
    """The pieces of a required group not drawn whole, [] when whole."""
    linked = not (len(group) == _PAIR and (tuple(group) in conductors or (group[1], group[0]) in conductors))
    parts = components(group, where, piece, linked=linked)
    return parts if len(parts) > 1 or len(group) > sum(map(len, parts)) else []


def hole_pin(part: Sequence[PinRef], far_ends: Collection[Pair], net_of: Mapping[PinRef, str]) -> PinRef:
    """The pin a drawn piece is marked at: its first pin in far-end order wired to a pin outside it (R676), else its first pin with a net.

    The far ends come in `stub_far_order`, so the pin does not follow the order of the group's pins (R1717).
    """
    held = [a for a, _ in far_ends if a in part and a in net_of]
    outside = [a for a, b in far_ends if a in part and a in net_of and b not in part]
    if (pin := next(iter(outside), None) or next(iter(held), None) or next((p for p in part if p in net_of), None)) is None:
        msg = f"cut: a pin of a required group has no ink and no reference: {part[0].sym} {part[0].pin}"
        raise CoreError(msg)
    return pin


def join(part: Sequence[PinRef], rest: Sequence[PinRef], far_ends: Collection[Pair], net_of: Mapping[PinRef, str]) -> tuple[str, Pair]:
    """The pair the loop tags to join `part` to `rest`: its first undrawn conductor into `rest`, else its marked pin and the rest's."""
    pair = next(((a, b) for a, b in far_ends if a in part and b in rest), (hole_pin(part, far_ends, net_of), hole_pin(rest, far_ends, net_of)))
    return net_of[pair[0]], pair
