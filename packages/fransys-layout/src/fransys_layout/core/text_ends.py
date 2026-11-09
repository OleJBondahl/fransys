"""Stage 8, where each reference end stands, from the placement alone.

A pin end stands one marker box out from its pin on the pin's turned side. An arrow stands at the
trunk end of its fan in the row of its column; a copy at the start of its fan's trunk on its
page. A tag end that names a column stands at the net's pin nearest that column on its page.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import pairwise
from typing import TYPE_CHECKING

from .arrow_reserve import arrow_rows, leg_feet, leg_fit, leg_lines, leg_rows
from .band import abut as band_abut
from .band import lane_line
from .clearance import Keep, footprint_keeps
from .cut_drawn import cut_stands
from .cut_end_rooms import laned_stub, pole_of
from .errors import CoreError
from .geometry import sized
from .keys import natural_key
from .ref_kind import kind_of
from .route_env import pin_sides
from .sides import step_out
from .values import Box, PinRef, RefKind, StandClass

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .arrow_reserve import ArrowEnds
    from .flow_values import CutResult, Fan
    from .outputs import Placement, Trunk
    from .route_fixed import Fixed
    from .values import XY, Options, Orientation, PlacementProblem, Ref, RefEnd, Side, Size

Key = tuple[tuple[int, int | str], ...]
PinAt = tuple[int, int, int, "Orientation"]


@dataclass(frozen=True, slots=True)
class MarkEnv:
    """Everything stage 8a reads, looked up once: the pins, trunks, rows and nets of a run."""

    options: Options
    area: Size
    pins: Mapping[tuple[str, str], PinAt]
    sides: Mapping[tuple[str, str, Orientation], Side]
    trunks: Mapping[tuple[int, str], tuple[Trunk, ...]]
    fans: Mapping[str, Fan]
    leads: frozenset[PinRef] = frozenset()
    pin_net: Mapping[tuple[str, str], str] = field(default_factory=dict)
    stands: Mapping[PinRef, Mapping[Orientation, PinRef | None]] = field(
        default_factory=dict
    )  # a mixed pin -> by orientation, the pin its marker stands at
    legs: Mapping[int, Mapping[PinRef, int]] = field(default_factory=dict)  # a page -> its one-sided pins, each with the row of its leg's trunk end
    footprints: Mapping[int, tuple[tuple[str, Box], ...]] = field(default_factory=dict)  # by page, each placed symbol and its footprint
    arrowed: ArrowEnds = field(default_factory=dict)  # the page, fan and row of each trunk that stands an arrow at its right end
    keeps: Mapping[int, Sequence[Keep]] = field(default_factory=dict)  # by page, what a marker box keeps clear of
    leg_lines: Mapping[int, Mapping[tuple[str, int, PinRef], tuple[XY, XY, XY]]] = field(
        default_factory=dict
    )  # by page, each leg's line, by (fan, row, pin)
    bands: Mapping[int, tuple[tuple[int, int], ...]] = field(default_factory=dict)  # by page, the solved row bands
    ranks: Mapping[str, int] = field(default_factory=dict)  # a symbol -> its rank; no id text decides an order (SYMBOL-TIE)
    columns: Mapping[str, tuple[int, ...]] = field(default_factory=dict)  # a column or hub id -> the ranks of its symbols, in cell order


@dataclass(frozen=True, slots=True)
class Stand:
    x: int
    y: int
    end: PinRef
    orient: Orientation
    side: Side  # the side the marker's box lies on: the turn `Options.marker_facing` gives it
    band: tuple[int, int] | None = None  # the row band a pin's marker box stays in (R1333)
    walked: bool = False  # the end of a lane placement walked clear of every keep: the one fit test (R1331, R1338)
    stood: bool = True  # False: the arrow's lane end found no stand at placement (Trunk.stood); the marker is MARKER_UNPLACED (layout-0507)


def mark_env(cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options) -> MarkEnv:
    """The lookups of one run; a pin, trunk or column is found by its id."""
    pins, trunks = {}, {}
    for pg in placement.pages:
        for p in pg.placed:
            for q in p.pin_xy:
                pins[(p.sym, q.pin)] = (pg.page, q.x, q.y, p.orient)
        for t in sorted(pg.trunks, key=lambda t: t.row):
            trunks[(pg.page, t.fan)] = (*trunks.get((pg.page, t.fan), ()), t)
    ranks = {s.id: s.rank if s.rank is not None else len(problem.symbols) + i for i, s in enumerate(problem.symbols)}
    columns = {c.id: tuple(ranks[cell.sym] for lane in c.lanes for cell in lane.cells) for c in cut.flow.columns} | {
        k: (v,) for k, v in ranks.items()
    }
    fans, arrowed = {f.id: f for f in cut.flow.fans}, arrow_rows(cut.spec.reference_plan, cut.spec.pages, cut.flow.fans)
    legs_by_page = {
        pg.page: leg_lines(
            pg.trunks,
            fans,
            leg_rows(cut.spec.reference_plan, pg.page),
            leg_fit(options, cut.spec.reference_plan, pg.page),
            (leg_feet(pg.placed, pg.hangings), arrowed, problem.area),
        )
        for pg in placement.pages
    }
    rows = {page: {pin: row for _, row, pin in lines} for page, lines in legs_by_page.items()}
    return MarkEnv(
        options,
        problem.area,
        pins,
        pin_sides(problem),
        trunks,
        fans,
        cut.spec.leads,
        {(r.sym, r.pin): n.id for n in problem.nets for r in n.pins},
        cut_stands(problem, cut),
        rows,
        {pg.page: tuple((p.sym, p.footprint) for p in pg.placed) for pg in placement.pages},
        arrowed,
        leg_lines=legs_by_page,
        bands={pg.page: pg.bands for pg in placement.pages},
        ranks=ranks,
        columns=columns,
    )


def pin_keeps(env: MarkEnv) -> dict[int, list[Keep]]:
    """By page, a point Keep per pin and a segment Keep per lead, owned by its net, and each footprint, owned by its symbol (R845, R920)."""
    out: dict[int, list[Keep]] = {page: [Keep("", box, "footprint", sym) for sym, box in feet] for page, feet in env.footprints.items()}
    for (sym, pin), (page, x, y, orient) in env.pins.items():
        if (net := env.pin_net.get((sym, pin))) is None:
            continue
        if PinRef(sym, pin) in env.leads:
            (x1, y1) = step_out(env.sides[(sym, pin, orient)], x, y, env.options.wiring_grid)
            out.setdefault(page, []).append(
                Keep("", Box(min(x, x1), min(y, y1), abs(x1 - x), abs(y1 - y)), "wire", net, None, None, ((x, y), (x1, y1)))
            )
        else:
            out.setdefault(page, []).extend(footprint_keeps([("", net)], Box(x, y, 0, 0)))
    return out


def wire_keeps(fixed: Mapping[int, Fixed]) -> dict[int, list[Keep]]:
    """By page, a Keep for each segment of a fixed wire, owned by its net (R872, R1007)."""
    out: dict[int, list[Keep]] = {}
    for page, pair in fixed.items():
        for w in pair.trunks.wires:
            for (x0, y0), (x1, y1) in pairwise(w.points):
                box = Box(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
                out.setdefault(page, []).append(Keep("", box, "wire", w.net, None, None, (w.points[0], w.points[-1])))
    return out


def bundle_nets(env: MarkEnv, net: str) -> frozenset[str]:
    """The nets a marker of `net` may stand beside: itself, its fan's lanes and those of every fan that meets a symbol its fan meets (R1007)."""
    syms = {a.pin.sym for f in env.fans.values() if net == f.id or net in f.nets for a in (*f.drivers, *f.legs)}
    return frozenset({net, *(n for f in env.fans.values() if syms & {a.pin.sym for a in (*f.drivers, *f.legs)} for n in f.nets)})


