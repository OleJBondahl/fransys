"""Stage 8, where each reference end stands, from the placement alone.

A pin end stands one marker box out from its pin on the pin's turned side. An arrow stands at the
trunk end of its fan in the row of its column; a copy at the start of its fan's trunk on its
page. A tag end that names a column stands at the net's pin nearest that column on its page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .band import lane_offset, lane_rows
from .geometry import inside, marker_box_at
from .keys import natural_key
from .ref_kind import kind_of
from .route_env import lead_pins, lone_cut_pins, pin_sides
from .sides import step_out
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
# the symbol at R0 points east; this turn points its box along the pin's turned side
_FACING: Mapping[Side, Orientation] = frozendict({"E": "R0", "S": "R90", "W": "R180", "N": "R270"})
_FACED: Mapping[Orientation, Side] = frozendict(zip(_FACING.values(), _FACING, strict=True))


@dataclass(frozen=True, slots=True)
class MarkEnv:
    """Everything stage 8a reads, looked up once: the pins, trunks, rows and nets of a run."""

    options: Options
    area: Size
    pins: Mapping[tuple[str, str], PinAt]
    sides: Mapping[tuple[str, str, Orientation], Side]
    trunks: Mapping[tuple[int, str], tuple[Trunk, ...]]
    fans: Mapping[str, Fan]
    leads: Mapping[PinRef, str] = field(default_factory=dict)
    lone: frozenset[PinRef] = frozenset()
    pin_net: Mapping[tuple[str, str], str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Stand:
    x: int
    y: int
    end: PinRef
    orient: Orientation = "R0"

    @property
    def side(self) -> Side:
        """The side the marker's box lies on, from its turn: the one table, `_FACING`."""
        return _FACED[self.orient]


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
        pin_sides(problem),
        trunks,
        {f.id: f for f in cut.flow.fans},
        lead_pins(problem, cut.flow.fans),
        lone_cut_pins(problem),
        {(r.sym, r.pin): n.id for n in problem.nets for r in n.pins},
    )


def who(ref: Ref) -> str:
    """The net and kind of a reference, for the message of a refusal."""
    return f"net {ref.net} ({kind_of(ref)})"


def _abut(options: Options, side: Side, x: int, y: int, key: tuple[PinRef, str]) -> Stand:
    """The stand whose box has its near edge at (x, y) on `side`; the box turns to face it."""
    turned = _FACING[side]
    box = marker_box_at(0, 0, options, turned, key)  # the box about an origin of (0, 0)
    depth = {"E": -box.x, "W": box.x + box.w, "S": -box.y, "N": box.y + box.h}[side]
    return Stand(*step_out(side, x, y, depth), key[0], turned)


def pin_stand(env: MarkEnv, pin: PinRef, page: int, ref: Ref, lead: int = 0) -> Stand:
    """One marker box out from the pin along its turned side, past a `lead` wire if it has one."""
    if (pin.sym, pin.pin) not in env.pins:
        msg = f"marks: {who(ref)} has no placed pin {pin.sym}.{pin.pin}"
        raise ValueError(msg)
    at, x, y, orient = env.pins[(pin.sym, pin.pin)]
    if at != page:
        msg = f"marks: {who(ref)} names {pin.sym}.{pin.pin} on page {page}, not {at}"
        raise ValueError(msg)
    side = env.sides[(pin.sym, pin.pin, orient)]
    x, y = step_out(side, x, y, lead)
    return _abut(env.options, side, x, y, (pin, str(kind_of(ref))))


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
    t, pin = trunks[0], _named(ref, end)
    side = env.options.arrow_sides[int(index != 0)]
    x0, x1, y = _lane_line(env, t, pin)
    return _abut(env.options, side, x1 if side == "E" else x0, y, (pin, str(kind_of(ref))))


def _lane_line(env: MarkEnv, t: Trunk, pin: PinRef) -> tuple[int, int, int]:
    """(x0, x1, y) of the arrow's line: the trunk's ends and the y of the pin's pole lane.

    A bundle's continuing lanes run one lane step past the hull (place_assemble._lane_ends), so
    its one arrow stands at that end.
    """
    fan = env.fans.get(t.fan)
    net = env.pin_net.get((pin.sym, pin.pin))
    pole = fan.nets.index(net) if fan is not None and net in fan.nets else 0
    if fan is None or fan.lanes == 1:
        return t.x0, t.x1, t.y
    reach = lane_offset(1, env.options.wiring_grid)
    row = lane_rows(t.lane_ends)[pole]
    return t.x0 - reach, t.x1 + reach, t.y + lane_offset(row, env.options.wiring_grid)


def copy_stand(env: MarkEnv, ref: Ref, end: RefEnd) -> Stand:
    """A copy end follows the pin rule, like a tag: it stands at the pin stage 4 named for it."""
    return pin_stand(env, _named(ref, end), end.page, ref)


def _pin_key(k: tuple[str, str]) -> tuple[Key, Key]:
    return natural_key(k[0]), natural_key(k[1])


def tag_stand(env: MarkEnv, ref: Ref, end: RefEnd) -> Stand:
    """A tag end stands at the pin stage 4 named for it."""
    return pin_stand(env, _named(ref, end), end.page, ref)


def _fan_trunk(env: MarkEnv, pin: PinRef, page: int) -> Trunk | None:
    """The trunk, on `page`, of the fan that holds `pin`: where its stub stands (R499)."""
    for fan in env.fans.values():
        if pin in env.lone and any(a.pin == pin for a in (*fan.drivers, *fan.legs)):
            return next(iter(env.trunks.get((page, fan.id), ())), None)
    return None


def _trunk_end_stand(env: MarkEnv, trunk: Trunk, key: tuple[PinRef, str]) -> Stand:
    """The stand at the first `arrow_sides` end of the trunk whose box lies inside the page."""
    stands = [
        _abut(env.options, side, trunk.x1 if side == "E" else trunk.x0, trunk.y, key)
        for side in env.options.arrow_sides
    ]
    fits = (
        s for s in stands if inside(marker_box_at(s.x, s.y, env.options, s.orient, key), env.area)
    )
    return next(fits, stands[0])


def pinned_stand(env: MarkEnv, ref: Ref, end: RefEnd) -> Stand:
    """A stub stands at the trunk end of its bundle, else at its boundary pin."""
    if end.pin is None:
        msg = f"marks: {who(ref)} page {end.page}: the end names no pin"
        raise ValueError(msg)
    if (trunk := _fan_trunk(env, end.pin, end.page)) is not None and end.pin not in env.leads:
        return _trunk_end_stand(env, trunk, (end.pin, str(kind_of(ref))))
    grid = env.options.wiring_grid
    return pin_stand(env, end.pin, end.page, ref, grid if end.pin in env.leads else 0)


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
