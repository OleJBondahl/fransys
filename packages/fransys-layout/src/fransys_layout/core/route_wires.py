"""Stage 6 wires of a column: lane wires, chain hops, box wires, joins and jogs nested by E6."""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from .geometry import rotate_side
from .intervals import levels
from .keys import natural_key
from .outputs import Wire
from .route_env import Drawn, Jog, failed, pin_point, z_wire
from .sides import SIDE_STEP
from .values import PinRef

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .route_env import RouteEnv
    from .values import XY, Cell, Column, End


def straight_or_jog(net: str, page: int, a: XY, b: XY) -> Wire | Jog:
    """Straight when the ends share x or y; else a jog, nested later with its neighbours."""
    if a[0] == b[0] or a[1] == b[1]:
        return Wire(net, page, (a, b), "straight")
    top, bottom = (a, b) if a[1] <= b[1] else (b, a)
    return Jog(net, top, bottom)


def _pair(env: RouteEnv, net: str, a: PinRef, b: PinRef) -> Drawn | None:
    """The wire between two placed pins, or None when either is not placed."""
    pa, pb = pin_point(env, a.sym, a.pin), pin_point(env, b.sym, b.pin)
    if pa is None or pb is None:
        return None
    item = straight_or_jog(net, env.page, pa, pb)
    return Drawn(jogs=(item,)) if isinstance(item, Jog) else Drawn(wires=(item,))


def _refused(env: RouteEnv, subject: str, text: str) -> Drawn:
    return Drawn(findings=(failed(env, subject, text),))


def _between(env: RouteEnv, col: Column, i: int, cells: tuple[Cell, Cell]) -> Drawn:
    """The wire between two consecutive cells of lane i, joined at their facing pins."""
    a, b = cells
    if not (a.bottom_pin and b.top_pin):
        return Drawn()
    ref_a, ref_b = PinRef(a.sym, a.bottom_pin), PinRef(b.sym, b.top_pin)
    net, other = env.net_of.get(ref_a), env.net_of.get(ref_b)
    if net is None or other is None:
        return Drawn()  # a pin with no net of its own is reached by a trunk, not a lane wire
    if net != other:
        text = (
            f"cells {a.sym} and {b.sym} of lane {i} in column {col.id} are on different nets at "
            f"{a.bottom_pin} and {b.top_pin}, so no wire is drawn between them: put both pins "
            "on one net"
        )
        return _refused(env, col.id, text)
    return _pair(env, net, ref_a, ref_b) or Drawn()


def _lane_placed(env: RouteEnv, col: Column, i: int) -> list[str]:
    return [c.sym for c in col.lanes[i].cells if c.sym not in env.placed]


def _lane(env: RouteEnv, col: Column, i: int) -> Drawn:
    """Consecutive cells of lane i; a cell that is not on the page is a finding."""
    gone = _lane_placed(env, col, i)
    if gone:
        text = (
            f"lane {i} of column {col.id} has no placed cell for {', '.join(gone)}, so none of "
            "its wires is drawn: stage 5 must place every cell of a lane on one page; report "
            "the column"
        )
        return _refused(env, col.id, text)
    out = Drawn()
    for cells in pairwise(col.lanes[i].cells):
        out += _between(env, col, i, cells)
    return out


def _box_wire(env: RouteEnv, col: Column, slot: tuple[bool, int], end: End) -> Drawn:
    """The wire from an attached box pin to the lane's first (head) or last (foot) cell pin."""
    head, pos = slot
    i = end.lane if end.lane is not None else pos
    box = end.pin
    if box is None or i >= len(col.lanes):
        return _refused(env, col.id, f"column {col.id} has a box end for no lane: {pos}")
    cells = col.lanes[i].cells
    cell = cells[0] if head else cells[-1]
    pin = cell.top_pin if head else cell.bottom_pin
    if cell.sym not in env.placed:
        return Drawn()  # the lane's own finding names it
    net = env.net_of.get(box)
    if pin is None or net is None or env.net_of.get(PinRef(cell.sym, pin)) != net:
        text = (
            f"box {box.sym} pin {box.pin} shares no net with a pin of lane {i} in column "
            f"{col.id}, so no wire is drawn from it: wire it to a pin of that lane's end cell"
        )
        return _refused(env, box.sym, text)
    return _pair(env, net, box, PinRef(cell.sym, pin)) or _refused(
        env, box.sym, f"box {box.sym} is not placed on page {env.page}; place it or cut its net"
    )


def _end_wires(env: RouteEnv, col: Column) -> Drawn:
    """The wires of the ends: a box pin's wire to its lane, an open end's stub (one kind read)."""
    out = Drawn()
    for head, ends in ((True, col.heads), (False, col.feet)):
        for pos, end in enumerate(ends):
            kind = end.kind
            if kind == "boxpin":
                out += _box_wire(env, col, (head, pos), end)
            elif kind == "open":
                out += _stub(env, end)
    return out


def _hop_pin(env: RouteEnv, net: str, sym: str) -> PinRef | None:
    return next((r for r in env.net_pins.get(net, ()) if r.sym == sym), None)