def who(ref: Ref) -> str:
    """The net and kind of a reference, for the message of a refusal."""
    return f"net {ref.net} ({kind_of(ref)})"


def abut(options: Options, side: Side, x: int, y: int, key: tuple[PinRef, str]) -> Stand:
    """The stand whose box has its near edge at (x, y) on `side`; the box turns to face it."""
    ox, oy, turned = band_abut(options, side, x, y, key)
    return Stand(ox, oy, key[0], turned, side)


def stood_at(env: MarkEnv, pin: PinRef) -> PinRef:
    """The pin `pin`'s marker stands at in its placed orientation: itself, or the sibling `env.stands` names."""
    placed = env.pins.get((pin.sym, pin.pin))
    return (env.stands[pin][placed[3]] if placed is not None and pin in env.stands else None) or pin


def pin_stand(env: MarkEnv, pin: PinRef, page: int, ref: Ref) -> Stand:
    """One marker box out from the pin along its turned side, past its lead wire if it has one.

    A mixed pin on a free-sided symbol stands at the pin `env.stands` names for its orientation: the end stays `pin`.
    """
    xy = stood_at(env, pin)
    if (xy.sym, xy.pin) not in env.pins:
        msg = f"marks: {who(ref)} has no placed pin {xy.sym}.{xy.pin}"
        raise CoreError(msg)
    at, x, y, orient = env.pins[(xy.sym, xy.pin)]
    if at != page:
        msg = f"marks: {who(ref)} names {xy.sym}.{xy.pin} on page {page}, not {at}"
        raise CoreError(msg)
    side = env.sides[(xy.sym, xy.pin, orient)]
    x, y = step_out(side, x, y, env.options.wiring_grid if xy in env.leads else 0)
    stand = abut(env.options, side, x, y, (pin, str(kind_of(ref))))
    feet = next((box for sym, box in env.footprints.get(page, ()) if sym == xy.sym), None)
    band = None if feet is None else next((b for b in env.bands.get(page, ()) if b[0] <= feet.y < b[1]), None)
    return replace(stand, band=band)


