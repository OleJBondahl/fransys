"""The stage 6 connectivity oracle (ROUTE-FIX A): is a net on a page drawn whole, or ends in a Ref?

It reads only the wires, the pins' placed points and the reference plan, so it can check any
router: a pin is joined to another when their points are joined by wires of the net (a vertex
of one wire on a segment of another counts as a join).
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.core import Net, Placement
    from fransys_layout.core.outputs import Routes, Wire
    from fransys_layout.core.values import Ref

XY = tuple[int, int]


def _on(p: XY, a: XY, b: XY) -> bool:
    """P lies on the axis-parallel segment a-b, ends included."""
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def _touches(p: XY, wire: Wire) -> bool:
    """P lies on the wire: a bundle trunk is one wire per lane, a pole's drop ends on its own."""
    return p in wire.points or any(_on(p, a, b) for a, b in pairwise(wire.points))


def _owners(net: Net) -> set[str]:
    """The wire net ids that draw this net: its own, and its bundle's fan."""
    return {net.id, *([f"f:{net.bundle.id}"] if net.bundle else [])}


def _page_pins(placement: Placement, net: Net, page: int) -> dict[tuple[str, str], XY]:
    out: dict[tuple[str, str], XY] = {}
    for pg in (p for p in placement.pages if p.page == page):
        by_sym = {p.sym: p for p in pg.placed}
        for ref in net.pins:
            placed = by_sym.get(ref.sym)
            if placed is not None:
                out.update(
                    {(ref.sym, q.pin): (q.x, q.y) for q in placed.pin_xy if q.pin == ref.pin}
                )
    return out


def _find(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _pieces(
    pins: dict[tuple[str, str], XY],
    wires: Sequence[Wire],
    nodes: Mapping[str, tuple[tuple[str, ...], ...]],
) -> list[set[tuple[str, str]]]:
    """The pins grouped by the wires that join them, and by the symbol node they share."""
    parent = list(range(len(wires)))
    for i, a in enumerate(wires):
        for j in range(i + 1, len(wires)):
            b = wires[j]
            if any(_touches(p, b) for p in a.points) or any(_touches(p, a) for p in b.points):
                parent[_find(parent, i)] = _find(parent, j)
    groups: dict[int, set[tuple[str, str]]] = {}
    lone = -1
    for key, xy in pins.items():
        hit = next((i for i, w in enumerate(wires) if _touches(xy, w)), None)
        root = _find(parent, hit) if hit is not None else lone
        lone -= hit is None
        groups.setdefault(root, set()).add(key)
    pieces: list[set[tuple[str, str]]] = []
    for group in groups.values():
        merged = [p for p in pieces if _same_node(p, group, nodes)]
        for p in merged:
            pieces.remove(p)
            group = group | p  # noqa: PLW2901 -- the group grows by what it shares a node with
        pieces.append(group)
    return pieces


def _same_node(
    a: set[tuple[str, str]],
    b: set[tuple[str, str]],
    nodes: Mapping[str, tuple[tuple[str, ...], ...]],
) -> bool:
    """Some pin of a and some pin of b are two pins of one symbol node (one conductor inside)."""
    return any(
        x[0] == y[0] and any(x[1] in nd and y[1] in nd for nd in nodes.get(x[0], ()))
        for x in a
        for y in b
    )


def connected_or_referenced(  # noqa: PLR0913, PLR0917 -- one per oracle input; a bundle object would be a second shape
    routes: Routes,
    placement: Placement,
    refs: Sequence[Ref],
    net: Net,
    page: int,
    nodes: Mapping[str, tuple[tuple[str, ...], ...]] | None = None,
) -> bool:
    """True when every pin of `net` on `page` is joined by drawn wires, or its piece ends in a Ref.

    A piece ends in a Ref when one of its pins is the pin of a planned end of the net on this page.
    A net with at most one pin on the page has nothing to join. `nodes` maps a symbol id to its
    `Sym.nodes`: two pins of one node are one conductor and need no wire between them.
    """
    pins = _page_pins(placement, net, page)
    wires = [w for pg in routes.pages if pg.page == page for w in pg.wires if w.net in _owners(net)]
    pieces = _pieces(pins, wires, nodes or {})
    if len(pieces) <= 1:
        return True
    referenced = {
        (e.pin.sym, e.pin.pin)
        for r in refs
        if r.net == net.id
        for e in r.ends
        if e.page == page and e.pin is not None
    }
    return all(piece & referenced for piece in pieces)
