"""Stage 5, y: a trunk's y lies outside every foreign hard box whose x-range meets its span.

A foreign cell is a free one: no trunk of the page attaches to its symbol. The base solution says
which hold their trunk's y; each is pushed under an `above` trunk, over a `below` one, and the
solution is taken again until none holds a trunk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import cell_anchor
from .pack import cell_node
from .pack_sep import hard_soft
from .place_trunk import trunk_node

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from .constraints import Graph
    from .place_env import PageEnv
    from .place_levels import Span
    from .values import Box

ROUNDS = 8


def _held(env: PageEnv) -> frozenset[str]:
    """The symbols some trunk of the page attaches to: each stands at its own trunk's line."""
    return frozenset(a.pin.sym for f in env.flow.fans for a in (*f.drivers, *f.legs))


def _foreign(
    env: PageEnv, x: Mapping[str, int], y: Mapping[str, int], row: int
) -> Iterator[tuple[str, int, int, Box]]:
    """(node, left, top, hard box) of every free cell of the row."""
    own = _held(env)
    for col in env.plan.rows[row].columns:
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
                left = x[f"col:{col}"] + pc.offsets[lane] - cell_anchor(sym, cell)[0] + hard.x
                yield node, left, y[node] + hard.y, hard


def _pushes(
    env: PageEnv, x: Mapping[str, int], y: Mapping[str, int], span: Span
) -> list[tuple[str, str, int]]:
    """(from node, to node, distance) per foreign hard box that holds the span's trunk line."""
    if span.x0 == span.x1:
        return []
    trunk = trunk_node(span.fan, span.row)
    line, wire = y[trunk], env.options.wire_min
    out = []
    for node, left, top, hard in _foreign(env, x, y, span.row):
        if left < span.x1 and span.x0 < left + hard.w and top <= line <= top + hard.h:
            if span.side == "above":
                out.append((trunk, node, wire - hard.y))
            else:
                out.append((node, trunk, hard.y + hard.h + wire))
    return out


def clear_foreign(g: Graph, env: PageEnv, x: Mapping[str, int], spans: Sequence[Span]) -> None:
    """Add the edges that take every trunk line out of the foreign hard boxes its span meets."""
    seen: set[tuple[str, str]] = set()
    for _ in range(ROUNDS):
        y = g.solve()
        if y is None:
            return
        fresh = [p for s in spans for p in _pushes(env, x, y, s) if (p[0], p[1]) not in seen]
        if not fresh:
            return
        for a, b, d in fresh:
            seen.add((a, b))
            g.after(a, b, d)
