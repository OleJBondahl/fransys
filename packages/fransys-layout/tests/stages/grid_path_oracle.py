"""The grid search as it stood before layout-0156, kept verbatim as the exactness oracle.

`oracle_path` and its helpers are a copy of `stages/grid_path.py` taken before any speed-up. It
shares nothing private with the module, so a change to the module cannot move it. The replay
and property tests assert that `grid_path` returns exactly what this returns, `None` included.
"""

import heapq
from typing import TYPE_CHECKING

from fransys_layout.geometry import (
    FACING_STEP,
    OPPOSITE,
    WIRING_GRID,
    Facing,
    Point,
    contains_point,
)
from fransys_layout.stages.space import Cell, End, obstacle_index, step_admitted

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages.grid_path import Field

type _State = tuple[Cell, Facing]

_HEADINGS = tuple(Facing)
_RANK = {heading: rank for rank, heading in enumerate(_HEADINGS)}


def oracle_path(start: End, goal: End, field: Field) -> tuple[Point, ...] | None:
    """The cheapest orthogonal path, uniform cost; ties break on `(cost, x, y, heading rank)`."""
    first: _State = ((start.at.x, start.at.y), start.facing)
    last: _State = ((goal.at.x, goal.at.y), OPPOSITE[goal.facing])
    ends, obstacles = frozenset({first[0], last[0]}), obstacle_index(field.obstacles)
    best: dict[_State, int] = {first: 0}
    came: dict[_State, _State] = {}
    settled: set[_State] = set()
    heap = [(0, start.at.x, start.at.y, _RANK[start.facing])]
    while heap:
        cost, x, y, rank = heapq.heappop(heap)
        state: _State = ((x, y), _HEADINGS[rank])
        if state in settled:
            continue
        settled.add(state)
        if state == last:
            return _corners(_walk(came, first, last))
        for heading in (start.facing,) if state == first else _HEADINGS:
            step = FACING_STEP[heading]
            cell = (x + step[0], y + step[1])
            if not contains_point(field.region, cell[0], cell[1]) or not step_admitted(
                (x, y), cell, obstacles, ends
            ):
                continue
            if field.axes and not _crosses_cleanly((x, y), state[1], heading, cell, field):
                continue
            price = cost + _price(cell, field, turned=heading is not state[1])
            if price < best.get((cell, heading), price + 1):
                best[cell, heading] = price
                came[cell, heading] = state
                heapq.heappush(heap, (price, cell[0], cell[1], _RANK[heading]))
    return None


def _crosses_cleanly(here: Cell, came: Facing, heading: Facing, cell: Cell, field: Field) -> bool:
    if here in field.axes and heading is not came:
        return False
    other = field.axes.get(cell)
    if other is None:
        return True
    mine = frozenset({"v" if heading in (Facing.N, Facing.S) else "h"})
    return len(mine) == 1 and len(other) == 1 and mine != other


def _price(cell: Cell, field: Field, *, turned: bool) -> int:
    price = 0 if cell in field.free else WIRING_GRID
    if cell in field.busy:
        price += field.crossing_penalty
    return price + field.turn_penalty if turned else price


def _walk(came: Mapping[_State, _State], first: _State, last: _State) -> list[Cell]:
    cells = [last[0]]
    state = last
    while state != first:
        state = came[state]
        cells.append(state[0])
    cells.reverse()
    return cells


def _corners(cells: Sequence[Cell]) -> tuple[Point, ...]:
    points = [Point(x=cells[0][0], y=cells[0][1])]
    for before, cell, after in zip(cells, cells[1:], cells[2:], strict=False):
        if (cell[0] - before[0], cell[1] - before[1]) != (after[0] - cell[0], after[1] - cell[1]):
            points.append(Point(x=cell[0], y=cell[1]))
    points.append(Point(x=cells[-1][0], y=cells[-1][1]))
    return tuple(points)
