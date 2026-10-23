"""Stage 5, y: a trunk's y lies outside every foreign hard box whose x-range meets its span.

A cell is foreign to a trunk when the trunk's fan does not attach to its symbol, even if another
fan's trunk holds it. The base solution says which hold a trunk's y; each is pushed under an
`above` trunk, over a `below` one, and the solution is taken again until none holds a trunk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import cell_anchor
from .node_names import col_node
from .pack import cell_node
from .pack_sep import hard_soft
from .place_trunk import trunk_node

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .constraints import Graph
    from .place_env import PageEnv
    from .place_levels import Span
    from .values import Box

ROUNDS = 8


def _own(env: PageEnv, fan: str) -> frozenset[str]:
    """The symbols the fan attaches to: each stands at the fan's own trunk line."""
    return frozenset(a.pin.sym for f in env.flow.fans if f.id == fan for a in (*f.drivers, *f.legs))


def _foreign(
    env: PageEnv, x: Mapping[str, int], y: Mapping[str, int], span: Span, rows: Iterable[int]
) -> Iterator[tuple[str, int, int, Box]]:
    """(node, left, top, hard box) of every cell of the rows its fan does not attach to."""
    own = _own(env, span.fan)
    for col in (c for row in rows for c in env.plan.rows[row].columns):
        pc = env.pcs[col]
        for lane, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                if cell.sym in own:
                    continue
                sym = env.syms[cell.sym]
                hard, _ = hard_soft(
                    sym, cell, in_row=cell.sym in env.in_row, tag_stagger=env.options.tag_stagger
                )
                node = cell_node(pc.id, lane, i)
                left = x[col_node(col)] + pc.offsets[lane] - cell_anchor(sym, cell)[0] + hard.x
                yield node, left, y[node] + hard.y, hard


def _crossings(
    env: PageEnv, x: Mapping[str, int], y: Mapping[str, int], span: Span
) -> list[tuple[str, str, int]]:
    """Pushes that take a trunk's drops out of the foreign boxes of the rows between it and its own.

    An `above` trunk lies below each earlier row's box a drop passes, a `below` one above a later.
    """
    trunk, wire, above = trunk_node(span.fan, span.row), env.options.wire_min, span.side == "above"
    drops = (*span.drivers, *span.legs)
    rows = range(span.row) if above else range(span.row + 1, len(env.plan.rows))
    out = []
    for node, left, top, hard in _foreign(env, x, y, span, rows):
        if not any(left <= d <= left + hard.w for d in drops):
            continue
        if above and y[trunk] < top + hard.h + wire:
            out.append((node, trunk, hard.y + hard.h + wire))
        elif not above and y[trunk] > top - wire:
            out.append((trunk, node, wire - hard.y))
    return out


def _pushes(
    env: PageEnv, x: Mapping[str, int], y: Mapping[str, int], span: Span
) -> list[tuple[str, str, int]]:
    """(from node, to node, distance) per foreign hard box that holds the span's trunk line."""
    if span.x0 == span.x1:
        return []
    trunk = trunk_node(span.fan, span.row)
    line, wire = y[trunk], env.options.wire_min
    out = _crossings(env, x, y, span)
    for node, left, top, hard in _foreign(env, x, y, span, [span.row]):
        if left < span.x1 and span.x0 < left + hard.w and top <= line <= top + hard.h:
            if span.side == "above":
                out.append((trunk, node, wire - hard.y))
            else:
                out.append((node, trunk, hard.y + hard.h + wire))
    return out


def _cells(pairs: AbstractSet[tuple[str, str]]) -> frozenset[str]:
    return frozenset(n for pair in pairs for n in pair if n.startswith("cell:"))


def clear_foreign(
    g: Graph, env: PageEnv, x: Mapping[str, int], spans: Sequence[Span]
) -> frozenset[str]:
    """Add the edges that take every trunk line out of the foreign hard boxes its span meets.

    Returns the nodes of the foreign cells it pushed a trunk away from.
    """
    seen: set[tuple[str, str]] = set()
    for _ in range(ROUNDS):
        y = g.solve()
        if y is None:
            return _cells(seen)
        fresh = [p for s in spans for p in _pushes(env, x, y, s) if (p[0], p[1]) not in seen]
        if not fresh:
            return _cells(seen)
        for a, b, d in fresh:
            seen.add((a, b))
            g.after(a, b, d)
    return _cells(seen)
