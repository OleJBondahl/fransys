"""Stage 5, assemble: the solved x and y of a page become its Placed symbols, gaps and trunks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from .arrow_reserve import arrow_rows, lead_reserve, leg_feet, leg_fit, leg_lines, leg_rows, row_arrows, row_legs
from .clearance import footprint_keeps
from .flow_values import Lane
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
from .place_lanes import _hull, _marker_keeps, drawn_lane_ends, stand_of, taps_x
from .place_span import solved_spans
from .place_trunk import box_pin_x, held_room, trunk_node
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .clearance import Keep
    from .flow_values import Cell, Fan
    from .pack import PlacedColumn
    from .place_env import PageEnv
    from .place_lanes import Taps


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


def _box_pins(env: PageEnv, box: str, edges: Mapping[str, str], x: Mapping[str, int], oy: int) -> tuple[PinXY, ...]:
    """Movable pins at their solved x on the edge they are used on; others at their offset."""
    sym = env.syms[box]
    edge_y = {"N": sym.body.y, "S": sym.body.y + sym.body.h}
    return tuple(PinXY(p.id, box_pin_x(env, x, box, p.id), oy + edge_y.get(edges.get(p.id, ""), p.dy)) for p in sym.pins)


def _placed_box(env: PageEnv, box: str, edges: Mapping[str, str], x: Mapping[str, int], oy: int) -> Placed:
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
            out.append(Gap(f"g:{env.plan.page}:{r}:{k}", env.plan.page, a, b, x0, x1, 0, top, bottom))
    return tuple(out)


_Ctx = tuple["Sequence[Keep]", "Sequence[tuple[Fan, int, int, Taps]]", "Mapping[str, Placed]", "Mapping[str, int]", "Mapping[str, int]"]


def _trunk(env: PageEnv, ctx: _Ctx, at: int, drop: int) -> Trunk | None:
    """The trunk of the `at`th fan and row of `ctx` = (feet, tapped, placed, x, y), its arrow standing at or past the leg `drop` x."""
    feet, tapped, placed, x, y = ctx
    fan, r, ty, ts = tapped[at]
    if not (span := _hull([v for _, v, _ in ts])):
        return None
    others = [(f.id, t, c) for f, _, t, c in tapped if f is not fan]
    lanes = drawn_lane_ends(env, x, fan, r, stand_of(env, (ty, _row_bounds(env, y, r)), feet, placed, others)._replace(drop=drop))
    x0, x1 = lanes.ends[0] if fan.lanes == 1 and lanes.ends[0] else span
    return Trunk(fan.id, env.plan.page, ty, x0, x1, fan.lanes, r, *lanes, room=held_room(fan, env, r))


def _drops(env: PageEnv, trunks: Sequence[Trunk], feet: Sequence[Box]) -> dict[tuple[str, int], int]:
    """Per (fan, row) the x of its last placed leg drop: the legs placed first, as the router draws them (BUNDLE-LEGS)."""
    page, opts = env.plan.page, env.options
    fans = {f.id: f for f in env.flow.fans}
    around = (feet, arrow_rows(env.refs, [env.plan], env.flow.fans), env.problem.area)
    out: dict[tuple[str, int], int] = {}
    for (fan, row, _), line in leg_lines(trunks, fans, leg_rows(env.refs, page), leg_fit(opts, env.refs, page), around).items():
        out[fan, row] = max(out.get((fan, row), 0), line[1][0])
    return out


def _trunks(
    env: PageEnv, placed: Mapping[str, Placed], xy: tuple[Mapping[str, int], Mapping[str, int]], shown: Mapping[str, Placed], marks: Sequence[Keep]
) -> tuple[Trunk, ...]:
    """One trunk per fan and row it touches, from its leftmost to its rightmost attachment; `shown` holds the drawn footprints.

    The legs are placed on a first pass, clear of the footprints and the hangings (`marks`); a trunk whose last leg drop lies past its
    arrow's lane end is stood again at the drop.
    """
    x, y = xy
    feet = (*(k for s, p in shown.items() for k in footprint_keeps((("", s),), p.footprint)), *marks)
    rows = range(len(env.plan.rows))
    tapped = [(f, r, y[n], taps_x(env, x, f, r, placed)) for f in env.flow.fans for r in rows if (n := trunk_node(f.id, r)) in y]
    ctx = (feet, tapped, placed, x, y)
    out = [_trunk(env, ctx, i, 0) for i in range(len(tapped))]
    drops = _drops(env, [t for t in out if t], leg_feet(shown.values(), _hung(marks)))
    return tuple(t for i, t0 in enumerate(out) if (t := _stood(env, ctx, i, t0, drops.get((tapped[i][0].id, tapped[i][1]), 0))))


def _stood(env: PageEnv, ctx: _Ctx, at: int, trunk: Trunk | None, drop: int) -> Trunk | None:
    """`trunk` stood again at the leg `drop` x when its arrow's lane end lies short of it."""
    return _trunk(env, ctx, at, drop) if trunk and drop + env.options.wiring_grid > max((e[1] for e in trunk.lane_ends if e), default=0) else trunk


