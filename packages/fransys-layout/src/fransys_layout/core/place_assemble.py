"""Stage 5, assemble: the solved x and y of a page become its Placed symbols, gaps and trunks."""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from .anchor_rooms import anchor_rooms
from .arrow_reserve import arrow_ends, reserve
from .band import lane_offset
from .geometry import (
    box_reach,
    cell_anchor,
    cell_footprint,
    column_extent,
    pin_xy,
    shift,
    view_of,
)
from .keys import natural_key
from .node_names import HIGH, LOW, box_node, box_y_node, col_node
from .outputs import Gap, PagePlacement, PinXY, Placed, Trunk
from .pack import cell_node
from .place_span import solved_spans
from .place_trunk import box_pin_x, in_row, trunk_node
from .values import Box, Lane

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from .pack import PlacedColumn
    from .place_env import PageEnv
    from .room import Room
    from .values import Attach, Cell, Fan


def _placed_cell(env: PageEnv, cell: Cell, ox: int, oy: int) -> Placed:
    """A cell's symbol with its origin at (ox, oy): body, footprint and pins all absolute."""
    sym = env.syms[cell.sym]
    body = shift(view_of(sym, cell.orient).body, ox, oy)
    fp = shift(cell_footprint(sym, cell, in_row=cell.sym in env.in_row), ox, oy)
    offsets = {p.id: pin_xy(sym, cell, p.id) for p in sym.pins}
    pins = tuple(PinXY(pin, ox + dx, oy + dy) for pin, (dx, dy) in offsets.items())
    return Placed(sym.id, env.plan.page, ox, oy, cell.orient, body, fp, pins)


def _cells(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int]) -> dict[str, Placed]:
    """Every cell once: a symbol spanning lanes stands where its first lane puts it."""
    out: dict[str, Placed] = {}
    for pc in env.pcs.values():
        for lane, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                if cell.sym not in out:
                    ax, _ = cell_anchor(env.syms[cell.sym], cell)
                    ox = x[col_node(pc.id)] + pc.offsets[lane] - ax
                    out[cell.sym] = _placed_cell(env, cell, ox, y[cell_node(pc.id, lane, i)])
    return out


def _box_pins(
    env: PageEnv, box: str, edges: Mapping[str, str], x: Mapping[str, int], oy: int
) -> tuple[PinXY, ...]:
    """Movable pins at their solved x on the edge they are used on; others at their offset."""
    sym = env.syms[box]
    edge_y = {"N": sym.body.y, "S": sym.body.y + sym.body.h}
    return tuple(
        PinXY(p.id, box_pin_x(env, x, box, p.id), oy + edge_y.get(edges.get(p.id, ""), p.dy))
        for p in sym.pins
    )


def _placed_box(
    env: PageEnv, box: str, edges: Mapping[str, str], x: Mapping[str, int], oy: int
) -> Placed:
    """A box spans its solved left to right edge; its footprint grows with the body."""
    sym = env.syms[box]
    left, right = x[box_node(box, LOW)], x[box_node(box, HIGH)]
    body = Box(left, oy + sym.body.y, right - left, sym.body.h)
    lead, tail = box_reach(sym)
    fp = sym.footprint
    grown = Box(left - lead, oy + fp.y, right - left + lead + tail, fp.h)
    pins = _box_pins(env, box, edges, x, oy)
    return Placed(box, env.plan.page, left - sym.body.x, oy, "R0", body, grown, pins)


def _boxes(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int]) -> dict[str, Placed]:
    out: dict[str, Placed] = {}
    for row in env.plan.rows:
        for b in (env.blocks[name] for name in row.blocks):
            if b.is_card and b.anchor:
                oy = y[box_y_node(b.anchor)]
                out[b.anchor] = _placed_box(env, b.anchor, dict(b.pin_edges), x, oy)
    return out


def _extent(env: PageEnv, pc: PlacedColumn) -> tuple[int, int]:
    lanes = tuple(Lane(cells, off) for cells, off in zip(pc.lanes, pc.offsets, strict=True))
    return column_extent(env.syms, lanes, env.in_row)


def _row_bounds(env: PageEnv, y: Mapping[str, int], r: int) -> tuple[int, int]:
    return y[f"row:{r}"], y[f"row:{r + 1}"] - env.options.row_gap


def _gaps(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int]) -> tuple[Gap, ...]:
    """One gap per pair of neighbouring columns of a row, between their facing footprints."""
    out = []
    for r, row in enumerate(env.plan.rows):
        top, bottom = _row_bounds(env, y, r)
        ordered = sorted(row.columns, key=lambda c: x[col_node(c)])
        for k, (a, b) in enumerate(pairwise(ordered)):
            x0 = x[col_node(a)] + _extent(env, env.pcs[a])[1]
            x1 = x[col_node(b)] + _extent(env, env.pcs[b])[0]
            out.append(
                Gap(f"g:{env.plan.page}:{r}:{k}", env.plan.page, a, b, x0, x1, 0, top, bottom)
            )
    return tuple(out)


