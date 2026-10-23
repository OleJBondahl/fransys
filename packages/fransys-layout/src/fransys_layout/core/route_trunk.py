"""Stage 6 trunks: the trunk line, one drop per attachment on its row, risers and crossed drops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .band import lane_offset, level_offset
from .errors import CoreError
from .outputs import Wire
from .route_env import Drawn, Rise, failed, pin_point, row_band, z_wire

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
        return self.trunk.y + (lane_offset(lane, self.grid) if self.fan.lanes > 1 else 0)

    def member(self, lane: int) -> str:
        """The net a drop to lane j carries: the member's id in a bundle, else the fan's net."""
        return self.fan.nets[lane] if self.fan.lanes > 1 else self.net


class TrunkError(CoreError):
    """A bundle's attachment names a lane index its fan has no net for."""


def _check_poles(fan: Fan) -> None:
    """Every attachment of a bundle names a lane index with a lane line and a net; else raise."""
    room = min(fan.lanes, len(fan.nets))
    for a in (*fan.drivers, *fan.legs):
        if fan.lanes > 1 and a.pole >= room:
            msg = (
                f"bundle {fan.id}: {a.pin.sym} {a.pin.pin} is on pole {a.pole}, but the bundle "
                f"has {fan.lanes} lanes and {len(fan.nets)} nets ({', '.join(fan.nets)}); every "
                "pole of a bundle needs a net: give the missing pole's net to the bundle"
            )
            raise TrunkError(msg)


def drop_kind(fan: Fan, a: Attach) -> WireKind:
    """A box pin that drives the trunk rises to it; every other attachment drops."""
    return "riser" if a.column is None and a not in fan.legs else "drop"


def plain_drop(line: Line, a: Attach, xy: XY, lane: int) -> tuple[Wire, ...]:
    """The attachment's straight drop to the line of its lane; none when it already sits on it."""
    y = line.y_of(lane)
    if xy[1] == y:
        return ()
    return (Wire(line.member(lane), line.trunk.page, (xy, (xy[0], y)), drop_kind(line.fan, a)),)


def _foreign_body(env: RouteEnv, fan: Fan, x: int, ys: tuple[int, int]) -> bool:
    """The vertical at x between ys passes a footprint of a symbol the fan is not attached to."""
    cols = {a.column for a in (*fan.drivers, *fan.legs) if a.column}
    own = {a.pin.sym for a in (*fan.drivers, *fan.legs)}
    own |= {
        c.sym for col in env.columns if col.id in cols for lane in col.lanes for c in lane.cells
    }
    top, bottom = min(ys), max(ys)
    return any(
        p.footprint.x < x < p.footprint.x + p.footprint.w
        and p.footprint.y < bottom
        and top < p.footprint.y + p.footprint.h
        for sym, p in env.placed.items()
        if sym not in own
    )


def drop_or_rise(env: RouteEnv, line: Line, a: Attach, xy: XY, lane: int) -> Drawn:
    """The straight drop, or a rise for A* when its vertical passes a foreign body."""
    y = line.y_of(lane)
    if xy[1] != y and _foreign_body(env, line.fan, xy[0], (xy[1], y)):
        return Drawn(
            rises=(Rise(line.member(lane), a.pin.sym, xy, (xy[0], y), drop_kind(line.fan, a)),)
        )
    return Drawn(wires=plain_drop(line, a, xy, lane))


@dataclass(frozen=True, slots=True)
class Crossed:
    """One function of a bundle whose lane indexes take the lanes in another order."""

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
    """Lane j leaves its index's x one step toward the target index, runs to its level, crosses."""
    line, (j, rank, pole_x, own_x) = c.line, at
    if c.above:
        level = line.trunk.y - lane_offset(rank + 1, line.grid)
    else:
        level = line.trunk.y + level_offset(line.fan.lanes, rank, line.grid)
    depart = own_x + (line.grid if pole_x > own_x else -line.grid)
    ends = (xy, (depart, line.y_of(j)))
    return z_wire(line.member(j), line.trunk.page, ends, level, drop_kind(line.fan, a))


def _room(c: Crossed, atts: Sequence[Held], rank: Mapping[int, int]) -> bool:
    """The deepest crossed level lies strictly between the trunk's lines and the pins' row."""
    if not rank:
        return True
    line, pin_y = c.line, atts[0][1][1]
    deepest = max(rank.values())
    if c.above:
        return pin_y < line.trunk.y - lane_offset(deepest + 1, line.grid)
    return line.trunk.y + level_offset(line.fan.lanes, deepest, line.grid) < pin_y


def crossed_drops(env: RouteEnv, c: Crossed, atts: Sequence[Held]) -> Drawn:
    """One function whose indexes take the lanes in another order: lane j drops to index perm[j].

    Left-shifters take the levels nearest the trunk, then right-shifters, each nested by E6.
    With no room for the levels nothing is drawn and a finding says so.
    """
    lane_of = {pole: lane for lane, pole in enumerate(c.perm)}
    xs = {a.pole: xy[0] for a, xy in atts}
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
        j = lane_of.get(a.pole, a.pole)
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


def _trunk_line(line: Line) -> tuple[Wire, ...]:
    """The trunk's line; none when its ends share one x (symdef draws no run of no length)."""
    t = line.trunk
    if t.x0 == t.x1:
        return ()
    return (Wire(line.net, t.page, ((t.x0, t.y), (t.x1, t.y)), "trunk", line.fan.lanes),)


def trunk_wires(env: RouteEnv, trunk: Trunk) -> Drawn:
    """The trunk line, one drop per attachment on its row; a bundle's lane j drops from line j.

    A bundle's trunk carries the bundle id; each drop carries its member's id (layout-0297, D.7).
    A function in `fan.crossed` takes its lanes in another index order; crossed_drops draws it.
    """
    fan = env.fans.get(trunk.fan)
    if fan is None:
        text = f"trunk of fan {trunk.fan} has no fan in the flow, so it is not drawn: report it"
        return Drawn(findings=(failed(env, trunk.fan, text),))
    _check_poles(fan)
    line = Line(fan, trunk, fan.nets[0] if fan.lanes == 1 else fan.id, env.options.wiring_grid)
    out = Drawn(wires=_trunk_line(line))
    permuted = dict(fan.crossed) if fan.lanes > 1 else {}
    held: dict[tuple[str, bool], list[Held]] = {}
    for a, xy in _placed_attachments(env, line, row_band(env, trunk)):
        if a.pin.sym in permuted:
            held.setdefault((a.pin.sym, xy[1] < trunk.y), []).append((a, xy))
        else:
            out += drop_or_rise(env, line, a, xy, a.pole)
    for (sym, above), atts in sorted(held.items()):
        out += crossed_drops(env, Crossed(line, permuted[sym], above), atts)
    return out