def _rows(env: PageEnv, placed: Mapping[str, Placed], y: Mapping[str, int]) -> tuple[tuple[int, int], ...]:
    """(height, width) of each row: the row's span in y, its placed footprints' span in x."""
    out = []
    for r, row in enumerate(env.plan.rows):
        syms = {c.sym for pc in env.pcs.values() if pc.row == r for ln in pc.lanes for c in ln}
        syms |= {env.blocks[b].anchor or "" for b in row.blocks if env.blocks[b].is_card}
        fps = [placed[s].footprint for s in syms if s in placed]
        top, bottom = _row_bounds(env, y, r)
        width = max(f.x + f.w for f in fps) - min(f.x for f in fps) if fps else 0
        left, right = row_arrows(env.refs, env.plan, env.blocks, env.flow.fans, r)
        width += lead_reserve(left, env.options) + lead_reserve(right, env.options) + row_legs(env.refs, env.plan, env.flow.fans, r, env.options)
        out.append((bottom - top, width))
    return tuple(out)


def placed_at(env: PageEnv, x: Mapping[str, int]) -> dict[str, Placed]:
    """The page's symbols placed at `x`; a flag's fold reads only x, so every y is 0."""
    zero: defaultdict[str, int] = defaultdict(int)
    return {**_cells(env, x, zero), **_boxes(env, x, zero)}


def assemble(
    env: PageEnv,
    x: Mapping[str, int],
    y: Mapping[str, int],
) -> PagePlacement:
    """The page's Placed symbols (by natural id order), gaps with no tracks yet, trunks, rows."""
    placed = {**_cells(env, x, y), **_boxes(env, x, y)}
    shown = replace(env, syms=env.bare) if env.bare else env
    seen = {**_cells(shown, x, y), **_boxes(shown, x, y)}
    ordered = tuple(seen[k] for k in sorted(seen, key=natural_key))
    bands = tuple(_row_bounds(env, y, r) for r in range(len(env.plan.rows)))
    marks = tuple(_marker_keeps(env, placed))
    trunks = _trunks(env, placed, (x, y), seen, marks)
    spans = solved_spans(env, placed, trunks, [t for t, _ in bands])
    return PagePlacement(env.plan.page, ordered, _gaps(env, x, y), trunks, _rows(env, placed, y), bands, spans, _hung(marks))


def _hung(marks: Iterable[Keep]) -> dict[str, tuple[Box, ...]]:
    """The hanging boxes by owner symbol: `PagePlacement.hangings` (layout-0547)."""
    hung: dict[str, tuple[Box, ...]] = {}
    for k in marks:
        hung[k.owner] = (*hung.get(k.owner, ()), k.box)
    return hung
