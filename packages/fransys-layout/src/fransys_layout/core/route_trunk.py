"""Stage 6 trunks: the trunk line, one drop per attachment on its row, risers and crossed drops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .band import lane_offset, lane_rows, level_offset
from .errors import CoreError
from .outputs import Wire
from .route_env import Drawn, Rise, failed, pin_point, row_band, z_wire
from .values import Finding

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
        """A bundle lane j stands its band row's steps below the trunk's first line (R505)."""
        if self.fan.lanes == 1:
            return self.trunk.y
        return self.trunk.y + lane_offset(lane_rows(self.trunk.lane_ends)[lane], self.grid)

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


def _bodies_hit(
    env: RouteEnv, own: frozenset[str], xs: tuple[int, int], ys: tuple[int, int]
) -> tuple[str, ...]:
    """The placed symbols not in `own` whose footprint the segment's box (xs by ys) passes."""
    return tuple(
        sym
        for sym, p in env.placed.items()
        if sym not in own
        and p.footprint.x < max(xs)
        and min(xs) < p.footprint.x + p.footprint.w
        and p.footprint.y < max(ys)
        and min(ys) < p.footprint.y + p.footprint.h
    )


def _body_hit(env: RouteEnv, own: frozenset[str], xs: tuple[int, int], ys: tuple[int, int]) -> bool:
    return bool(_bodies_hit(env, own, xs, ys))


def _foreign_body(env: RouteEnv, fan: Fan, x: int, ys: tuple[int, int]) -> bool:
    """The vertical at x between ys passes a footprint of a symbol the fan is not attached to."""
    cols = {a.column for a in (*fan.drivers, *fan.legs) if a.column}
    own = {a.pin.sym for a in (*fan.drivers, *fan.legs)}
    own |= {
        c.sym for col in env.columns if col.id in cols for lane in col.lanes for c in lane.cells
    }
    return _body_hit(env, frozenset(own), (x, x), ys)


def _trunk_clear(env: RouteEnv, line: Line) -> Finding | None:
    """TRUNK_THROUGH_BODY (a warning, the line still drawn) naming the first symbol passed."""
    for w in _trunk_line(line):
        (x0, y), (x1, _) = w.points[0], w.points[-1]
        if hit := _bodies_hit(env, frozenset(), (x0, x1), (y, y)):
            text = (
                f"trunk {line.fan.id} draws a line at y {y} from x {x0} to {x1} through the "
                f"keep-out of {hit[0]}; it is drawn as placed (stage 5 does not yet stand a "
                "trunk clear of bodies)"
            )
            return Finding("TRUNK_THROUGH_BODY", text, env.page, line.fan.id)
    return None


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
    """The trunk's lines: one per lane of a bundle, from its first tap to its last; else one.

    A line with ends on one x is not drawn (symdef draws no run of no length).
    """
    t = line.trunk
    if line.fan.lanes == 1:
        return (
            (Wire(line.net, t.page, ((t.x0, t.y), (t.x1, t.y)), "trunk"),) if t.x0 != t.x1 else ()
        )
    return tuple(
        Wire(line.member(j), t.page, ((x0, line.y_of(j)), (x1, line.y_of(j))), "trunk", lane=j)
        for j, ends in enumerate(t.lane_ends)
        if ends is not None and ends[0] != ends[1]
        for x0, x1 in (ends,)
    )


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
    found = _trunk_clear(env, line)
    out = Drawn(wires=_trunk_line(line), findings=(found,) if found else ())
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