def _trunk_of(env: MarkEnv, fan: str, end: RefEnd, ref: Ref) -> tuple[Trunk, ...]:
    if not (found := env.trunks.get((end.page, fan), ())):
        msg = f"marks: {who(ref)} page {end.page}: fan {fan} has no trunk"
        raise CoreError(msg)
    return found


def _named(ref: Ref, end: RefEnd) -> PinRef:
    """The pin an arrow or copy end names; stage 4 fills it, so none is a plan it cannot make."""
    if end.pin is None:
        msg = f"marks: {who(ref)} page {end.page}: the end names no pin; stage 4 fills it"
        raise CoreError(msg)
    return end.pin


def arrow_stand(env: MarkEnv, ref: Ref, end: RefEnd, index: int) -> Stand:
    """The right end of the fan's trunk in the end's row for the first end, else its left end."""
    if end.row is None:
        msg = f"marks: {who(ref)} page {end.page}: the end names no row; stage 4 fills it"
        raise CoreError(msg)
    trunks = [t for t in _trunk_of(env, ref.net, end, ref) if t.row == end.row]
    if not trunks:
        msg = f"marks: {who(ref)} page {end.page}: no trunk in row {end.row}"
        raise CoreError(msg)
    return _lane_stand(env, trunks[0], (_named(ref, end), str(kind_of(ref))), int(index != 0))


def _lane_stand(env: MarkEnv, t: Trunk, key: tuple[PinRef, str], index: int) -> Stand:
    """The stand at the end of the lane of the pin's pole: an arrow's, or a bundle's cross-document stub (R1338)."""
    side = env.options.arrow_sides[int(index != 0)]
    fan = env.fans.get(t.fan)
    x0, x1, y, stood = lane_line(t, pole_of(fan, key[0]) if fan is not None else 0, fan.lanes if fan is not None else 1, env.options.wiring_grid)
    return replace(abut(env.options, side, x1 if side == "E" else x0, y, key), walked=True, stood=stood[side == "E"])


def _own_lane_stand(env: MarkEnv, ref: Ref, end: RefEnd, trunk: Trunk, key: tuple[PinRef, str]) -> Stand:
    """A bundled stub with no leg line stands at the end of its own pole's lane (R1938); a pole with no lane end is an error."""
    fan = env.fans[next(f.id for f in env.fans.values() if ref.net in f.nets)]
    pole = pole_of(fan, key[0])
    if not trunk.lane_ends[pole]:
        msg = f"marks: {who(ref)} page {end.page}: pole {pole} of the bundle has no lane end for the stub at {key[0].sym}.{key[0].pin}; "
        msg += "give the pole a pin on this page"
        raise CoreError(msg)
    return _lane_stand(env, trunk, key, 0)


