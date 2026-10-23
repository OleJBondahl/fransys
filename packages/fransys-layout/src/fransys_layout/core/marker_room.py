"""The room a row keeps for its fitted marker boxes: sizes el passes in `Options.marker_fit`.

Stage 5 reads it so a text-sized box stands inside the page. It reads boxes only; it names no kind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import inside, marker_box
from .room import Room

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from .outputs import Marker
    from .place_env import PageEnv
    from .values import Box, Column, Options, PinRef, PlacementProblem


def _grown(old: Room, boxes: Sequence[Box]) -> Room:
    return Room(
        max(old.left, *(-b.x for b in boxes)),
        max(old.right, *(b.x + b.w for b in boxes)),
        max(old.up, *(-b.y for b in boxes)),
        max(old.down, *(b.y + b.h for b in boxes)),
    )


def fitted(env: PageEnv) -> Iterator[tuple[PinRef, Room]]:
    """(pin, room) of every pin whose marker box el fitted from its text.

    A pin of a column stands above or below its cell, so only the quarter-turn views count; a
    head pin reaches up only and a foot pin down only, as its flag lies on that side.
    """
    cells = [c for pc in env.pcs.values() for ln in pc.lanes for c in ln]
    heads = {(c.sym, c.top_pin) for c in cells}
    feet = {(c.sym, c.bottom_pin) for c in cells}
    for (pin, _), views in env.options.marker_fit.items():
        room = _grown(Room(), [b for o, b in views.items() if o in env.options.marker_vertical])
        if (pin.sym, pin.pin) in heads:
            room = room._replace(down=0)
        elif (pin.sym, pin.pin) in feet:
            room = room._replace(up=0)
        yield pin, room


def row_rooms(env: PageEnv) -> dict[int, Room]:
    """The widest reach of the fitted boxes of the ref ends standing in each row of the page."""
    rows = {c.sym: pc.row for pc in env.pcs.values() for ln in pc.lanes for c in ln}
    for r, row in enumerate(env.plan.rows):
        rows |= {env.blocks[b].anchor or "": r for b in row.blocks if env.blocks[b].is_card}
    out: dict[int, Room] = {}
    for pin, room in fitted(env):
        if pin.sym in rows:
            r = rows[pin.sym]
            out[r] = Room(*map(max, out.get(r, Room()), room, strict=False))
    for sym, room in env.flag_room.items():
        out[rows[sym]] = Room(*map(max, out.get(rows[sym], Room()), room, strict=False))
    return out


def column_rooms(env: PageEnv) -> dict[str, list[tuple[int, Room]]]:
    """Per column: (lane offset, room) of each fitted end whose pin stands on one of its cells."""
    at = {
        c.sym: (pc.id, pc.offsets[li])
        for pc in env.pcs.values()
        for li, ln in enumerate(pc.lanes)
        for c in ln
    }
    out: dict[str, list[tuple[int, Room]]] = {}
    for pin, room in fitted(env):
        if pin.sym in at:
            out.setdefault(at[pin.sym][0], []).append((at[pin.sym][1], room))
    return out


def _reach(column: Column, options: Options, *, head: bool) -> int:
    """The G the fitted boxes of a column's head (up) or other (down) pins reach beyond them.

    A box equal to the plain marker's adds nothing: the cut counted it already.
    """
    cells = [c for lane in column.lanes for c in lane.cells]
    syms, heads = {c.sym for c in cells}, {(c.sym, c.top_pin) for c in cells}
    return max(
        (
            max(-b.y for o, b in views.items() if o in options.marker_vertical)
            if head
            else max(b.y + b.h for o, b in views.items() if o in options.marker_vertical)
            for (pin, _), views in options.marker_fit.items()
            if pin.sym in syms and ((pin.sym, pin.pin) in heads) is head and views != options.marker
        ),
        default=0,
    )


def lowered(height: int, columns: Iterable[Column], options: Options) -> int:
    """`height` plus the G the fitted boxes of `columns` reach above and below it."""
    cols = list(columns)
    up = max((_reach(c, options, head=True) for c in cols), default=0)
    down = max((_reach(c, options, head=False) for c in cols), default=0)
    return height + up + down


def outside(markers: Iterable[Marker], problem: PlacementProblem, options: Options) -> list[Marker]:
    """The flags whose box leaves the page area: `widen` measures their symbols' height again."""
    return [m for m in markers if not inside(marker_box(m, options), problem.area)]
