"""Stage 6 trunks: the trunk line, one drop per attachment on its row, risers and crossed drops."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .arrow_reserve import leg_pins
from .band import lane_offset, lane_rows, level_offset
from .clearance import fan_own, pin_points, through_keeps
from .errors import CoreError
from .outputs import Refused, Wire
from .route_env import Drawn, Rise, hard_keeps, pin_point, z_wire
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from .flow_values import Attach, Fan
    from .outputs import Trunk
    from .route_env import RouteEnv
    from .values import XY, PinRef, WireKind

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


def _foreign_body(env: RouteEnv, fan: Fan, xy: XY, y: int) -> bool:
    """The drop from pin xy to y passes a foreign footprint or any body but at its own pin."""
    cols = {a.column for a in (*fan.drivers, *fan.legs) if a.column}
    own = fan_own(
        fan,
        ([c.sym for ln in col.lanes for c in ln.cells] for col in env.columns if col.id in cols),
    )
    return bool(through_keeps(Box(xy[0], min(xy[1], y), 0, abs(y - xy[1])), hard_keeps(env), (xy,), own, pin_points(env.placed)))


def drop_or_rise(env: RouteEnv, line: Line, a: Attach, xy: XY, lane: int) -> Drawn:
    """The straight drop, or a rise for A* when its vertical passes a foreign body."""
    y = line.y_of(lane)
    if xy[1] != y and _foreign_body(env, line.fan, xy, y):
        return Drawn(rises=(Rise(line.member(lane), a.pin, xy, (xy[0], y), drop_kind(line.fan, a)),))
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
    level = line.trunk.y - lane_offset(rank + 1, line.grid) if c.above else line.trunk.y + level_offset(line.fan.lanes, rank, line.grid)
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
    With no room for the levels nothing is drawn and each drop is lost.
    """
    lane_of = {pole: lane for lane, pole in enumerate(c.perm)}
    xs = {a.pole: xy[0] for a, xy in atts}
    rank = _ranks(c.perm, xs)
    if not _room(c, atts, rank):
        return Drawn(lost=tuple(Refused(c.line.member(lane_of.get(a.pole, a.pole)), (a.pin,)) for a, _ in atts))
    out = Drawn()
    for a, xy in atts:
        j = lane_of.get(a.pole, a.pole)
        out += drop_or_rise(env, c.line, a, xy, j) if j not in rank else Drawn(wires=(_crossed_wire(c, a, xy, (j, rank[j], xs[c.perm[j]], xs[j])),))
    return out


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
        return (Wire(line.net, t.page, ((t.x0, t.y), (t.x1, t.y)), "trunk"),) if t.x0 != t.x1 else ()
    return tuple(
        Wire(line.member(j), t.page, ((x0, line.y_of(j)), (x1, line.y_of(j))), "trunk", lane=j)
        for j, ends in enumerate(t.lane_ends)
        if ends is not None and ends[0] != ends[1]
        for x0, x1 in (ends,)
    )


def _leg_wires(env: RouteEnv, line: Line, lost: Collection[tuple[str, PinRef]]) -> tuple[Wire, ...]:
    """The leg of each one-sided pin of the trunk: out from the cut x along its lane, then down below the bundle (ONE-SIDED-PIN)."""
    t = line.trunk
    return tuple(
        Wire(line.member(pole), t.page, tuple(dict.fromkeys(env.leg_lines[t.fan, t.row, pin])), "straight")
        for pole, pin in leg_pins(line.fan, env.legs, t.row)
        if (line.member(pole), pin) not in lost
    )


def _lane(permuted: Mapping[str, tuple[int, ...]], a: Attach) -> int:
    """The lane an attachment drops to: its pole, or the lane a crossed function maps that pole to."""
    perm = permuted.get(a.pin.sym)
    return perm.index(a.pole) if perm and a.pole in perm else a.pole


def _withheld(env: RouteEnv, line: Line, permuted: Mapping[str, tuple[int, ...]]) -> tuple[set[tuple[str, PinRef]], set[int]]:
    """The (net, pin) pairs of lost conductors, and the lanes whose every attachment is lost (R2146)."""
    lost = {(net, p) for net, pins in env.lost for p in pins}
    atts = [(_lane(permuted, a), a) for a in (*line.fan.drivers, *line.fan.legs)]
    live = {j for j, a in atts if (line.member(j), a.pin) not in lost}
    return lost, {j for j, _ in atts} - live


def _lone_lanes(trunk: Trunk, placed: Sequence[Held]) -> frozenset[int]:
    """Lanes with one tap on this row and no length while another lane is drawn: its drop joins nothing (BUNDLE-LANE-END)."""
    if len(trunk.lane_ends) <= 1 or not any(e and e[0] != e[1] for e in trunk.lane_ends):
        return frozenset()  # one tap on the page: a TRUNK_END copy stands where its drop ends
    taps = Counter(a.pole for a, _ in placed)
    return frozenset(j for j, e in enumerate(trunk.lane_ends) if taps[j] == 1 and e is not None and e[0] == e[1])


def _lines(env: RouteEnv, line: Line, permuted: Mapping[str, tuple[int, ...]]) -> tuple[Drawn, set[tuple[str, PinRef]]]:
    """The trunk lines and legs of the conductors not lost, and the lost (net, pin) pairs."""
    lost, gone = _withheld(env, line, permuted)
    return Drawn(wires=tuple(w for w in _trunk_line(line) if (w.lane or 0) not in gone) + _leg_wires(env, line, lost)), lost


def _fan_of(env: RouteEnv, trunk: Trunk) -> Fan:
    """The trunk's fan, with every attachment's pole checked; a trunk with no fan is a bug to report."""
    if (fan := env.fans.get(trunk.fan)) is None:
        msg = f"trunk of fan {trunk.fan} has no fan in the flow, so it is not drawn: report it"
        raise CoreError(msg)
    _check_poles(fan)
    return fan


def trunk_wires(env: RouteEnv, trunk: Trunk) -> Drawn:
    """The trunk line, one drop per attachment on its row; a bundle's lane j drops from line j.

    A bundle's trunk carries the bundle id; each drop carries its member's id (layout-0297, D.7).
    A function in `fan.crossed` takes its lanes in another index order; crossed_drops draws it.
    """
    fan = _fan_of(env, trunk)
    line = Line(fan, trunk, fan.nets[0] if fan.lanes == 1 else fan.id, env.options.wiring_grid)
    permuted = dict(fan.crossed) if fan.lanes > 1 else {}
    out, lost = _lines(env, line, permuted)
    held: dict[tuple[str, bool], list[Held]] = {}
    lone = _lone_lanes(trunk, placed := _placed_attachments(env, line, env.bands[trunk.row]))
    for a, xy in placed:
        if (line.member(_lane(permuted, a)), a.pin) in lost:
            continue  # a lost conductor lays no drop (R2146)
        if a.pin.sym in permuted:
            held.setdefault((a.pin.sym, xy[1] < trunk.y), []).append((a, xy))
        elif a.pole not in lone:
            out += drop_or_rise(env, line, a, xy, a.pole)
    for (sym, above), atts in sorted(held.items()):
        out += crossed_drops(env, Crossed(line, permuted[sym], above), atts)
    return out
