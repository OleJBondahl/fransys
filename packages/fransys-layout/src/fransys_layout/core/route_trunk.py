"""Stage 6 trunks: the trunk line, one drop per attachment on its row, risers and crossed drops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .outputs import Wire
from .route_env import Drawn, failed, pin_point, row_band, z_wire

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .outputs import Trunk
    from .route_env import RouteEnv
    from .values import XY, Attach, Fan, WireKind

Held = tuple["Attach", "XY"]


@dataclass(frozen=True, slots=True)
class Line:
    """A trunk with its fan: the net its wires carry and the y of each of its lane lines."""

    fan: Fan
    trunk: Trunk
    net: str
    grid: int

    def y_of(self, lane: int) -> int:
        """A bundle's lane j stands j grid steps below the trunk's first line; a plain fan on it."""
        return self.trunk.y + (self.grid * lane if self.fan.lanes > 1 else 0)


def drop_kind(fan: Fan, a: Attach) -> WireKind:
    """A box pin that drives the trunk rises to it; every other attachment drops."""
    return "riser" if a.column is None and a not in fan.legs else "drop"


def plain_drop(line: Line, a: Attach, xy: XY, lane: int) -> tuple[Wire, ...]:
    """The attachment's straight drop to the line of its lane; none when it already sits on it."""
    y = line.y_of(lane)
    if xy[1] == y:
        return ()
    return (Wire(line.net, line.trunk.page, (xy, (xy[0], y)), drop_kind(line.fan, a)),)


@dataclass(frozen=True, slots=True)
class Crossed:
    """One function of a bundle whose poles take the lanes in another order."""

    line: Line
    perm: tuple[int, ...]
    above: bool


def _ranks(perm: Sequence[int], xs: Mapping[int, int]) -> dict[int, int]:
    """Level rank of each moved lane: left-shifters first, then right-shifters, E6 inside each."""
    moved = [j for j, pole in enumerate(perm) if pole != j and j in xs and perm[j] in xs]
    lefts = sorted((j for j in moved if xs[perm[j]] < xs[j]), key=lambda j: xs[j])
    rights = sorted((j for j in moved if xs[perm[j]] > xs[j]), key=lambda j: -xs[j])
    return {j: m for m, j in enumerate(lefts + rights)}


def _crossed_wire(c: Crossed, a: Attach, xy: XY, at: tuple[int, int, int, int]) -> Wire:
    """Lane j leaves its pole's x one step toward the target pole, runs to its level and across."""
    line, (j, rank, pole_x, own_x) = c.line, at
    if c.above:
        level = line.trunk.y - line.grid * (rank + 1)
    else:
        level = line.trunk.y + line.grid * (line.fan.lanes + rank)
    depart = own_x + (line.grid if pole_x > own_x else -line.grid)
    ends = (xy, (depart, line.y_of(j)))
    return z_wire(line.fan.id, line.trunk.page, ends, level, drop_kind(line.fan, a))


def _room(c: Crossed, atts: Sequence[Held], rank: Mapping[int, int]) -> bool:
    """The deepest crossed level lies strictly between the trunk's lines and the pins' row."""
    if not rank:
        return True
    line, pin_y = c.line, atts[0][1][1]
    deepest = max(rank.values())
    if c.above:
        return pin_y < line.trunk.y - line.grid * (deepest + 1)
    return line.trunk.y + line.grid * (line.fan.lanes + deepest) < pin_y


def crossed_drops(env: RouteEnv, c: Crossed, atts: Sequence[Held]) -> Drawn:
    """One function whose poles take the lanes in another order: lane j drops to pole perm[j].

    Left-shifters take the levels nearest the trunk, then right-shifters, each nested by E6.
    With no room for the levels nothing is drawn and a finding says so.
    """
    lane_of = {pole: lane for lane, pole in enumerate(c.perm)}
    xs = {a.lane: xy[0] for a, xy in atts}
    rank = _ranks(c.perm, xs)
    if not _room(c, atts, rank):
        sym = atts[0][0].pin.sym
        text = (
            f"trunk {c.line.fan.id} has no room between its lines and the pins of {sym} for "
            f"{len(rank)} crossed levels, so the drops of {sym} are not drawn: stage 5 must "
            "leave one grid step per crossed lane under the trunk (report it to the designer)"
        )
        return Drawn(findings=(failed(env, sym, text),))
    out: list[Wire] = []
    for a, xy in atts:
        j = lane_of.get(a.lane, a.lane)
        if j not in rank:
            out.extend(plain_drop(c.line, a, xy, j))
        else:
            out.append(_crossed_wire(c, a, xy, (j, rank[j], xs[c.perm[j]], xs[j])))
    return Drawn(wires=tuple(out))


def _placed_attachments(env: RouteEnv, line: Line, row: tuple[int, int]) -> list[Held]:
    """Attachments of the fan standing on this trunk's row and within its x range.

    One of another row belongs to that row's trunk, and one on another page to that page's: both
    are skipped by design, never a finding.
    """
    out = []
    for a in (*line.fan.drivers, *line.fan.legs):
        xy = pin_point(env, a.pin.sym, a.pin.pin)
        if xy is not None and line.trunk.x0 <= xy[0] <= line.trunk.x1 and row[0] <= xy[1] <= row[1]:
            out.append((a, xy))
    return out


def trunk_wires(env: RouteEnv, trunk: Trunk) -> Drawn:
    """The trunk line, one drop per attachment on its row; a bundle's lane j drops from line j.

    A bundle's trunk and its drops carry the bundle id as their net: one thick line (L4). A
    function in `fan.crossed` takes its lanes in another pole order; crossed_drops draws it.
    """
    fan = env.fans.get(trunk.fan)
    if fan is None:
        text = f"trunk of fan {trunk.fan} has no fan in the flow, so it is not drawn: report it"
        return Drawn(findings=(failed(env, trunk.fan, text),))
    line = Line(fan, trunk, fan.nets[0] if fan.lanes == 1 else fan.id, env.options.wiring_grid)
    wires = [
        Wire(line.net, trunk.page, ((trunk.x0, trunk.y), (trunk.x1, trunk.y)), "trunk", fan.lanes)
    ]
    permuted = dict(fan.crossed) if fan.lanes > 1 else {}
    held: dict[tuple[str, bool], list[Held]] = {}
    for a, xy in _placed_attachments(env, line, row_band(env, trunk)):
        if a.pin.sym in permuted:
            held.setdefault((a.pin.sym, xy[1] < trunk.y), []).append((a, xy))
        else:
            wires.extend(plain_drop(line, a, xy, a.lane))
    out = Drawn(wires=tuple(wires))
    for (sym, above), atts in sorted(held.items()):
        out += crossed_drops(env, Crossed(line, permuted[sym], above), atts)
    return out
