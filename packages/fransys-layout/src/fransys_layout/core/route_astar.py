"""Stage 6 cross-links: A* on the wiring grid with bend and crossing penalties.

Cells are grid units; `step` is `Options.wiring_grid`. A cell is blocked by a footprint, refused
along the axis another net already uses it on, and costs `crossing_penalty` across it. In a soft
round (`Occupancy.share_cost`) the wire rules of R391 are priced, not refused.
"""

import heapq
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .values import XY, Box, Options
lazy from .occupancy import Occupancy

if TYPE_CHECKING:
    from collections.abc import Sequence
    from collections.abc import Set as AbstractSet

INF = 1 << 60
MOVES = ((1, 0, "h"), (-1, 0, "h"), (0, 1, "v"), (0, -1, "v"))
State = tuple[XY, str]
Entry = tuple[int, int, int, XY, str, tuple[XY, ...]]


@dataclass(frozen=True, slots=True)
class Leg:
    """One search: net, start and goal cells; `free` cells are enterable though blocked.

    `targets` are further goal cells (the net's tree); `own` are the symbols whose port cell it
    may enter.
    """

    net: str
    start: XY
    goal: XY
    free: AbstractSet[XY] = frozenset()
    targets: AbstractSet[XY] = frozenset()
    own: frozenset[str] = frozenset()


def tidy(points: Sequence[XY]) -> tuple[XY, ...]:
    """Drop repeated points and the middle point of any straight run."""
    out: list[XY] = []
    for p in points:
        if out and p == out[-1]:
            continue
        if len(out) > 1 and (out[-2][0] == out[-1][0] == p[0] or out[-2][1] == out[-1][1] == p[1]):
            out.pop()
        out.append(p)
    return tuple(out)


def anchor(pin: XY, fp: Box, step: int) -> tuple[XY, ...]:
    """From a pin to the grid point just outside the footprint edge nearest it.

    The wire leaves along that edge's normal for at least one step, then steps to the grid. A*
    starts and ends at the last point.
    """
    px, py = pin
    gap = {"N": py - fp.y, "S": fp.y + fp.h - py, "W": px - fp.x, "E": fp.x + fp.w - px}
    side = min(gap, key=lambda k: (gap[k], "NSWE".index(k)))
    gx, gy = round(px / step) * step, round(py / step) * step
    if side == "S":
        gy = ((fp.y + fp.h) // step + 1) * step
    elif side == "N":
        gy = (fp.y // step - 1) * step
    elif side == "E":
        gx = ((fp.x + fp.w) // step + 1) * step
    else:
        gx = (fp.x // step - 1) * step
    corner = (px, gy) if side in "NS" else (gx, py)
    return tidy((pin, corner, (gx, gy)))


def _step_cost(grid: Occupancy, leg: Leg, cell: XY, axis: str, options: Options) -> int | None:
    """None when the cell is blocked, or an end or the goal would lie on another net's wire."""
    net, soft = leg.net, grid.share_cost
    price = grid.step + grid.history.get((cell, axis), 0)
    if cell in leg.free or cell == leg.goal or cell in leg.targets:
        if grid.foreign(cell, net):
            if not soft:
                return None
            price += soft
        if cell in leg.free:
            return price
    if grid.blocked(cell, axis, net, leg.own):
        return None
    return price + options.crossing_penalty * grid.crossing(cell, axis, net) + soft * grid.contested(cell, axis, net)


def _inside(grid: Occupancy, cell: XY) -> bool:
    return 0 <= cell[0] < grid.cols and 0 <= cell[1] < grid.rows


def _moves(grid: Occupancy, leg: Leg, state: State, options: Options) -> list[tuple[XY, str, int]]:
    """Steps from a state; a path turns only off another net's wire (R391)."""
    cell, arrived = state
    on_foreign = bool(arrived) and grid.foreign(cell, leg.net)
    out = []
    for dx, dy, axis in MOVES:
        nxt = (cell[0] + dx, cell[1] + dy)
        turn = on_foreign and axis != arrived
        if not _inside(grid, nxt) or (turn and not grid.share_cost):
            continue
        cost = _step_cost(grid, leg, nxt, axis, options)
        if cost is not None:
            out.append((nxt, axis, cost + (grid.share_cost if turn else 0)))
    return out


def astar(grid: Occupancy, leg: Leg, options: Options) -> tuple[XY, ...] | None:
    """Grid cells from start to goal, or None when no path exists; at equal cost, fewer crossings win (R643)."""
    if grid.foreign(leg.start, leg.net) and not grid.share_cost:
        return None
    best: dict[State, tuple[int, int]] = {}
    goals = {leg.goal, *leg.targets}
    heap: list[Entry] = [(0, 0, 0, leg.start, "", (leg.start,))]
    while heap:
        node = heapq.heappop(heap)
        if node[3] in goals:
            return node[5]
        if best.get((node[3], node[4]), (INF, 0)) < (node[2], node[1]):
            continue
        _expand(grid, leg, options, (goals, best, heap), node)
    return None


def _expand(
    grid: Occupancy, leg: Leg, options: Options, search: tuple[AbstractSet[XY], dict[State, tuple[int, int]], list[Entry]], node: Entry
) -> None:
    """Queue every better move from one popped node, with its A* estimate to the nearest goal."""
    goals, best, heap = search
    _, crossed, g, cell, axis, path = node
    for nxt, nxt_axis, cost in _moves(grid, leg, (cell, axis), options):
        bend = options.bend_penalty if axis and axis != nxt_axis else 0
        ng, nc = g + cost + bend, crossed + grid.crossing(nxt, nxt_axis, leg.net)
        if (ng, nc) < best.get((nxt, nxt_axis), (INF, 0)):
            best[(nxt, nxt_axis)] = (ng, nc)
            h = min(abs(c[0] - nxt[0]) + abs(c[1] - nxt[1]) for c in goals) * grid.step
            heapq.heappush(heap, (ng + h, nc, ng, nxt, nxt_axis, (*path, nxt)))


def simplify(path: Sequence[XY], step: int) -> tuple[XY, ...]:
    """Grid cells to a polyline in G with only the corners kept."""
    pts = [(x * step, y * step) for x, y in path]
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:], strict=False):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.append(b)
    if len(pts) > 1:
        out.append(pts[-1])
    return tuple(out)
