"""Stage 6 wires of a column: lane wires, chain hops, box wires, joins and jogs nested by E6."""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from .clearance import pin_points, through_keeps
from .errors import CoreError
from .flow_values import hop_wires
from .geometry import stair_room
from .intervals import levels
from .jog_rows import bend_rows, taken_rows
from .keys import natural_key
from .net_keys import net_of_key
from .outputs import Refused, Wire
from .route_bend import bend_side
from .route_env import Drawn, Jog, body_hit, hard_keeps, own_syms, pin_point, z_wire
from .sides import step_out
from .values import Box, Finding, PinRef

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import NoReturn

    from .clearance import Keep
    from .flow_values import Cell, Column, End
    from .jog_rows import Taken
    from .route_env import RouteEnv
    from .values import XY


def straight_or_jog(net: str, page: int, a: XY, b: XY, ends: tuple[PinRef, ...]) -> Wire | Jog:
    """Straight when the ends share x or y; else a jog, nested later with its neighbours."""
    if a[0] == b[0] or a[1] == b[1]:
        return Wire(net, page, (a, b), "straight")
    top, bottom = (a, b) if a[1] <= b[1] else (b, a)
    return Jog(net, top, bottom, ends=ends)


def _pair(env: RouteEnv, net: str, a: PinRef, b: PinRef) -> Drawn | None:
    """The wire between two placed pins, or None when either is not placed."""
    pa, pb = pin_point(env, a.sym, a.pin), pin_point(env, b.sym, b.pin)
    if pa is None or pb is None:
        return None
    item = straight_or_jog(net, env.page, pa, pb, (a, b))
    return Drawn(jogs=(item,)) if isinstance(item, Jog) else Drawn(wires=(item,))


def _box_pair(env: RouteEnv, net: str, box: PinRef, cell: PinRef) -> Drawn | None:
    """A box pin's wire to a cell pin below it: long on the box's pin column, in by the pin's side.

    A jog nested from the top would run its long vertical on the lane's own pin column, through
    the lane's cells (SHORTS-ROUTE, layout-0381).
    """
    pb, pc = pin_point(env, box.sym, box.pin), pin_point(env, cell.sym, cell.pin)
    placed = env.placed.get(cell.sym)
    side = None if placed is None else env.sides.get((cell.sym, cell.pin, placed.orient))
    if pb is None or pc is None or side not in ("N", "S") or pb[0] == pc[0] or pb[1] >= min(pc[1], step_out(side, *pc, env.options.wiring_grid)[1]):
        return _pair(env, net, box, cell)
    stub = step_out(side, *pc, env.options.wiring_grid)
    x = _column_clear_of_bodies(env, pb, pc, stub[1])
    turn = pb[1] + env.options.wiring_grid  # one grid down the pin's own column: the jog never runs along the box's outline
    points = (pb, (pb[0], turn), (x, turn), (x, stub[1]), stub, pc) if x != pb[0] else (pb, (x, stub[1]), stub, pc)
    if body_hit(env, net, points):
        return Drawn(lost=(Refused(net, (box, cell)),))  # the long way round is the router's: a body stands on it (R1290 ii)
    return Drawn(wires=(Wire(net, env.page, points, "straight"),))


def _column_clear_of_bodies(env: RouteEnv, pb: XY, pc: XY, bottom: int) -> int:
    """The x of the long vertical: the box pin's column, moved one grid past each body outline it would lie on (R1146, layout-0480)."""
    bodies, x = tuple(k for k in hard_keeps(env) if k.kind == "body"), pb[0]
    while hit := through_keeps(Box(x, pb[1], 0, bottom - pb[1]), bodies, (pb, pc), frozenset(), pin_points(env.placed)):
        x = hit[0].box.x + hit[0].box.w + env.options.wiring_grid
    return x


def _refused(text: str) -> NoReturn:
    """A cell, pin or net the placement and the flow disagree on: a bug upstream, never a lost wire."""
    raise CoreError(text)


def _dropped(env: RouteEnv, col: Column, i: int, cells: tuple[Cell, Cell], why: str) -> Drawn:
    """A finding for two consecutive cells that get no wire (R324): the cells and the cause."""
    a, b = cells
    text = f"cells {a.sym} and {b.sym} of lane {i} in column {col.id}: {why}, so no wire is drawn between them"
    return Drawn(findings=(Finding("LANE_WIRE_DROPPED", text, env.page, a.sym),))


