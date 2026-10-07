"""The bounded grid search behind `route` and `harness_route` (package-layout.md 4, route.md 6.5).

Cells are wiring-grid points, a state is `(cell, heading)`, and the cost is in grid
units. Nothing here knows a handle or a record: `route` hands it boxes, cells and
penalties and gets a polyline back.
"""

import dataclasses
import heapq
from collections.abc import Hashable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.geometry import (
    FACING_STEP,
    OPPOSITE,
    WIRING_GRID,
    Box,
    Facing,
    Point,
    contains_point,
    port_exit,
)

from .space import Cell, End, Obstacle, obstacle_index, step_admitted

if TYPE_CHECKING:
    from .cell_index import CellIndex

type _State = tuple[Cell, Facing]

# Ties break on the heading's rank, which is `Facing`'s declaration order.
_HEADINGS = tuple(Facing)
_RANK = frozendict({heading: rank for rank, heading in enumerate(_HEADINGS)})


@dataclass(frozen=True, slots=True)
class Field:
    """What one edge's search sees: where it may go, what is in the way, what it pays."""

    region: Box
    obstacles: tuple[Obstacle, ...]
    free: frozenset[Cell]
    busy: frozenset[Cell]
    turn_penalty: int
    crossing_penalty: int
    # C22 (deep dive): per foreign-net cell, the axes ("h", "v") its wires pass it along; a
    # step may enter such a cell only across a straight foreign wire, and not turn in it
    axes: dict[Cell, frozenset[str]] = dataclasses.field(default_factory=dict)


def cells_of(points: tuple[Point, ...]) -> frozenset[Cell]:
    """Every wiring-grid cell a polyline covers, corners and endpoints included."""
    covered: set[Cell] = set()
    for first, second in pairwise(points):
        along = max(abs(second.x - first.x), abs(second.y - first.y)) // WIRING_GRID
        dx = (second.x - first.x) // along if along else 0
        dy = (second.y - first.y) // along if along else 0
        covered.update((first.x + dx * i, first.y + dy * i) for i in range(along + 1))
    return frozenset(covered)


@dataclass(slots=True)
class _Search:
    """One `grid_path` call: its ends, its obstacles and the step checks already made."""

    field: Field
    first: _State
    last: _State
    heading: Facing
    obstacles: CellIndex[Obstacle]
    ends: frozenset[Cell]
    admitted: dict[tuple[Cell, Cell], bool] = dataclasses.field(default_factory=dict)
    # decision layout-0156: the cost of the cheapest path; a state costlier than it is not tried
    bound: int | None = None

    def admits(self, here: Cell, cell: Cell) -> bool:
        """`step_admitted`, asked once per step in this call (the obstacles do not change)."""
        key = (here, cell)
        if key not in self.admitted:
            self.admitted[key] = step_admitted(here, cell, self.obstacles, self.ends)
        return self.admitted[key]

    def moves(self, state: _State, cost: int) -> Iterator[tuple[_State, int]]:
        """Each state a step from `state` reaches, with its cost; none that cannot beat `bound`."""
        (x, y), came = state
        for heading in (self.heading,) if state == self.first else _HEADINGS:
            step = FACING_STEP[heading]
            cell = (x + step[0], y + step[1])
            if not contains_point(self.field.region, cell[0], cell[1]):
                continue
            price = cost + _price(cell, self.field, turned=heading is not came)
            if self.bound is not None and price + _manhattan(cell, self.last[0]) > self.bound:
                continue
            if not self.admits((x, y), cell):
                continue
            if self.field.axes and not _crosses_cleanly((x, y), came, heading, cell, self.field):
                continue
            yield (cell, heading), price


def grid_path(start: End, goal: End, field: Field) -> tuple[Point, ...] | None:
    """The cheapest orthogonal path, uniform cost; ties break on `(cost, x, y, heading rank)`."""
    first: _State = ((start.at.x, start.at.y), start.facing)
    last: _State = ((goal.at.x, goal.at.y), OPPOSITE[goal.facing])
    ends = frozenset({first[0], last[0]})
    search = _Search(field, first, last, start.facing, obstacle_index(field.obstacles), ends)
    if not field.free:
        cheapest = _optimal_cost(search)
        if cheapest is None:
            return None
        search = dataclasses.replace(search, bound=cheapest)
    return _dijkstra(search)


def _manhattan(here: Cell, there: Cell) -> int:
    """The cost no path from `here` to `there` can beat when every step costs a grid or more."""
    return abs(here[0] - there[0]) + abs(here[1] - there[1])