def _hops(env: RouteEnv, col: Column) -> Drawn:
    """Every other net of a chain hop, from the pin on the box above to the pin on the box below."""
    out = Drawn()
    cells = col.lanes[0].cells if col.is_chain else ()
    for (a, b), nets in zip(pairwise(cells), col.hops, strict=False):
        anchored = env.net_of.get(PinRef(a.sym, a.bottom_pin or ""))
        for net in (n for n in nets if n != anchored):  # the lane's own wire draws the anchor
            pa, pb = _hop_pin(env, net, a.sym), _hop_pin(env, net, b.sym)
            drawn = _pair(env, net, pa, pb) if pa and pb else None
            out += drawn or _refused(
                env, net, f"net {net} has no placed pin on both {a.sym} and {b.sym}; wire the hop"
            )
    return out


def _stub(env: RouteEnv, end: End) -> Drawn:
    """A short wire out of the pin of an open end, along the pin's turned side (P4.1b).

    Drawn even where the target is blocked: the scorer counts any crossing, nothing is refused.
    """
    ref = end.pin
    if env.options.open_stub <= 0 or ref is None or end.net is None:
        return Drawn()
    placed = env.placed.get(ref.sym)
    start = pin_point(env, ref.sym, ref.pin)
    side = env.sides.get((ref.sym, ref.pin))
    if placed is None or start is None or side is None:
        text = (
            f"open end {ref.sym}.{ref.pin} of net {end.net} has no placed pin or side on page "
            f"{env.page}, so no stub is drawn: place {ref.sym} on this page or fix the pin name"
        )
        return _refused(env, end.net, text)
    dx, dy = SIDE_STEP[rotate_side(side, placed.orient)]
    n = env.options.open_stub
    stop = (start[0] + dx * n, start[1] + dy * n)
    return Drawn(wires=(Wire(end.net, env.page, (start, stop), "straight"),))


def lane_wires(env: RouteEnv, col: Column) -> Drawn:
    """A column's wires: between consecutive cells, to box pins, along chain hops, open stubs."""
    out = Drawn()
    for i in range(len(col.lanes)):
        out += _lane(env, col, i)
    return out + _end_wires(env, col) + _hops(env, col)


def _join_end(env: RouteEnv, col: Column, lane: int, which: tuple[int, End, str]) -> Drawn:
    """A member lane's join: level pins are one run, else a Z-wire nested with the jogs (E6)."""
    third, end, pin = which
    cell = col.lanes[lane].cells[0 if third == 1 else -1]
    a = pin_point(env, end.pin.sym, end.pin.pin) if end.pin else None
    m = pin_point(env, cell.sym, pin)
    if a is None or m is None or end.net is None or end.pin is None:
        return _refused(env, end.net or col.id, f"join of column {col.id} lane {lane}: pin gone")
    if a[1] == m[1]:
        return Drawn(wires=(Wire(end.net, env.page, (a, m), "join"),))
    top, bottom = (a, m) if a[1] < m[1] else (m, a)
    return Drawn(jogs=(Jog(end.net, top, bottom, "join", source_top=top is m),))


def join_wires(env: RouteEnv, col: Column) -> Drawn:
    """Each folded member lane is wired, at head and foot, to the pin its join End names."""
    out = Drawn()
    for i, lane in enumerate(col.lanes):
        head, foot = lane.cells[0], lane.cells[-1]
        for third, end, pin in ((1, col.heads[i], head.top_pin), (2, col.feet[i], foot.bottom_pin)):
            if end.is_join and pin is not None:
                out += _join_end(env, col, i, (third, end, pin))
    return out


def _stair(env: RouteEnv, key: tuple[int, int, bool], members: Sequence[Jog]) -> Drawn:
    """One group of jogs and joins between the same two pin levels, shifting the same way (E6).

    Nearest the top first: the end furthest along the shift turns highest, by source x, then by
    destination x. Spans that do not overlap in x share a level (`intervals.levels`).
    """
    y0, y1, left = key
    grid = env.options.wiring_grid
    ordered = sorted(
        members, key=lambda j: (j.source_x, j.dest_x, natural_key(j.net)), reverse=not left
    )
    spans = [(min(j.top[0], j.bottom[0]), max(j.top[0], j.bottom[0])) for j in ordered]
    level = levels(spans, range(len(ordered)))
    room = max((y1 - y0) // grid - 1, 1)
    wires = tuple(
        z_wire(j.net, env.page, (j.top, j.bottom), y0 + grid * (min(k, room - 1) + 1), j.drawn_as)
        for k, j in zip(level, ordered, strict=True)
    )
    over = [j for k, j in zip(level, ordered, strict=True) if k >= room]
    if not over:
        return Drawn(wires=wires)
    deep = max(level) + 1
    nets = ", ".join(j.net for j in ordered)
    text = (
        f"{len(ordered)} jogs ({nets}) between pin levels {y0} and {y1} have {room} turn "
        f"levels and overlapping spans need {deep}, so the last ones share a horizontal and "
        f"overlap: raise Options.wire_min to {grid * (deep + 1)}"
    )
    return Drawn(wires=wires, findings=(failed(env, over[0].net, text),))


def nest_jogs(env: RouteEnv, jogs: Sequence[Jog]) -> Drawn:
    """E6: jogs between the same levels that shift one way nest; the outermost source turns highest.

    Shifting left the furthest-left source turns highest, shifting right the furthest-right one.
    """
    groups: dict[tuple[int, int, bool], list[Jog]] = defaultdict(list)
    for j in jogs:
        groups[(j.top[1], j.bottom[1], j.bottom[0] < j.top[0])].append(j)
    out = Drawn()
    for key in sorted(groups):
        out += _stair(env, key, groups[key])
    return out
