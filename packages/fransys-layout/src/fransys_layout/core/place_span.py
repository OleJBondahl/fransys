"""Stage 5, spans: the solved top and bottom of each column and block of a page (layout-0374).

One measure for the recut: the footprints the solve placed, the anchors' boxes and the solved
band of every trunk attached to a column in its row. A column is never its block's extent
(layout-0298), but its own trunks count. Plain values out; the recut reads them and names no kind.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import TYPE_CHECKING

from .band import trunk_room
from .room import Room
from .row_extent import extent

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .outputs import Placed, Trunk
    from .place_env import PageEnv
    from .values import Block, Options

Span = tuple[int, int]


def _hull(spans: Sequence[Span]) -> Span:
    return min(a for a, _ in spans), max(b for _, b in spans)


def _foot(p: Placed, options: Options, room: Room) -> Span:
    """The G the row holds for a placed symbol: `extent` of its footprint about its origin."""
    up, down = extent(replace(p.footprint, y=p.footprint.y - p.y), room, options)
    return p.y - up, p.y + down


def _band(t: Trunk, grid: int) -> Span:
    """The G the solve holds about a trunk line, as it holds it (R409)."""
    above, below = trunk_room(t.lanes, grid)
    return t.y - above, t.y + below


def _column_span(
    env: PageEnv, col: str, feet: Mapping[str, Span], mine: Sequence[Trunk]
) -> Span | None:
    syms = {c.sym for lane in env.pcs[col].lanes for c in lane}
    own = [feet[s] for s in syms if s in feet]
    return _hull([*own, *(_band(t, env.options.wiring_grid) for t in mine)]) if own else None


def _row_of(env: PageEnv, block: Block) -> int:
    rows = [env.pcs[c].row for c in block.columns if c in env.pcs]
    if rows:
        return rows[0]
    return next((r for r, row in enumerate(env.plan.rows) if block.id in row.blocks), 0)


def _fan_columns(env: PageEnv) -> dict[str, set[str]]:
    by_col: dict[str, set[str]] = {}
    for fan in env.flow.fans:
        for a in (*fan.drivers, *fan.legs):
            if a.column:
                by_col.setdefault(a.column, set()).add(fan.id)
    return by_col


def _held(env: PageEnv, block: Block, trunks: tuple[Trunk, ...]) -> list[Span]:
    """The trunks of the block's row that join a pin of its anchor, to the line the solve keeps."""
    fans = {
        f.id for f in env.flow.fans if any(a.pin.sym == block.anchor for a in (*f.drivers, *f.legs))
    }
    grid, row = env.options.wiring_grid, _row_of(env, block)
    return [_band(t, grid) for t in trunks if block.anchor and t.row == row and t.fan in fans]


def _block_span(
    env: PageEnv,
    block: Block,
    columns: Mapping[str, Span],
    feet: Mapping[str, Span],
    trunks: tuple[Trunk, ...],
) -> Span | None:
    own = [columns[c] for c in block.columns if c in columns]
    if box := feet.get(block.anchor or ""):
        own.append(box)
    if not own:
        return None
    bands = (_band(t, env.options.wiring_grid) for t in trunks if block.fan == t.fan)
    return _hull([*own, *bands, *_held(env, block, trunks)])


def solved_spans(
    env: PageEnv,
    placed: Mapping[str, Placed],
    trunks: tuple[Trunk, ...],
    tops: Sequence[int] = (),
    rooms: Mapping[str, Room] = MappingProxyType({}),
) -> dict[str, Span]:
    """Column id and block id to (top, bottom) in G from the solve, as offsets from the row top.

    `rooms` is the G each symbol's drawn things reach beyond its footprint; the span holds it.
    """
    by_col = _fan_columns(env)
    feet = {s: _foot(p, env.options, rooms.get(s, Room())) for s, p in placed.items()}
    columns = {}
    for c, pc in env.pcs.items():
        mine = [t for t in trunks if t.row == pc.row and t.fan in by_col.get(c, ())]
        if span := _column_span(env, c, feet, mine):
            columns[c] = span
    rows = {c: env.pcs[c].row for c in columns}
    blocks = {b.id: _block_span(env, b, columns, feet, trunks) for b in env.blocks.values()}
    rows |= {b.id: _row_of(env, b) for b in env.blocks.values() if blocks[b.id]}
    return {
        key: (a - (top := tops[rows[key]] if rows[key] < len(tops) else 0), b - top)
        for key, (a, b) in {**columns, **{k: v for k, v in blocks.items() if v}}.items()
    }