def _between(env: RouteEnv, col: Column, i: int, cells: tuple[Cell, Cell]) -> Drawn:
    """The wire between two consecutive cells of lane i, joined at their facing pins."""
    a, b = cells
    if not (a.bottom_pin and b.top_pin):
        return _dropped(env, col, i, cells, "has no pin facing the other")
    ref_a, ref_b = PinRef(a.sym, a.bottom_pin), PinRef(b.sym, b.top_pin)
    net, other = env.net_of.get(ref_a), env.net_of.get(ref_b)
    if net is None or other is None:
        return _dropped(env, col, i, cells, "has a facing pin on no net")
    if net != other:
        text = (
            f"cells {a.sym} and {b.sym} of lane {i} in column {col.id} are on different nets at "
            f"{a.bottom_pin} and {b.top_pin}, so no wire is drawn between them: put both pins "
            "on one net"
        )
        return _refused(text)
    if (net, ref_a, ref_b) in env.dealt:
        return Drawn()  # the fan's trunk draws this connection (R1519)
    return _pair(env, net, ref_a, ref_b) or Drawn()


def _lane(env: RouteEnv, col: Column, i: int) -> Drawn:
    """Consecutive cells of lane i; a cell that is not on the page is a finding."""
    gone = [c.sym for c in col.lanes[i].cells if c.sym not in env.placed]
    if gone:
        text = (
            f"lane {i} of column {col.id} has no placed cell for {', '.join(gone)}, so none of "
            "its wires is drawn: stage 5 must place every cell of a lane on one page; report "
            "the column"
        )
        return _refused(text)
    out = Drawn()
    for cells in pairwise(col.lanes[i].cells):
        if frozenset((cells[0].sym, cells[1].sym)) not in env.joined:  # a join the router draws is no lane wire (layout-0482)
            out += _between(env, col, i, cells)
    return out


def _box_wire(env: RouteEnv, col: Column, slot: tuple[bool, int], end: End) -> Drawn:
    """The wire from an attached box pin to the lane's first (head) or last (foot) cell pin."""
    head, pos = slot
    i = end.lane if end.lane is not None else pos
    box = end.pin
    if box is None or i >= len(col.lanes):
        return _refused(f"column {col.id} has a box end for no lane: {pos}")
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
        return _refused(text)
    if net in env.cut_nets and box.sym not in env.placed:
        return Drawn()  # a spilled column's box stands on another page: the tag pair is the join
    return _box_pair(env, net, box, PinRef(cell.sym, pin)) or _refused(f"box {box.sym} is not placed on page {env.page}; place it or cut its net")


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


def _hops(env: RouteEnv, col: Column) -> Drawn:
    """Every other net of a chain hop, from the pin on the box above to the pin on the box below."""
    out = Drawn()
    for _, a, b, net, pa, pb in hop_wires(col, env.net_of, env.net_pins):
        drawn = _pair(env, net, pa, pb) if pa and pb else None
        out += drawn or _refused(f"net {net} has no placed pin on both {a.sym} and {b.sym}; wire the hop")
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
    side = None if placed is None else env.sides.get((ref.sym, ref.pin, placed.orient))
    if placed is None or start is None or side is None:
        text = (
            f"open end {ref.sym}.{ref.pin} of net {end.net} has no placed pin or side on page "
            f"{env.page}, so no stub is drawn: place {ref.sym} on this page or fix the pin name"
        )
        return _refused(text)
    stop = step_out(side, *start, env.options.open_stub)
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
        return _refused(f"join of column {col.id} lane {lane}: pin gone")
    if a[1] == m[1]:
        return Drawn(wires=(Wire(end.net, env.page, (a, m), "join"),))
    top, bottom = (a, m) if a[1] < m[1] else (m, a)
    return Drawn(jogs=(Jog(end.net, top, bottom, "join", source_top=top is m, ends=(end.pin, PinRef(cell.sym, pin))),))


