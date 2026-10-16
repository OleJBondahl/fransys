"""Stage 6 cross-links: A* on the wiring grid with bend and crossing penalties.

Cells are grid units; `step` is `Options.wiring_grid`. A cell is blocked by a footprint, refused
along the axis another net already uses it on, and costs `crossing_penalty` across it.
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


@dataclass(frozen=True, slots=True)
class Leg:
    """One search: net, start and goal cells; `free` cells are enterable though blocked.

    `targets` are further goal cells (the cells the net's tree holds); `window` is the inclusive
    cell box (x0, y0, x1, y1) the search stays in, None for the whole page.
    """

    net: str
    start: XY
    goal: XY
    free: AbstractSet[XY] = frozenset()
    targets: AbstractSet[XY] = frozenset()
    window: tuple[int, int, int, int] | None = None


def tidy(points: Sequence[XY]) -> tuple[XY, ...]:
    """Drop repeated points and the middle point of any straight run."""
    out: list[XY] = []
    for p in points:
        if out and p == out[-1]:
            continue
        if len(out) > 1 and _same_line(out[-2], out[-1], p):
            out.pop()
        out.append(p)
    return tuple(out)


def _same_line(a: XY, b: XY, c: XY) -> bool:
    return (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1])


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


def _step_cost(grid: Occupancy, net: str, cell: XY, axis: str, options: Options) -> int | None:
    """None when the cell is blocked or carries another net along the same axis."""
    if grid.blocked(cell, axis, net):
        return None
    return grid.step + options.crossing_penalty * grid.crossing(cell, axis, net)


def _inside(grid: Occupancy, leg: Leg, cell: XY) -> bool:
    x0, y0, x1, y1 = leg.window or (0, 0, grid.cols - 1, grid.rows - 1)
    return max(0, x0) <= cell[0] <= min(grid.cols - 1, x1) and max(0, y0) <= cell[1] <= min(
        grid.rows - 1, y1
    )


def _moves(grid: Occupancy, leg: Leg, cell: XY, options: Options) -> list[tuple[XY, str, int]]:
    out = []
    for dx, dy, axis in MOVES:
        nxt = (cell[0] + dx, cell[1] + dy)
        if not _inside(grid, leg, nxt):
            continue
        cost = grid.step if nxt in leg.free else _step_cost(grid, leg.net, nxt, axis, options)
        if cost is not None:
            out.append((nxt, axis, cost))
    return out


def astar(grid: Occupancy, leg: Leg, options: Options) -> tuple[XY, ...] | None:
    """Grid cells from start to goal, or None when no path exists."""
    best: dict[State, int] = {}
    goals = {leg.goal, *leg.targets}
    heap: list[tuple[int, int, XY, str, tuple[XY, ...]]] = [(0, 0, leg.start, "", (leg.start,))]
    while heap:
        _, g, cell, axis, path = heapq.heappop(heap)
        if cell in goals:
            return path
        if best.get((cell, axis), INF) < g:
            continue
        for nxt, nxt_axis, cost in _moves(grid, leg, cell, options):
            bend = options.bend_penalty if axis and axis != nxt_axis else 0
            if g + cost + bend < best.get((nxt, nxt_axis), INF):
                ng = g + cost + bend
                best[(nxt, nxt_axis)] = ng
                h = min(abs(c[0] - nxt[0]) + abs(c[1] - nxt[1]) for c in goals) * grid.step
                heapq.heappush(heap, (ng + h, ng, nxt, nxt_axis, (*path, nxt)))
    return None


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
