"""The drawn band of a bundle trunk in the x phase: each lane's end and its arrow keep."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from .arrow_reserve import leg_fit, leg_pins, leg_rows, leg_unit, reserve
from .band import arrow_box, lane_offset, lane_rows
from .clearance import Keep
from .cut_end_rooms import arrow_ends, arrow_leads, arrow_poles, cut_ends
from .errors import CoreError
from .geometry import sized
from .hangings import KEEP_KIND, hanging_keep
from .node_names import col_node
from .place_trunk import box_at, box_pin_x, in_row
from .stand_fit import Limits, fit, may_cross
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from .cut_end_rooms import CutEnd
    from .flow_values import Attach, Fan
    from .outputs import Placed
    from .place_env import PageEnv
    from .values import Options, PinRef


Key = tuple["PinRef", str]  # an arrow's (pin, kind)


class Stand(NamedTuple):
    """Where a trunk's lanes stand (R881): a pitch `reach`, the trunk's `y`, arrow `options`, footprint `keeps`, `placed` pins, `legs` (R903)."""

    reach: int = 0
    y: int = 0
    options: Options | None = None
    keeps: tuple[Keep, ...] = ()
    poles: tuple[frozenset[int], frozenset[int]] = (frozenset[int](), frozenset[int]())
    legs: int = 0
    placed: Mapping[str, Placed] | None = None
    limits: Limits | None = None  # the content box and the row band: a marker box leaves them never
    leads: tuple[frozenset[int], frozenset[int]] = (frozenset[int](), frozenset[int]())  # the poles whose lane carries the cut end's marker
    right: int = 0  # the far x an arrow's end may stand at with its marker inside the content box; 0 sets none (R1010)
    keys: tuple[dict[int, Key], dict[int, Key]] = ({}, {})  # per end, each pole's arrow key
    fits: tuple[dict[int, Options], dict[int, Options]] = ({}, {})  # per end, each pole's options sized for the lines its ledger end holds (R1598)
    drop: int = (
        0  # the x of the last placed leg drop of the trunk's right end: an arrow's lane end stands one pitch past it; 0 sets none (BUNDLE-LEGS)
    )


_BARE = Stand()
Taps = tuple[tuple["Attach", int, int | None], ...]  # each attachment with its x and its placed pin's y (None before the pin is placed)


def _hull(xs: Sequence[int]) -> tuple[int, int] | None:
    return (min(xs), max(xs)) if xs else None


def _arrow_at(at: int, step: int, key: Key, stand: Stand) -> Box:
    """The drawn box of the arrow with its near edge at `at` on the lane at `stand.y`, right of it for step +1, left for -1 (layout-0524)."""
    if stand.options is None:
        msg = "lane walk: Stand.options is unset; pass the options that draw the arrow"
        raise CoreError(msg)
    return arrow_box(stand.options, "E" if step > 0 else "W", at, stand.y, key)


def _free(x: int, step: int, key: Key, stand: Stand, own: Collection[str]) -> int | None:
    """`x` moved out (step -1 left, +1 right) along clear track to the next grid line where the arrow marker fits (R881, R906, R936, R1333).

    The walk stops at the first foreign footprint or marker on the trunk's line: the end then stays at `x`.
    None: no stand, the content box ends the walk (layout-0507). A foreign wire is crossed (R1023) only where the end then stands a cell clear of it.
    """
    g, ly = stand.reach, stand.y
    at = x
    while (hit := fit(_arrow_at(at, step, key, stand), stand.keeps, (), stand.limits)) is not None:
        if not hit:
            return at
        nxt = (max(k.box.x + k.box.w for k in hit) // g + 1) * g if step > 0 else (min(k.box.x for k in hit) - 1) // g * g
        if not may_cross(Box(min(at, nxt), ly, abs(nxt - at), 0), (nxt, ly), stand.keeps, own, g):
            return x
        at = nxt
    return None


def _back(x: int, step: int, key: Key, stand: Stand, inner: int) -> int | None:
    """The stand for an end `_free` found none for: the first clear grid step from `x` back toward the page, down to the hull end `inner` (R1488)."""
    g = stand.reach
    return next(
        (a for a in range(x - step * g, inner - step, -step * g) if fit(_arrow_at(a, step, key, stand), stand.keeps, (), stand.limits) == ()), None
    )


def _capped(own: tuple[int, int], end: int, right: int, grid: int) -> tuple[int, int]:
    """`own` with its far end held at the last grid step from `end` not past `right`: the arrow's marker stays in the content box (R1010)."""
    return (own[0], min(own[1], end + max(right - end, 0) // grid * grid)) if right else own


def _stepped(
    own: tuple[int, int], hull: tuple[int, int] | None, at: tuple[int, Fan, Collection[int]], arrows: tuple[int, int], stand: Stand
) -> tuple[int, int]:
    """`own` stepped out where an arrow stands: by `stand.reach` past the hull of an `away` lane, by the legs of a pole's arrow; then capped (R1010).

    `at` is the lane j, its fan and the `away` lanes.
    """
    j, fan, away = at
    tap_end = own[1]
    if hull and j in away and not (fan.lanes == 1 or fan.crossed):
        lo, hi = (arrows[s] and j in stand.poles[s] for s in (0, 1))
        own = (hull[0] - stand.reach if lo else own[0], hull[1] + stand.reach if hi else own[1])
        own = (own[0] - stand.reach * (j in stand.poles[0]), own[1] + (stand.reach + stand.legs) * (j in stand.poles[1]))
    elif fan.lanes == 1:
        own = (own[0], own[1] + (stand.legs + stand.reach * bool(stand.legs)) * (j in stand.poles[1]))
    own = (own[0], max(own[1], stand.drop + stand.reach)) if stand.drop and j in stand.poles[1] else own
    return _capped(own, tap_end, stand.right, stand.reach) if j in stand.poles[1] else own


def _owns(fan: Fan, taps: Sequence[tuple[Attach, int]]) -> list[tuple[int, int] | None]:
    """Per lane j the hull of the taps of pole j; a plain fan's one lane takes them all."""
    hull = _hull([v for _, v in taps])
    return [hull if fan.lanes == 1 or fan.crossed else _hull([v for a, v in taps if a.pole == j]) for j in range(fan.lanes)]


def _bare_ends(
    owns: Sequence[tuple[int, int] | None],
    fan: Fan,
    hull: tuple[int, int] | None,
    away: Collection[int],
    arrows_stand: tuple[tuple[int, int], Stand],
) -> list[tuple[int, int] | None]:
    """Per lane j its hull stepped out where an arrow stands, before any walk."""
    arrows, stand = arrows_stand
    return [_stepped(own, hull, (j, fan, away), arrows, stand) if own else None for j, own in enumerate(owns)]


class LaneEnds(NamedTuple):
    """Per lane j its drawn (x0, x1) and whether its arrow's box stood at each end (`Trunk.lane_ends`, `Trunk.stood`)."""

    ends: tuple[tuple[int, int] | None, ...]
    stood: tuple[tuple[bool, bool], ...]


def _standing(at: tuple[int, int], step: int, lane: Stand, own: Collection[str], inner: int) -> int | None:
    """The one candidate list of an arrow end: `_free` out along the lane (`lane.y` is its y), else `_back` toward the page (R1488).

    `at` is the end's x and its lane j: the arrow's (pin, kind) key is `lane.keys`.
    """
    x, j = at
    if (key := lane.keys[step > 0].get(j)) is None:
        msg = f"lane walk: lane {j} ends at a cut end whose arrow has no (pin, kind) key in Stand.keys; set it from cut_end_rooms.cut_ends"
        raise CoreError(msg)
    lane = lane._replace(options=lane.fits[step > 0].get(j, lane.options))
    out = _free(x, step, key, lane, own)
    return _back(x, step, key, lane, inner) if out is None else out


def _walked(
    at: tuple[int, tuple[int, int], tuple[int, int]], ly: int, stand: Stand, mine: Collection[str]
) -> tuple[tuple[int, int], tuple[bool, bool]]:
    """Lane j's end walked clear at each pole end, and whether each end found a stand; an end with none stays at its hull, not its bare end.

    `at` is the lane j, its bare `end` and its `hull`. A right end walks out, then back toward the page; a left end likewise (R1488).
    """
    j, end, hull = at
    lane = stand._replace(y=ly)
    lo = _standing((end[0], j), -1, lane, mine, hull[0]) if j in stand.poles[0] else end[0]
    hi = _standing((end[1], j), 1, lane, mine, hull[1]) if j in stand.poles[1] else end[1]
    return (hull[0] if lo is None else lo, hull[1] if hi is None else hi), (lo is not None, hi is not None)


def _lane_ends(
    fan: Fan,
    taps: Sequence[tuple[Attach, int]],
    away: Collection[int] = (),
    arrows: tuple[int, int] = (0, 0),
    stand: Stand = _BARE,
) -> LaneEnds:
    """Per lane j the hull of the taps of pole j; a plain fan's one lane takes them all.

    A lane in `away` runs `stand.reach` past the hull where an arrow stands (`arrows`: left, right counts); a `crossed` fan keeps it.
    A lane of `stand.poles` ends where its marker hits no `stand.keeps`.
    """
    mine = {a.pin.sym for a, _ in taps}
    owns = _owns(fan, taps)
    bare = _bare_ends(owns, fan, _hull([v for _, v in taps]), away, (arrows, stand))
    rows = lane_rows(bare)  # a lane's y has one home: the band row of its drawn lane (R1338 G1)
    walked = [
        _walked((j, end, owns[j] or end), stand.y + lane_offset(rows[j], stand.reach), stand, mine) if end and stand.keeps else (end, (True, True))
        for j, end in enumerate(bare)
    ]
    return LaneEnds(_levelled(tuple(w[0] for w in walked), stand), tuple(w[1] for w in walked))


def _levelled(out: tuple[tuple[int, int] | None, ...], stand: Stand) -> tuple[tuple[int, int] | None, ...]:
    """A continuing lane that is not a cut end's marker lane ends at the x of the marker's lane: one marker stands for the bundle (R1351, R1676).

    A lane that is no pole of the cut end stops at its last attachment.
    """
    ends = [[e[s] for j in leads if (e := out[j])] for s, leads in enumerate(stand.leads)]
    rest = [stand.poles[s] - stand.leads[s] for s in (0, 1)]
    return tuple(
        (min(ends[0], default=e[0]) if j in rest[0] else e[0], max(ends[1], default=e[1]) if j in rest[1] else e[1]) if e else e
        for j, e in enumerate(out)
    )


def continuing(fan: Fan, here: Collection[str], cut: Collection[int] = ()) -> frozenset[int]:
    """The poles with an attachment whose symbol is not in `here`, or whose lane ends at a cut end `cut`: their nets continue."""
    return frozenset(a.pole for a in (*fan.drivers, *fan.legs) if a.pin.sym not in here) | frozenset(cut)


def page_syms(env: PageEnv) -> frozenset[str]:
    """Every symbol standing on this page: cells of its columns and the anchors of its cards."""
    cells = {c.sym for pc in env.pcs.values() for lane in pc.lanes for c in lane}
    cards = {env.blocks[b].anchor for row in env.plan.rows for b in row.blocks}
    return frozenset(cells | {a for a in cards if a})


def taps_x(env: PageEnv, x: Mapping[str, int], fan: Fan, r: int, placed: Mapping[str, Placed] | None = None) -> Taps:
    """Each attachment of the fan in row r with its x and y: the placed pin if `placed` holds it, else its column lane or card pin (y None)."""
    out: list[tuple[Attach, int, int | None]] = []
    for a in (*fan.drivers, *fan.legs):
        if not in_row(env, fan, a, r):
            continue
        if here := (placed or {}).get(a.pin.sym):
            if (pin := next((q for q in here.pin_xy if q.pin == a.pin.pin), None)) is None:
                msg = f"placed {a.pin.sym} lacks pin {a.pin.pin} of fan {fan.id}: its pin_xy must list every pin a fan attaches to"
                raise CoreError(msg)
            out.append((a, pin.x, pin.y))
        elif a.column is not None:
            out.append((a, x[col_node(a.column)] + env.pcs[a.column].offsets[a.lane], None))
        elif box_at(env, a.pin.sym) is not None:
            out.append((a, box_pin_x(env, x, a.pin.sym, a.pin.pin), None))
    return tuple(out)


def _marker_keeps(env: PageEnv, placed: Mapping[str, Placed]) -> Iterable[Keep]:
    """The keep of each marker the page hangs at a placed pin: a trunk-end marker walks clear of them too (KI-297)."""
    for (sym, pin, orient), hs in env.hangings.items():
        if (p := placed.get(sym)) is not None and p.orient == orient and (at := next((q for q in p.pin_xy if q.pin == pin), None)):
            yield from (hanging_keep(h, (at.x, at.y), sym, None) for h in hs if KEEP_KIND[h.kind] == "marker")


def stand_of(
    env: PageEnv,
    at: tuple[int, tuple[int, int] | None],
    keeps: Sequence[Keep],
    placed: Mapping[str, Placed],
    columns: Iterable[tuple[str, int, Taps]],
) -> Stand:
    """The stand of a trunk at y over `keeps` (the footprints and the markers hung at the placed pins) and the "wire" keeps of `columns` (R1022).

    `at` is the trunk's y and its row band. `columns` is each other fan's (id, trunk y, taps_x); a column runs from its pin to its trunk.
    """
    y, band = at
    cols = list(columns)
    walls = (Keep("", Box(px, min(py, ty), 0, abs(py - ty)), "wire", fid) for fid, ty, ts in cols for _, px, py in ts if py is not None and py != ty)
    lines = (
        Keep("", Box(h[0], ty, h[1] - h[0], 0), "wire", fid) for fid, ty, ts in cols if (h := _hull([px for _, px, _ in ts]))
    )  # R1331: other fans' trunks
    marker = env.options.link_fit or env.options.marker
    right = env.problem.area.w - env.options.margin.w - (marker["R0"].w if marker else 0)
    return Stand(
        env.options.wiring_grid,
        y,
        env.options,
        (*keeps, *walls, *lines),
        placed=placed,
        limits=Limits(env.problem.area, band, (env.options.margin.w, env.options.margin.h)),
        right=right,
    )


def drawn_lane_ends(env: PageEnv, x: Mapping[str, int], fan: Fan, r: int, stand: Stand | None = None) -> LaneEnds:
    """Per lane j the drawn (x0, x1) and its stands, as Trunk.lane_ends and Trunk.stood: the one call of `_lane_ends`.

    With a `stand`, an arrowed end clears every footprint on the page that its marker hits (R906).
    """
    stand = stand or Stand(env.options.wiring_grid)
    taps = [(a, v) for a, v, _ in taps_x(env, x, fan, r, stand.placed)]
    legs = leg_pins(fan, leg_rows(env.refs, env.plan.page), r)
    poles = arrow_poles(fan, env.refs, env.plan, r)
    ends = cut_ends(env.refs, env.plan, (fan,), r)
    keys, fits = (_keys(ends, right=False), _keys(ends, right=True)), (_fits(ends, env.options, right=False), _fits(ends, env.options, right=True))
    stand = stand._replace(
        poles=poles,
        leads=arrow_leads(fan, env.refs, env.plan, r),
        legs=leg_unit(legs, leg_fit(env.options, env.refs, env.plan.page)),
        keys=keys,
        fits=fits,
    )
    return _lane_ends(fan, taps, continuing(fan, page_syms(env), poles[0] | poles[1]), arrow_ends(env.refs, env.plan, (fan,), r), stand)


def _keys(ends: Iterable[CutEnd], *, right: bool) -> dict[int, Key]:
    """Per pole the (pin, kind) key of the arrow its lane ends at, at the left or the right end."""
    return {p: (pin, c.key[1]) for c in ends if c.right is right and (pin := c.key[0]) is not None for p in c.poles}


def _fits(ends: Iterable[CutEnd], options: Options, *, right: bool) -> dict[int, Options]:
    """Per pole the options sized for the lines its marker's ledger end holds (R1598)."""
    return {
        p: sized(options, (pin, c.key[1]), c.end.also, c.end.far) for c in ends if c.right is right and (pin := c.key[0]) is not None for p in c.poles
    }


def lane_segments(env: PageEnv, x: Mapping[str, int], fan: Fan, r: int) -> tuple[tuple[int, int, int] | None, ...]:
    """Per lane j (dy, x0, x1): the drawn lane (as Trunk.lane_ends) plus the arrow keep.

    Where an arrow is planned at an end, a continuing lane (every lane of a plain fan) grows
    by the marker width beyond its drawn end. A lane with no taps is None.
    """
    poles = arrow_poles(fan, env.refs, env.plan, r)
    away, arrows = continuing(fan, page_syms(env), poles[0] | poles[1]), arrow_ends(env.refs, env.plan, (fan,), r)
    wide = reserve(1, env.options)
    out: list[tuple[int, int, int] | None] = []
    ends = drawn_lane_ends(env, x, fan, r).ends
    rows = lane_rows(ends)
    for j, e in enumerate(ends):
        keep = fan.lanes == 1 or j in away
        dy = lane_offset(rows[j], env.options.wiring_grid)
        left, right = (wide if n and keep else 0 for n in arrows)
        out.append(None if e is None else (dy, e[0] - left, e[1] + right))
    return tuple(out)
