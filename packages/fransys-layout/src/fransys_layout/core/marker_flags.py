"""The flags over a page's top and bottom pins, and the room their stagger takes (layout-0375).

Each flag stands one box out per overlapping flag before it (`text_markers.stagger`); this counts
that from the placed pins, so the solve keeps the room and the recut's spans see it (R362, R384).
"""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
from types import MappingProxyType
from typing import TYPE_CHECKING, NamedTuple

from . import intervals
from .marker_room import row_rooms
from .node_names import col_node
from .place_trunk import box_pin_x
from .ref_kind import kind_of
from .room import Room, joined
from .row_extent import grid_up
from .values import PinRef, RefKind

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from .place_env import PageEnv
    from .place_room import Step
    from .values import Box


class Flag(NamedTuple):
    """A flag over a pin: symbol, row, side, pin x, box and the group sharing a y."""

    sym: str
    row: int
    below: bool
    at: int
    box: Box
    group: str


def _by(rank: Sequence[int]) -> list[int]:
    """The indices in rank order, a rank being the position along the row (no sort: R362)."""
    order = [0] * len(rank)
    for i, r in enumerate(rank):
        order[r] = i
    return order


def _pins(env: PageEnv, x: Mapping[str, int]) -> Iterator[tuple[str, int, bool, int, str, str]]:
    """(symbol, row, below, x, pin) of the pins at a row's edges: a lane's ends, a box's N and S."""
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            at = x[col_node(pc.id)] + pc.offsets[li]
            yield cells[0].sym, pc.row, False, at, cells[0].top_pin or "", ""
            yield cells[-1].sym, pc.row, True, at, cells[-1].bottom_pin or "", ""
    for r, row in enumerate(env.plan.rows):
        for b in (env.blocks[n] for n in row.blocks):
            for pin, edge in b.pin_edges if b.is_card and b.anchor else ():
                if edge in "NS":
                    yield (
                        b.anchor or "",
                        r,
                        bool("NS".index(edge)),  # 1 = S, below the box
                        box_pin_x(env, x, b.anchor or "", pin),
                        pin,
                        b.anchor or "",
                    )


def _ends(env: PageEnv) -> list[tuple[PinRef, str]]:
    """(pin, kind) of every flag end of the page: each reference end but an arrow's."""
    return [
        (end.pin, str(kind_of(ref)))
        for ref in env.refs
        if kind_of(ref) is not RefKind.ARROW
        for end in ref.ends
        if end.pin is not None and end.page == env.plan.page
    ]


def _flags(env: PageEnv, x: Mapping[str, int]) -> list[Flag]:
    """Each flag standing over a top or bottom pin, one per reference end."""
    ends = _ends(env)
    out = []
    for sym, row, below, at, pin, group in _pins(env, x):
        face = env.options.marker_below if below else env.options.marker_above
        for kind in [k for (p, k) in ends if p.sym == sym and p.pin == pin]:
            boxes = env.options.marker_fit.get((PinRef(sym, pin), kind)) or env.options.marker
            if boxes is not None and face is not None and face in boxes:
                out.append(Flag(sym, row, below, at, boxes[face], group))
    return out


def _reaches(env: PageEnv, x: Mapping[str, int]) -> list[tuple[Flag, int]]:
    """(flag, G) the flag reaches beyond its pin once overlapping ones stand further out."""
    sides: dict[tuple[int, bool, str], list[Flag]] = {}
    for flag in _flags(env, x):
        sides.setdefault((flag.row, flag.below, flag.group), []).append(flag)
    out: list[tuple[Flag, int]] = []
    grid = env.options.wiring_grid  # a reach is whole grids, as the rows hold it
    for flags in sides.values():
        spans = [(f.at + f.box.x, f.at + f.box.x + f.box.w) for f in flags]
        pos = [f.at for f in flags]
        rank = [sum(1 for j, q in enumerate(pos) if (q, j) < (a, k)) for k, a in enumerate(pos)]
        steps = intervals.stem_levels(spans, _by(rank))
        out += [
            (f, grid_up((f.box.y + f.box.h if f.below else -f.box.y) + lv * f.box.h, grid))
            for f, lv in zip(flags, steps, strict=True)
        ]
    return out


def flag_rooms(env: PageEnv, x: Mapping[str, int]) -> dict[str, Room]:
    """Per symbol: the G its flags reach above and below it, staggered as the markers stage does."""
    out: dict[str, Room] = {}
    for f, reach in _reaches(env, x):
        old = out.get(f.sym, Room())
        out[f.sym] = (
            old._replace(down=max(old.down, reach))
            if f.below
            else old._replace(up=max(old.up, reach))
        )
    return out


def with_rooms(
    env: PageEnv, x: Mapping[str, int], extra: Mapping[str, Room] = MappingProxyType({})
) -> PageEnv:
    """`env` with its flags' room and each symbol's room: the y solve and the spans read both.

    A symbol's room joins its flags, its row's room below a cell, and `extra` (anchors, R409).
    """
    env = replace(env, flag_room=flag_rooms(env, x))
    out, rows = dict(env.flag_room), row_rooms(env)
    for pc in env.pcs.values():
        for sym in {c.sym for ln in pc.lanes for c in ln}:
            out[sym] = out.get(sym, Room())._replace(down=rows.get(pc.row, Room()).down)
    rooms = {s: joined(out.get(s, Room()), extra.get(s, Room())) for s in {**out, **extra}}
    return replace(env, rooms=rooms)


def _reach(
    env: PageEnv, ends: Sequence[tuple[PinRef, str]], sym: str, pin: str | None, *, below: bool
) -> int:
    """The G the tallest flag at `pin` of `sym` reaches along the wire, below it or above it."""
    face = env.options.marker_below if below else env.options.marker_above
    reach = 0
    for p, kind in ends:
        boxes = env.options.marker_fit.get((p, kind)) or env.options.marker
        if (
            pin is not None
            and (p.sym, p.pin) == (sym, pin)
            and boxes
            and face is not None
            and face in boxes
        ):
            box = boxes[face]
            reach = max(reach, box.y + box.h if below else -box.y)
    return reach


def pair_steps(env: PageEnv) -> dict[Step, int]:
    """The pin-to-pin y step each pair of consecutive cells needs for the flags between them.

    The flags of the upper cell's bottom pin and the lower cell's top pin stand on the wire
    between them; the lane ends are `flag_rooms`', so only a pair of two cells has a step here.
    """
    ends = _ends(env)
    out: dict[Step, int] = {}
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            for i, (a, b) in enumerate(pairwise(cells)):
                need = _reach(env, ends, a.sym, a.bottom_pin, below=True) + _reach(
                    env, ends, b.sym, b.top_pin, below=False
                )
                if need:
                    out[pc.id, li, i] = grid_up(need, env.options.wiring_grid)
    return out