def _trunk_end_stand(env: MarkEnv, trunk: Trunk, key: tuple[PinRef, str]) -> Stand:
    """The stand at the first `arrow_sides` end of the trunk: its lane end was walked clear at placement (R1331)."""
    side = env.options.arrow_sides[0]
    return abut(env.options, side, trunk.x1 if side == "E" else trunk.x0, trunk.y, key)


def leg_stand(env: MarkEnv, ref: Ref, end: RefEnd, row: int) -> Stand:
    """A one-sided pin's marker stands at the end of its leg, below the bundle (ONE-SIDED-PIN)."""
    fan = next(f.id for f in env.fans.values() if ref.net in f.nets)
    trunks = [t for t in _trunk_of(env, fan, end, ref) if t.row == row]
    if not trunks:
        msg = f"marks: {who(ref)} page {end.page}: no trunk in row {row}"
        raise CoreError(msg)
    pin = _named(ref, end)
    x, y = env.leg_lines[end.page][fan, row, pin][-1]
    return abut(env.options, "S", x, y, (pin, str(kind_of(ref))))


def pinned_stand(env: MarkEnv, ref: Ref, end: RefEnd) -> Stand:
    """A stub stands below its lane (LEG), else at the trunk end of its fan (LEG with no leg, TRUNK_END), else at its boundary pin (ONE-SIDED-PIN)."""
    if end.pin is None:
        msg = f"marks: {who(ref)} page {end.page}: the end names no pin"
        raise CoreError(msg)
    fan = next((f.id for f in env.fans.values() if ref.net in f.nets), None)
    bundled = kind_of(ref) in (RefKind.STUB, RefKind.COPY) and fan is not None and laned_stub(env.fans[fan])
    match end.stand:
        case StandClass.LEG if end.row is not None and end.pin in env.legs.get(end.page, {}):
            return leg_stand(env, ref, end, end.row)
        case StandClass.LEG | StandClass.TRUNK_END if (
            trunk := next(iter(env.trunks.get((end.page, fan), ())), None)
        ) is not None and end.pin not in env.leads:
            key = (end.pin, str(kind_of(ref)))
            return _own_lane_stand(env, ref, end, trunk, key) if bundled else _trunk_end_stand(env, trunk, key)
    return pin_stand(env, end.pin, end.page, ref)


def end_stand(env: MarkEnv, ref: Ref, end: RefEnd, index: int) -> Stand:
    """Where one end of a reference stands; the rule is the reference kind's. Its box is the one for the lines its ledger end holds (R1598)."""
    if end.pin is not None:
        env = replace(env, options=sized(env.options, (end.pin, str(kind_of(ref))), end.also, end.far))
    match kind_of(ref):
        case RefKind.ARROW:
            return arrow_stand(env, ref, end, index)
        case RefKind.TAG:  # a tag end stands at the pin stage 4 named for it
            return pin_stand(env, _named(ref, end), end.page, ref)
        case RefKind.COPY | RefKind.STUB | RefKind.STAR:
            return pinned_stand(env, ref, end)


def hub_xy(env: MarkEnv, ref: Ref, end: RefEnd) -> tuple[int, int]:
    """Where a copy's hub stands: its first placed pin, by the pin's name (all of one symbol, so no id text orders it).

    The hub is on a page other than the copy's; on the copy's own page there is nothing to copy.
    """
    fan = next((f for f in env.fans.values() if ref.net in f.nets), None)
    pins = sorted((k for k in env.pins if fan is not None and k[0] == fan.hub), key=lambda k: natural_key(k[1]))
    if not pins:
        msg = f"marks: {who(ref)}: the hub has no placed pin; the placement must place a pin of the fan's hub"
        raise CoreError(msg)
    page, x, y, _ = env.pins[pins[0]]
    if page == end.page:
        msg = (
            f"marks: {who(ref)} page {end.page}: the hub {pins[0][0]} stands on the copy's own "
            "page; stage 4 copies() plans a copy end only on a page other than the hub's"
        )
        raise CoreError(msg)
    return x, y