def _attach_x(
    env: PageEnv, a: Attach, placed: Mapping[str, Placed], x: Mapping[str, int]
) -> int | None:
    """The x of a trunk's attachment (`in_row` holds): a column's lane wire or a box pin."""
    here = placed.get(a.pin.sym)
    pin = next((q.x for q in here.pin_xy if q.pin == a.pin.pin), None) if here else None
    if a.column is None or pin is not None:
        return pin
    pc = env.pcs[a.column]
    return x[col_node(pc.id)] + pc.offsets[a.lane]


def _taps(
    env: PageEnv, fan: Fan, r: int, placed: Mapping[str, Placed], x: Mapping[str, int]
) -> tuple[tuple[Attach, int], ...]:
    """Each attachment of the fan standing in row r with its x."""
    out = []
    for a in (*fan.drivers, *fan.legs):
        at = _attach_x(env, a, placed, x) if in_row(env, fan, a, r) else None
        if at is not None:
            out.append((a, at))
    return tuple(out)


def _hull(xs: Sequence[int]) -> tuple[int, int] | None:
    return (min(xs), max(xs)) if xs else None


def _lane_ends(
    fan: Fan,
    taps: Sequence[tuple[Attach, int]],
    away: Collection[int] = (),
    arrows: tuple[int, int] = (0, 0),
    reach: int = 0,
) -> tuple[tuple[int, int] | None, ...]:
    """Per lane j the hull of the taps of pole j; a plain fan's one lane takes them all.

    A lane in `away` (its net continues off the page) runs `reach` past the hull where an arrow
    stands, `arrows` being the (left, right) counts; a `crossed` fan keeps the hull on every lane.
    """
    hull = _hull([v for _, v in taps])
    if fan.lanes == 1 or fan.crossed:
        return (hull,) * fan.lanes
    out = []
    for j in range(fan.lanes):
        own = _hull([v for a, v in taps if a.pole == j])
        if own and hull and j in away:
            own = (
                hull[0] - reach if arrows[0] else own[0],
                hull[1] + reach if arrows[1] else own[1],
            )
        out.append(own)
    return tuple(out)


def _continuing(fan: Fan, placed: Mapping[str, Placed]) -> frozenset[int]:
    """The poles with an attachment off this page: their nets continue past the cut."""
    return frozenset(a.pole for a in (*fan.drivers, *fan.legs) if a.pin.sym not in placed)


def _trunks(
    env: PageEnv, placed: Mapping[str, Placed], x: Mapping[str, int], y: Mapping[str, int]
) -> tuple[Trunk, ...]:
    """One trunk per fan and row it touches, from its leftmost to its rightmost attachment."""
    out = []
    for fan in env.flow.fans:
        for r in range(len(env.plan.rows)):
            node = trunk_node(fan.id, r)
            taps = _taps(env, fan, r, placed, x) if node in y else ()
            if span := _hull([v for _, v in taps]):
                arrows = arrow_ends(env.refs, env.plan.page, r, fan.id)
                ends = _lane_ends(
                    fan,
                    taps,
                    _continuing(fan, placed),
                    arrows,
                    lane_offset(1, env.options.wiring_grid),
                )
                out.append(
                    Trunk(fan.id, env.plan.page, y[node], span[0], span[1], fan.lanes, r, ends)
                )
    return tuple(out)


def _rows(
    env: PageEnv, placed: Mapping[str, Placed], y: Mapping[str, int]
) -> tuple[tuple[int, int], ...]:
    """(height, width) of each row: the row's span in y, its placed footprints' span in x."""
    out = []
    for r, row in enumerate(env.plan.rows):
        syms = {c.sym for pc in env.pcs.values() if pc.row == r for ln in pc.lanes for c in ln}
        syms |= {env.blocks[b].anchor or "" for b in row.blocks if env.blocks[b].is_card}
        fps = [placed[s].footprint for s in syms if s in placed]
        top, bottom = _row_bounds(env, y, r)
        width = max(f.x + f.w for f in fps) - min(f.x for f in fps) if fps else 0
        left, right = arrow_ends(env.refs, env.plan.page, r)
        width += reserve(left, env.options) + reserve(right, env.options)
        out.append((bottom - top, width))
    return tuple(out)


def placed_rooms(env: PageEnv, x: Mapping[str, int]) -> Mapping[str, Room]:
    """The anchors' rooms of the page's symbols at `x`: a room is an offset, so any y gives it."""
    zero: defaultdict[str, int] = defaultdict(int)
    return anchor_rooms(env.problem, {**_cells(env, x, zero), **_boxes(env, x, zero)})


def assemble(
    env: PageEnv,
    x: Mapping[str, int],
    y: Mapping[str, int],
) -> PagePlacement:
    """The page's Placed symbols (by natural id order), gaps with no tracks yet, trunks, rows."""
    placed = {**_cells(env, x, y), **_boxes(env, x, y)}
    ordered = tuple(placed[k] for k in sorted(placed, key=natural_key))
    bands = tuple(_row_bounds(env, y, r) for r in range(len(env.plan.rows)))
    trunks = _trunks(env, placed, x, y)
    spans = solved_spans(env, placed, trunks, [t for t, _ in bands], env.rooms)
    return PagePlacement(
        env.plan.page, ordered, _gaps(env, x, y), trunks, _rows(env, placed, y), bands, spans
    )
