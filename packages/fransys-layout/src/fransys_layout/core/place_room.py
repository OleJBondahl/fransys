"""Stage 5, room: the y step each pair of consecutive cells needs for the jogs between them.

From the x solution alone (no route call): the jogs of one step form a stair whose spans take
levels from `intervals.levels`, in the order stage 6 nests them (E6); the step is
`max(wire_min, grid * (levels + 1))`. A step with no jog keeps `wire_min`.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

from .flow_values import hop_wires
from .geometry import cell_anchor, pin_xy, stair_room
from .intervals import levels
from .keys import natural_key
from .node_names import col_node
from .pack import cell_node
from .values import PinRef

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from collections.abc import Set as AbstractSet

    from .flow_values import Cell
    from .pack import PlacedColumn
    from .place_env import PageEnv

Step = tuple[str, int, int]  # (column id, lane, index of the upper cell)
CrossedRooms = dict[tuple[str, str], int]  # (fan id, symbol) -> crossed levels


class _Jog(NamedTuple):
    step: Step
    row: int
    top_x: int
    bottom_x: int
    net: str


def origins(env: PageEnv, x: Mapping[str, int]) -> dict[str, int]:
    """The x origin of each symbol: where its first lane puts it, as stage 5 assembles it."""
    out: dict[str, int] = {}
    for pc in env.pcs.values():
        for lane, cells in enumerate(pc.lanes):
            for cell in cells:
                if cell.sym not in out:
                    ax, _ = cell_anchor(env.syms[cell.sym], cell)
                    out[cell.sym] = x[col_node(pc.id)] + pc.offsets[lane] - ax
    return out


def _wires(
    env: PageEnv, pc: PlacedColumn, net_of: Mapping[PinRef, str], pins: Mapping[str, tuple[PinRef, ...]]
) -> Iterator[tuple[Step, Cell, str, Cell, str, str]]:
    """The wires between consecutive cells of a column: each lane's own, and the chain hops (route draws the same, `hop_wires`)."""
    for li, cells in enumerate(pc.lanes):
        for i, (a, b) in enumerate(pairwise(cells)):
            own = net_of.get(PinRef(a.sym, a.bottom_pin or ""))
            if own is not None and a.bottom_pin and b.top_pin and own == net_of.get(PinRef(b.sym, b.top_pin)):
                yield (pc.id, li, i), a, a.bottom_pin, b, b.top_pin, own
    for i, _, _, net, pa, pb in hop_wires(env.columns[pc.id], net_of, pins):
        if pa and pb:
            yield (pc.id, 0, i), pc.lanes[0][i], pa.pin, pc.lanes[0][i + 1], pb.pin, net


def _no_row(env: PageEnv, y: Mapping[str, int], pc: PlacedColumn, foot: tuple[int, Cell], target: tuple[tuple[int, int], Cell, str]) -> bool:
    """True when the join's two pins stand one grid apart in y, so its stair has room 0."""
    (li, top), ((tl, ti), bottom, pin) = foot, target
    if top.bottom_pin is None:
        return False
    yt = y[cell_node(pc.id, li, len(pc.lanes[li]) - 1)] + pin_xy(env.syms[top.sym], top, top.bottom_pin)[1]
    yb = y[cell_node(pc.id, tl, ti)] + pin_xy(env.syms[bottom.sym], bottom, pin)[1]
    return abs(yt - yb) > 0 and stair_room(0, abs(yt - yb), env.options.wiring_grid) < 1


def _net_wires(env: PageEnv, step: Step, foot: Cell, target: Cell) -> Iterator[tuple[Step, Cell, str, Cell, str, str]]:
    """Each net's wire between a foot and its target, one per pin pair."""
    for net in env.problem.nets:
        for ra in (r for r in net.pins if r.sym == foot.sym):
            for rb in (r for r in net.pins if r.sym == target.sym):
                yield step, foot, ra.pin, target, rb.pin, net.id


