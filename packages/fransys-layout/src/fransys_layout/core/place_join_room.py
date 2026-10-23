"""Stage 5, join room: the y step above a cell that a folded lane's foot join runs to.

A foot join wires the last cell of a member lane to a cell in another lane of its column. Every
net between the two symbols whose pins differ in x needs a turn row between them, as the jogs
between two cells do (`place_room`; SHORTS-ROUTE, layout-0381). The step is
`grid * (levels + jog_lanes)` over those nets, keyed as `place_room`'s steps are. It is reserved
only where the join's stair would have no row; every other join keeps its bend (R456).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from .geometry import pin_xy, stair_room
from .intervals import levels
from .pack import cell_node

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .place_env import PageEnv
    from .place_room import Step
    from .values import Cell


class _End(NamedTuple):
    node: str
    cell: Cell
    pin: str | None


def _spans(env: PageEnv, origin: Mapping[str, int], a: Cell, b: Cell) -> list[tuple[int, int]]:
    """The x span of each net pin pair between two cells' symbols whose pins differ in x."""
    out = []
    for net in env.problem.nets:
        for ra in (r for r in net.pins if r.sym == a.sym):
            for rb in (r for r in net.pins if r.sym == b.sym):
                xa = origin[a.sym] + pin_xy(env.syms[a.sym], a, ra.pin)[0]
                xb = origin[b.sym] + pin_xy(env.syms[b.sym], b, rb.pin)[0]
                if xa != xb:
                    out.append((min(xa, xb), max(xa, xb)))
    return out


def _no_row(env: PageEnv, y: Mapping[str, int], top: _End, bottom: _End) -> bool:
    """True when the join's two pins stand one grid apart in y, so its stair has room 0."""
    if top.pin is None or bottom.pin is None:
        return False
    yt = y[top.node] + pin_xy(env.syms[top.cell.sym], top.cell, top.pin)[1]
    yb = y[bottom.node] + pin_xy(env.syms[bottom.cell.sym], bottom.cell, bottom.pin)[1]
    dy = abs(yt - yb)
    return dy > 0 and stair_room(0, dy, env.options.wiring_grid) < 1


def join_rooms(env: PageEnv, origin: Mapping[str, int], y: Mapping[str, int]) -> dict[Step, int]:
    """The step above each lane cell that a foot join of its column reaches, where it has no row.

    `y` is the page solved before these steps; a join with a row of its own keeps its bend.
    """
    grid = env.options.wiring_grid
    spans: dict[Step, list[tuple[int, int]]] = defaultdict(list)
    for col in env.flow.columns:
        pc = env.pcs.get(col.id)
        if pc is None:
            continue
        where = {c.sym: (li, i) for li, cells in enumerate(pc.lanes) for i, c in enumerate(cells)}
        for li, end in enumerate(col.heads if pc.flipped else col.feet):
            into = where.get(end.pin.sym) if end.is_join and end.pin is not None else None
            if into is None or into[1] == 0 or end.pin is None:
                continue
            foot, target = pc.lanes[li][-1], pc.lanes[into[0]][into[1]]
            a = _End(cell_node(pc.id, li, len(pc.lanes[li]) - 1), foot, foot.bottom_pin)
            if _no_row(env, y, a, _End(cell_node(pc.id, *into), target, end.pin.pin)):
                spans[col.id, into[0], into[1] - 1] += _spans(env, origin, foot, target)
    return {
        step: grid * (max(levels(s, range(len(s)))) + env.options.jog_lanes)
        for step, s in spans.items()
        if s
    }