def join_wires(env: RouteEnv, col: Column) -> Drawn:
    """Each folded member lane is wired, at head and foot, to the pin its join End names.

    A join with no net only stands the lane level with that pin's cell: no wire is drawn.
    """
    out = Drawn()
    for i, lane in enumerate(col.lanes):
        head, foot = lane.cells[0], lane.cells[-1]
        for third, end, pin in ((1, col.heads[i], head.top_pin), (2, col.feet[i], foot.bottom_pin)):
            if end.is_join and pin is not None and end.net is not None:
                out += _join_end(env, col, i, (third, end, pin))
    return out


def _rows(env: RouteEnv, key: tuple[int, int, bool, int], count: int) -> list[int]:
    """The y of each bend row a stair may take, nearest the pins first: between them, or beyond the two pins that face away from it."""
    y0, y1, _, side = key
    grid, area = env.options.wiring_grid, env.area
    if side == 0:
        return [y0 + grid * (r + 1) for r in range(stair_room(y0, y1, grid))]
    reach = count if area is None else (area.h - y1 if side > 0 else y0) // grid
    return [(y1 if side > 0 else y0) + side * grid * (r + 1) for r in range(reach)]


def _stair(env: RouteEnv, key: tuple[int, int, bool, int], members: Sequence[Jog], taken: Sequence[Taken], keeps: Sequence[Keep]) -> Drawn:
    """One group of jogs and joins between the same two pin levels, shifting the same way (E6).

    Nearest the top first: the end furthest along the shift turns highest, by source x, then by
    destination x; spans that do not overlap share a level. Same-facing pins bend beyond them (layout-0541).
    """
    left, side = key[2], key[3]
    ordered = sorted(
        members,
        key=lambda j: (*((j.source_x, j.dest_x) if side == 0 else (abs(j.top[0] - j.bottom[0]), j.source_x)), natural_key(j.net)),
        reverse=side == 0 and not left,
    )
    spans = [(min(j.top[0], j.bottom[0]), max(j.top[0], j.bottom[0])) for j in ordered]
    level = levels(spans, range(len(ordered)))
    ys = _rows(env, key, len(ordered))
    by_level = [
        [(*s, own_syms(env, net_of_key(j.net), j.net)) for k, s, j in zip(level, spans, ordered, strict=True) if k == n]
        for n in range(max(level) + 1)
    ]
    rows = bend_rows(ys, by_level, taken, keeps, grid=env.options.wiring_grid)
    kept = [(row, j) for k, j in zip(level, ordered, strict=True) if (row := rows[k]) is not None]
    laid = [(j, z_wire(j.net, env.page, (j.top, j.bottom), ys[row], j.drawn_as)) for row, j in kept]
    hit = [
        body_hit(env, w.net, w.points) is not None for _, w in laid
    ]  # a Z through any body, its own pins' too, is the router's loss, not a drawn wire (R1290 ii, layout-0541)
    wires = tuple(w for (_, w), h in zip(laid, hit, strict=True) if not h)
    lost = tuple(Refused(j.net, j.ends) for k, j in zip(level, ordered, strict=True) if rows[k] is None)
    return Drawn(wires=wires, lost=lost + tuple(Refused(j.net, j.ends) for (j, _), h in zip(laid, hit, strict=True) if h))


def nest_jogs(env: RouteEnv, jogs: Sequence[Jog], taken: Sequence[Taken] = (), keeps: Sequence[Keep] = ()) -> Drawn:
    """E6: jogs between the same levels that shift one way nest; the outermost source turns highest.

    A bend row on a `taken` run, a jog's end point (R1520) or a `keeps` footprint moves to the next free row (R428).
    Pins facing away from each other are lost to the loop (layout-0541).
    """
    groups: dict[tuple[int, int, bool, int], list[Jog]] = defaultdict(list)
    out = Drawn()
    for j in jogs:
        if (side := bend_side(env, j)) is None:
            out += Drawn(lost=(Refused(j.net, j.ends),))
        else:
            groups[(j.top[1], j.bottom[1], j.bottom[0] < j.top[0], side)].append(j)
    held = [*taken, *((p[1], p[0], p[0]) for j in jogs for p in (j.top, j.bottom))]
    for key in sorted(groups):
        laid = _stair(env, key, groups[key], held, keeps)
        held += taken_rows([s for w in laid.wires for s in pairwise(w.points)])
        out += laid
    return out