def _join_wires(
    env: PageEnv, pc: PlacedColumn, y: Mapping[str, int] | None, busy: AbstractSet[Step]
) -> Iterator[tuple[Step, Cell, str, Cell, str, str]]:
    """The nets of a lane's foot join into another lane, where `y` leaves it no row or its step holds jogs (R456).

    With no `y` (the page not yet solved) no join is reserved; every other join keeps its bend.
    """
    if y is None:
        return
    col = env.columns[pc.id]
    where = {c.sym: (li, i) for li, cells in enumerate(pc.lanes) for i, c in enumerate(cells)}
    for li, end in enumerate(col.heads if pc.flipped else col.feet):
        if end.pin is None or not end.is_join:
            continue
        into = where.get(end.pin.sym)
        if into is None or into[1] == 0:
            continue
        foot, target = pc.lanes[li][-1], pc.lanes[into[0]][into[1]]
        if (pc.id, into[0], into[1] - 1) not in busy and not _no_row(env, y, pc, (li, foot), (into, target, end.pin.pin)):
            continue
        yield from _net_wires(env, (pc.id, into[0], into[1] - 1), foot, target)


def _moved(env: PageEnv, origin: Mapping[str, int], pc: PlacedColumn, wires: Iterator[tuple[Step, Cell, str, Cell, str, str]]) -> Iterator[_Jog]:
    """The wires whose two pins differ in x."""
    for step, a, pin_a, b, pin_b, net in wires:
        xa = origin[a.sym] + pin_xy(env.syms[a.sym], a, pin_a)[0]
        xb = origin[b.sym] + pin_xy(env.syms[b.sym], b, pin_b)[0]
        if xa != xb:
            yield _Jog(step, pc.row, xa, xb, net)


def _jogs(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int] | None) -> list[_Jog]:
    """Every wire between consecutive cells of a lane, or of a chain hop, whose two pins differ in x, then the foot joins `_join_wires` keeps."""
    nets, origin, pins = {r: n.id for n in env.problem.nets for r in n.pins}, origins(env, x), {n.id: n.pins for n in env.problem.nets}
    out = [j for pc in env.pcs.values() for j in _moved(env, origin, pc, _wires(env, pc, nets, pins))]
    busy = {j.step for j in out}
    return out + [j for pc in env.pcs.values() for j in _moved(env, origin, pc, _join_wires(env, pc, y, busy))]


def _routed_rooms(env: PageEnv) -> dict[Step, int]:
    """Room for a join routed round a body (layout-0482): every step beside a cell that lacks the facing pin.

    The join is a cross-link with an end on each symbol; its wire runs above the cell and below the symbol, in any lane.
    """
    pairs = [((pc.id, li, i), a, b) for pc in env.pcs.values() for li, cells in enumerate(pc.lanes) for i, (a, b) in enumerate(pairwise(cells))]
    lacking = {(b if a.bottom_pin else a).sym for _, a, b in pairs if frozenset((a.sym, b.sym)) in env.flow.joined}
    need = env.options.wire_min + 2 * env.options.wiring_grid
    return {k: need for k, a, b in pairs if lacking & {a.sym, b.sym}}


def step_rooms(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int] | None = None) -> dict[Step, int]:
    """The pin-to-pin y step of each cell pair that has a jog; the others keep wire_min. `y` is the page solved before the join rooms."""
    groups: dict[tuple[int, int, bool], list[_Jog]] = defaultdict(list)
    for j in _jogs(env, x, y):
        groups[j.row, j.step[2], j.bottom_x < j.top_x].append(j)
    grid = env.options.wiring_grid
    rooms: dict[Step, int] = _routed_rooms(env)
    for (_, _, left), group in groups.items():
        ordered = sorted(group, key=lambda j: (j.top_x, j.bottom_x, natural_key(j.net)), reverse=not left)
        spans = [(min(j.top_x, j.bottom_x), max(j.top_x, j.bottom_x)) for j in ordered]
        for j, level in zip(ordered, levels(spans, range(len(ordered))), strict=True):
            need = grid * (level + env.options.jog_lanes)
            rooms[j.step] = max(rooms.get(j.step, 0), need, env.options.wire_min)
    return rooms


def crossed_levels(env: PageEnv, x: Mapping[str, int]) -> CrossedRooms:
    """The levels stage 6 draws per (fan id, symbol), one per moved lane.

    A lane moves when its index sits at another x than its own lane's; stage 6 gives each its level.
    """
    out: CrossedRooms = {}
    for fan in env.flow.fans:
        for sym, perm in fan.crossed:
            xs = {
                a.pole: x[col_node(a.column)] + env.pcs[a.column].offsets[a.lane]
                for a in (*fan.drivers, *fan.legs)
                if a.pin.sym == sym and a.column is not None and a.column in env.pcs
            }
            moved = [j for j, pole in enumerate(perm) if pole != j and j in xs and pole in xs]
            if moved:
                out[fan.id, sym] = len(moved)
    return out
