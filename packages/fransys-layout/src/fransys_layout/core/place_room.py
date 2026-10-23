"""Stage 5, room: the y step each pair of consecutive cells needs for the jogs between them.

From the x solution alone (no route call): the jogs of one step form a stair whose spans take
levels from `intervals.levels`, in the order stage 6 nests them (E6); the step is
`max(wire_min, grid * (levels + 1))`. A step with no jog keeps `wire_min`.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING, NamedTuple

from .geometry import cell_anchor, pin_xy
from .intervals import levels
from .keys import natural_key
from .node_names import col_node

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .place_env import PageEnv

Step = tuple[str, int, int]  # (column id, lane, index of the upper cell)
CrossedRooms = dict[tuple[str, str], int]  # (fan id, symbol) -> crossed levels


class _Jog(NamedTuple):
    step: Step
    row: int
    top_x: int
    bottom_x: int
    net: str


def _net_of(env: PageEnv) -> dict[tuple[str, str], str]:
    return {(r.sym, r.pin): n.id for n in env.problem.nets for r in n.pins}


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


def _jogs(env: PageEnv, x: Mapping[str, int]) -> list[_Jog]:
    """Every wire between consecutive cells of a lane whose two pins differ in x."""
    nets, origin = _net_of(env), origins(env, x)
    out = []
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            for i, (a, b) in enumerate(pairwise(cells)):
                if a.bottom_pin is None or b.top_pin is None:
                    continue
                net = nets.get((a.sym, a.bottom_pin))
                if net is None or net != nets.get((b.sym, b.top_pin)):
                    continue
                xa = origin[a.sym] + pin_xy(env.syms[a.sym], a, a.bottom_pin)[0]
                xb = origin[b.sym] + pin_xy(env.syms[b.sym], b, b.top_pin)[0]
                if xa != xb:
                    out.append(_Jog((pc.id, li, i), pc.row, xa, xb, net))
    return out


def step_rooms(env: PageEnv, x: Mapping[str, int]) -> dict[Step, int]:
    """The pin-to-pin y step of each cell pair that has a jog; the others keep wire_min."""
    groups: dict[tuple[int, int, bool], list[_Jog]] = defaultdict(list)
    for j in _jogs(env, x):
        groups[j.row, j.step[2], j.bottom_x < j.top_x].append(j)
    grid = env.options.wiring_grid
    rooms: dict[Step, int] = {}
    for (_, _, left), group in groups.items():
        ordered = sorted(
            group, key=lambda j: (j.top_x, j.bottom_x, natural_key(j.net)), reverse=not left
        )
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
