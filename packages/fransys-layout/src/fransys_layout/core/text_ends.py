"""Stage 8, where each reference end stands, from the placement alone.

A pin end stands one marker box out from its pin on the pin's turned side. An arrow stands at the
trunk end of its fan in the row of its column; a copy at the start of its fan's trunk on its
page. A tag end that names a column stands at the net's pin nearest that column on its page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .keys import natural_key
from .ref_kind import kind_of
from .scene_facts import turn_side
from .values import RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .outputs import Placement, Trunk
    from .values import (
        CutResult,
        Fan,
        Options,
        Orientation,
        PinRef,
        PlacementProblem,
        Ref,
        RefEnd,
        Side,
        Size,
    )

Key = tuple[tuple[int, int | str], ...]
PinAt = tuple[int, int, int, "Orientation"]
_STEP = frozendict({"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)})


@dataclass(frozen=True, slots=True)
class MarkEnv:
    """Everything stage 8a reads, looked up once: the pins, trunks, rows and nets of a run."""

    options: Options
    area: Size
    pins: Mapping[tuple[str, str], PinAt]
    sides: Mapping[tuple[str, str], Side]
    trunks: Mapping[tuple[int, str], tuple[Trunk, ...]]
    fans: Mapping[str, Fan]


@dataclass(frozen=True, slots=True)
class Stand:
    x: int
    y: int
    end: PinRef


def mark_env(
    cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options
) -> MarkEnv:
    """The lookups of one run; a pin, trunk or column is found by its id."""
    pins, trunks = {}, {}
    for pg in placement.pages:
        for p in pg.placed:
            for q in p.pin_xy:
                pins[(p.sym, q.pin)] = (pg.page, q.x, q.y, p.orient)
        for t in sorted(pg.trunks, key=lambda t: t.row):
            trunks[(pg.page, t.fan)] = (*trunks.get((pg.page, t.fan), ()), t)
    return MarkEnv(
        options,
        problem.area,
        pins,
        {(s.id, p.id): p.side for s in problem.symbols for p in s.pins},
        trunks,
        {f.id: f for f in cut.flow.fans},
    )


def who(ref: Ref) -> str:
    """The net and kind of a reference, for the message of a refusal."""
    return f"net {ref.net} ({kind_of(ref)})"


def pin_stand(env: MarkEnv, pin: PinRef, page: int, ref: Ref) -> Stand:
    """One marker box out from the pin along its turned side."""
    if (pin.sym, pin.pin) not in env.pins:
        msg = f"marks: {who(ref)} has no placed pin {pin.sym}.{pin.pin}"
        raise ValueError(msg)
    at, x, y, orient = env.pins[(pin.sym, pin.pin)]
    if at != page:
        msg = f"marks: {who(ref)} names {pin.sym}.{pin.pin} on page {page}, not {at}"
        raise ValueError(msg)
    dx, dy = _STEP[turn_side(env.sides[(pin.sym, pin.pin)], orient)]
    size = env.options.marker
    return Stand(x + dx * size.w if dx else x, y + dy * size.h if dy else y, pin)


def _trunk_of(env: MarkEnv, fan: str, end: RefEnd, ref: Ref) -> tuple[Trunk, ...]:
    if not (found := env.trunks.get((end.page, fan), ())):
        msg = f"marks: {who(ref)} page {end.page}: fan {fan} has no trunk"
        raise ValueError(msg)
    return found


def _named(ref: Ref, end: RefEnd) -> PinRef:
    """The pin an arrow or copy end names; stage 4 fills it, so none is a plan it cannot make."""
    if end.pin is None:
        msg = f"marks: {who(ref)} page {end.page}: the end names no pin; stage 4 fills it"
        raise ValueError(msg)
    return end.pin


def arrow_stand(env: MarkEnv, ref: Ref, end: RefEnd, index: int) -> Stand:
    """The right end of the fan's trunk in the end's row for the first end, else its left end."""
    if end.row is None:
        msg = f"marks: {who(ref)} page {end.page}: the end names no row; stage 4 fills it"
        raise ValueError(msg)
    trunks = [t for t in _trunk_of(env, ref.net, end, ref) if t.row == end.row]
    if not trunks:
        msg = f"marks: {who(ref)} page {end.page}: no trunk in row {end.row}"
        raise ValueError(msg)
    return Stand(trunks[0].x1 if index == 0 else trunks[0].x0, trunks[0].y, _named(ref, end))


def copy_stand(env: MarkEnv, ref: Ref, end: RefEnd) -> Stand:
    """The start of the fan's first trunk on the page the copy is drawn on."""
    fan = next((f for f in env.fans.values() if ref.net in f.nets), None)
    if fan is None:
        msg = f"marks: {who(ref)} belongs to no fan"
        raise ValueError(msg)
    t = _trunk_of(env, fan.id, end, ref)[0]
    return Stand(t.x0, t.y, _named(ref, end))


def _pin_key(k: tuple[str, str]) -> tuple[Key, Key]:
    return natural_key(k[0]), natural_key(k[1])


def tag_stand(env: MarkEnv, ref: Ref, end: RefEnd) -> Stand:
    """A tag end stands at the pin stage 4 named for it."""
    return pin_stand(env, _named(ref, end), end.page, ref)


def pinned_stand(env: MarkEnv, ref: Ref, end: RefEnd) -> Stand:
    """A stub stands at its boundary pin; an end with no pin is a plan stage 4 cannot make."""
    if end.pin is None:
        msg = f"marks: {who(ref)} page {end.page}: the end names no pin"
        raise ValueError(msg)
    return pin_stand(env, end.pin, end.page, ref)


def end_stand(env: MarkEnv, ref: Ref, end: RefEnd, index: int) -> Stand:
    """Where one end of a reference stands; the rule is the reference kind's."""
    match kind_of(ref):
        case RefKind.ARROW:
            return arrow_stand(env, ref, end, index)
        case RefKind.COPY:
            return copy_stand(env, ref, end)
        case RefKind.TAG:
            return tag_stand(env, ref, end)
        case RefKind.STUB | RefKind.STAR:
            return pinned_stand(env, ref, end)


def hub_xy(env: MarkEnv, ref: Ref, end: RefEnd) -> tuple[int, int]:
    """Where a copy's hub stands: its first placed pin, in the order of the pin's id.

    The hub is on a page other than the copy's; on the copy's own page there is nothing to copy.
    """
    fan = next((f for f in env.fans.values() if ref.net in f.nets), None)
    pins = sorted((k for k in env.pins if fan is not None and k[0] == fan.hub), key=_pin_key)
    if not pins:
        msg = (
            f"marks: {who(ref)}: the hub has no placed pin; "
            "the placement must place a pin of the fan's hub"
        )
        raise ValueError(msg)
    page, x, y, _ = env.pins[pins[0]]
    if page == end.page:
        msg = (
            f"marks: {who(ref)} page {end.page}: the hub {pins[0][0]} stands on the copy's own "
            "page; stage 4 copies() plans a copy end only on a page other than the hub's"
        )
        raise ValueError(msg)
    return x, y
