"""Stage 5, y: a trunk's lanes lie outside every foreign hard box their drawn band meets.

A cell is foreign to a trunk when the trunk's fan does not attach to its symbol, even if another
fan's trunk holds it.
The base solution says which hold a lane's y. The page's hard order decides the side of each: a box it holds
below the trunk is pushed under the trunk, one it holds above is pushed over it, and the trunk's side decides only
a box the order does not hold. The solution is taken again until none holds a trunk.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .clearance import Keep, clear, fan_own, footprint_keeps
from .geometry import cell_anchor
from .node_names import col_node
from .pack import cell_node
from .pack_sep import hard_soft
from .place_lanes import lane_segments
from .place_levels import _below, _reachable
from .place_trunk import trunk_node
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .constraints import Graph
    from .flow_values import Cell, Fan
    from .place_env import PageEnv
    from .place_levels import Span

ROUNDS = 8


def _fan(env: PageEnv, fan: str) -> Fan:
    return next(f for f in env.flow.fans if f.id == fan)


def _foreign(env: PageEnv, x: Mapping[str, int], span: Span, rows: Iterable[int]) -> Iterator[Keep]:
    """The hard-box keeps of every cell of the rows its fan does not attach to."""
    return cell_keeps(env, x, rows, fan_own(_fan(env, span.fan)))


def cell_keeps(env: PageEnv, x: Mapping[str, int], rows: Iterable[int], own: AbstractSet[str]) -> Iterator[Keep]:
    """The hard-box keeps of every cell of `rows` whose symbol is not in `own`."""
    for col in (c for row in rows for c in env.plan.rows[row].columns):
        pc = env.pcs[col]
        for lane, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                if cell.sym not in own:
                    box = _hard_box(env, x[col_node(col)] + pc.offsets[lane], cell)
                    yield from footprint_keeps(((cell_node(pc.id, lane, i), cell.sym),), box)


def _hard_box(env: PageEnv, origin: int, cell: Cell) -> Box:
    """The cell footprint at its column lane `origin`, hangings included: a foreign trunk keeps clear of a marker."""
    sym = env.syms[cell.sym]
    _, hard_and_soft = hard_soft(
        sym, cell, in_row=cell.sym in env.in_row, tag_stagger=env.options.tag_stagger
    )  # the soft box holds the hangings (stub markers)
    return Box(origin - cell_anchor(sym, cell)[0] + hard_and_soft.x, hard_and_soft.y, hard_and_soft.w, hard_and_soft.h)


def _crossings(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int], span: Span) -> list[tuple[str, str, int]]:
    """Pushes that take a trunk's drops out of the foreign boxes of the rows between it and its own.

    An `above` trunk lies below each earlier row's box a drop passes, a `below` one above a later.
    """
    trunk, wire, above = trunk_node(span.fan, span.row), env.options.wire_min, span.side == "above"
    rows = range(span.row) if above else range(span.row + 1, len(env.plan.rows))
    keeps = tuple(_foreign(env, x, span, rows))
    tops = [y[k.node] + k.box.y for k in keeps]
    if not keeps:
        return []
    lo, hi = min(tops), max(t + k.box.h for t, k in zip(tops, keeps, strict=True))
    hit = {k.node for d in (*span.drivers, *span.legs) for k in clear(Box(d, lo, 0, hi - lo), keeps, y)}
    out = []
    for k in (k for k in keeps if k.node in hit):
        top = y[k.node] + k.box.y
        if (above and y[trunk] < top + k.box.h + wire) or (not above and y[trunk] > top - wire):
            out.append(_edge(trunk, k.node, _gap(k.box, wire, 0, trunk_above=not above), trunk_above=not above))
    return out


def _gap(box: Box, wire: int, dy: int, *, trunk_above: bool) -> int:
    """How far the box stands under the trunk line (trunk above it), or over it, with `wire` between."""
    return wire - box.y + dy if trunk_above else box.y + box.h + wire - dy


def _edge(trunk: str, node: str, d: int, *, trunk_above: bool) -> tuple[str, str, int]:
    return (trunk, node, d) if trunk_above else (node, trunk, d)


def hard_order(g: Graph, trunk: str) -> dict[str, int]:
    """Per node of `g`: 1 when the hard order holds `trunk` above it, -1 when below it, 0 when it holds neither."""
    below = _below(g)
    above: defaultdict[str, set[str]] = defaultdict(set)
    for a, targets in below.items():
        for b in targets:
            above[b].add(a)
    root = g.uf.find(trunk)[0]
    down, up = _reachable(below, root), _reachable(above, root)
    held = {n: g.uf.find(n)[0] for n in g.nodes}
    return {n: 0 if r == root else 1 if r in down else -1 if r in up else 0 for n, r in held.items()}


def _pushes(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int], span: Span, held: Mapping[str, int]) -> list[tuple[str, str, int]]:
    """(from node, to node, distance) per foreign hard box that a lane of the span's band meets."""
    if span.x0 == span.x1:
        return []
    trunk, wire = trunk_node(span.fan, span.row), env.options.wire_min
    out = _crossings(env, x, y, span)
    keeps = tuple(_foreign(env, x, span, [span.row]))
    segs = [s for s in lane_segments(env, x, _fan(env, span.fan), span.row) if s]
    over = {k.node: (held.get(k.node, 0) or (1 if span.side == "above" else -1)) > 0 for k in keeps}
    need: dict[str, int] = {}
    for dy, x0, x1 in segs:
        for k in clear(Box(x0, y[trunk] + dy, x1 - x0, 0), keeps, y):
            d = _gap(k.box, wire, dy, trunk_above=over[k.node])
            need[k.node] = max(need.get(k.node, d), d)  # the lane that needs the farthest push counts
    out.extend(_edge(trunk, n, d, trunk_above=over[n]) for n, d in need.items())
    return out


def _cells(pairs: AbstractSet[tuple[str, str]]) -> frozenset[str]:
    return frozenset(n for pair in pairs for n in pair if n.startswith("cell:"))


def clear_foreign(g: Graph, env: PageEnv, x: Mapping[str, int], spans: Sequence[Span]) -> frozenset[str]:
    """Add the edges that take every trunk line out of the foreign hard boxes its span meets.

    Returns the nodes of the foreign cells it pushed a trunk away from.
    """
    seen: set[tuple[str, str]] = set()
    for _ in range(ROUNDS):
        y = g.solve()
        if y is None:
            return _cells(seen)
        fresh = [p for s in spans for p in _pushes(env, x, y, s, hard_order(g, trunk_node(s.fan, s.row))) if (p[0], p[1]) not in seen]
        if not fresh:
            return _cells(seen)
        for a, b, d in fresh:
            seen.add((a, b))
            g.after(a, b, d)
    return _cells(seen)