def _optimal_cost(search: _Search) -> int | None:
    """A* with the Manhattan bound: the cost of the cheapest path, or None (layout-0156)."""
    goal = search.last[0]
    best = {search.first: 0}
    heap = [(_manhattan(search.first[0], goal), 0, *search.first[0], _RANK[search.first[1]])]
    while heap:
        _, cost, x, y, rank = heapq.heappop(heap)
        state: _State = ((x, y), _HEADINGS[rank])
        if cost > best[state]:
            continue
        if state == search.last:
            return cost
        for after, price in search.moves(state, cost):
            if price < best.get(after, price + 1):
                best[after] = price
                heapq.heappush(
                    heap, (price + _manhattan(after[0], goal), price, *after[0], _RANK[after[1]])
                )
    return None


@dataclass(slots=True)
class _Frontier:
    """The states reached so far: the cheapest cost to each, where from, and what is next."""

    best: dict[_State, int]
    came: dict[_State, _State] = dataclasses.field(default_factory=dict)
    heap: list[tuple[int, int, int, int]] = dataclasses.field(default_factory=list)

    def offer(self, after: _State, state: _State, price: int) -> None:
        """Reach `after` from `state` at `price`, if that beats what is known."""
        if price < self.best.get(after, price + 1):
            self.best[after] = price
            self.came[after] = state
            heapq.heappush(self.heap, (price, after[0][0], after[0][1], _RANK[after[1]]))


def _dijkstra(search: _Search) -> tuple[Point, ...] | None:
    """Settle states in `(cost, x, y, heading rank)` order until the goal state settles."""
    frontier = _Frontier({search.first: 0}, heap=[(0, *search.first[0], _RANK[search.first[1]])])
    settled: set[_State] = set()
    while frontier.heap:
        cost, x, y, rank = heapq.heappop(frontier.heap)
        state: _State = ((x, y), _HEADINGS[rank])
        if state in settled:
            continue
        settled.add(state)
        if state == search.last:
            return _corners(_walk(frontier.came, search.first, search.last))
        for after, price in search.moves(state, cost):
            frontier.offer(after, state, price)
    return None


def _crosses_cleanly(here: Cell, came: Facing, heading: Facing, cell: Cell, field: Field) -> bool:
    """C22: no turn inside a foreign wire's cell, and entering one only across its wire."""
    if here in field.axes and heading is not came:
        return False
    other = field.axes.get(cell)
    if other is None:
        return True
    return clean_crossing(frozenset({"v" if heading in (Facing.N, Facing.S) else "h"}), other)


def clean_crossing(mine: frozenset[str], other: frozenset[str]) -> bool:
    """C22: two nets meet at a cell only across each other's straight wire, one `h`, one `v`."""
    return len(mine) == 1 and len(other) == 1 and mine != other


def axes_of(points: tuple[Point, ...]) -> dict[Cell, frozenset[str]]:
    """C22: every cell a polyline covers, with its axes (a corner or an end has both)."""
    found: dict[Cell, set[str]] = {}
    for first, second in pairwise(points):
        axis = "v" if first.x == second.x else "h"
        for cell in cells_of((first, second)):
            found.setdefault(cell, set()).add(axis)
    for end in (points[0], points[-1]):
        found.setdefault((end.x, end.y), set()).update({"h", "v"})
    return {cell: frozenset(axes) for cell, axes in found.items()}


def reserve_exits[Net: Hashable](
    ends: Iterable[tuple[Net, End]],
) -> dict[Cell, dict[Net, frozenset[str]]]:
    """EF-D part 3: the cell before each end with its wire's axis; a cell two nets claim is out."""
    claims: dict[Cell, dict[Net, frozenset[str]]] = {}
    for net, end in ends:
        exit_at = port_exit(end.at, end.facing)
        cell = (exit_at.x, exit_at.y)
        axis = "v" if end.facing in (Facing.N, Facing.S) else "h"
        claims.setdefault(cell, {})[net] = claims.get(cell, {}).get(net, frozenset()) | {axis}
    return {cell: nets for cell, nets in claims.items() if len(nets) == 1}


def _price(cell: Cell, field: Field, *, turned: bool) -> int:
    """What entering `cell` costs: a step, unless the same net already drew through it."""
    price = 0 if cell in field.free else WIRING_GRID
    if cell in field.busy:
        price += field.crossing_penalty
    return price + field.turn_penalty if turned else price


def _walk(came: Mapping[_State, _State], first: _State, last: _State) -> list[Cell]:
    """The cells of the found path, from the start cell to the goal cell."""
    cells = [last[0]]
    state = last
    while state != first:
        state = came[state]
        cells.append(state[0])
    cells.reverse()
    return cells


def _corners(cells: Sequence[Cell]) -> tuple[Point, ...]:
    """The path as its vertices: the two ends and every cell where it turns."""
    points = [Point(x=cells[0][0], y=cells[0][1])]
    for before, cell, after in zip(cells, cells[1:], cells[2:], strict=False):
        if (cell[0] - before[0], cell[1] - before[1]) != (after[0] - cell[0], after[1] - cell[1]):
            points.append(Point(x=cell[0], y=cell[1]))
    points.append(Point(x=cells[-1][0], y=cells[-1][1]))
    return tuple(points)
