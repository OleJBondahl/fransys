"""Stage 6 environment: what one page's wires read, built once per page from stages 1 to 5.

`Drawn` is what a wire-making function returns; nothing here draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import pairwise
from typing import TYPE_CHECKING

from .arrow_reserve import arrow_rows, leg_feet, leg_fit, leg_lines, leg_rows
from .clearance import Keep, fan_own, pin_points, through_keeps
from .errors import CoreError
from .net_keys import net_of_key, port_key
from .outputs import Marker, Refused, Wire
from .sides import step_out
from .values import Box, Finding, PinRef

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .annex_values import Annex, AnnexBox
    from .arrow_reserve import ArrowEnds
    from .flow_values import Column, CrossLink, CutResult, Fan
    from .outputs import Gap, PagePlacement, Placed, Placement, Trunk
    from .values import XY, Options, Orientation, PlacementProblem, Side, Size, WireKind


@dataclass(frozen=True, slots=True)
class Jog:
    """A pin-to-pin wire whose ends differ in x: top end, bottom end, and its net.

    `source_top` says which end is the source E6 orders by: the top pin of a jog, the joined
    lane's pin of a join.
    """

    net: str
    top: XY
    bottom: XY
    drawn_as: WireKind = "straight"
    source_top: bool = True
    ends: tuple[PinRef, ...] = ()

    @property
    def source_x(self) -> int:
        return (self.top if self.source_top else self.bottom)[0]

    @property
    def dest_x(self) -> int:
        return (self.bottom if self.source_top else self.top)[0]


@dataclass(frozen=True, slots=True)
class Rise:
    """A drop or riser whose straight vertical passes a foreign body: A* routes it to `target`."""

    net: str
    pin: PinRef
    start: XY
    target: XY
    drawn_as: WireKind


@dataclass(frozen=True, slots=True)
class Drawn:
    """Wires, jogs still to be nested, the findings of what could not be drawn, and the rises."""

    wires: tuple[Wire, ...] = ()
    jogs: tuple[Jog, ...] = ()
    findings: tuple[Finding, ...] = ()
    rises: tuple[Rise, ...] = ()
    lost: tuple[Refused, ...] = ()

    def __add__(self, other: Drawn) -> Drawn:
        return Drawn(
            self.wires + other.wires,
            self.jogs + other.jogs,
            self.findings + other.findings,
            self.rises + other.rises,
            self.lost + other.lost,
        )


@dataclass(frozen=True, slots=True)
class RouteEnv:
    """Everything stage 6 reads for one page, so no function takes more than five parameters."""

    page: int
    placed: Mapping[str, Placed]
    columns: tuple[Column, ...]
    net_of: Mapping[PinRef, str]
    net_pins: Mapping[str, tuple[PinRef, ...]]
    fans: Mapping[str, Fan]
    gaps: tuple[Gap, ...]
    trunks: tuple[Trunk, ...]
    bands: tuple[tuple[int, int], ...]
    cross_links: tuple[CrossLink, ...]
    cut_nets: frozenset[str]
    options: Options
    obstacles: tuple[Keep, ...] = ()
    sides: Mapping[tuple[str, str, Orientation], Side] = field(default_factory=dict)
    # layout-0334: the content box; the router searches no cell past it (None: no bound)
    area: Size | None = None
    leads: frozenset[PinRef] = frozenset()
    # R472, layout-0390: the foreign port ends no wire passes, built once: a sentinel net per
    # box pin of no net, to its pin point and the cell its stem steps out to
    blocked_ends: Mapping[str, tuple[XY, ...]] = field(default_factory=dict)
    # (net, upper pin, lower pin) of each connection a fan deals between two cells of a lane: the trunk draws it (R1519)
    dealt: frozenset[tuple[str, PinRef, PinRef]] = frozenset()
    # the one-sided pins that stand a leg, each with the row of the trunk end the leg hangs from (ONE-SIDED-PIN)
    legs: Mapping[PinRef, int] = field(default_factory=dict)
    # the page, fan and row of each trunk that stands an arrow at its right end (R875)
    arrowed: ArrowEnds = field(default_factory=dict)
    # each leg's line from the cut x to its marker's foot, by (fan, row, pole): the one line the marker stage stands at too
    leg_lines: Mapping[tuple[str, int, PinRef], tuple[XY, XY, XY]] = field(default_factory=dict)
    # the symbol pairs of lane cells joined by a cross-link, not a lane wire (layout-0482)
    joined: frozenset[frozenset[str]] = frozenset()
    # the conductors the loop withholds: each lost link, jog or rise by `lost_key` (ROUTE-FALLBACK-REFERENCE)
    lost: frozenset[LostKey] = frozenset()
    # the page's reference markers once they stand: a lead runs to the near edge of each one that stands out on its pin's line (MARKER-FREE-SIDE)
    markers: tuple[Marker, ...] = ()
    # the annexes of the symbols on this page, in the problem's order, and the labels the round before stood (TAG-CORNERS)
    annexes: tuple[Annex, ...] = ()
    labels: tuple[AnnexBox, ...] = ()
    # the runs of a strip on this page, whose tags are among the annexes (STRIP-TAG-ONCE)
    runs: Mapping[str, tuple[str, Placed]] = field(default_factory=dict)
    # the anchors' leads on this page, pin to port: wire ink for the label stage only
    anchor_leads: tuple[Wire, ...] = ()


type LostKey = tuple[str, frozenset[PinRef]]


def lost_key(net: str, ends: Sequence[PinRef]) -> LostKey:
    """The one key of a lost conductor: its net and all its pins, in no order."""
    return net, frozenset(ends)


def pin_point(env: RouteEnv, sym: str, pin: str) -> XY | None:
    """The one lookup of a placed pin; None when the symbol or the pin is not on this page."""
    placed = env.placed.get(sym)
    if placed is None:
        return None
    return next(((q.x, q.y) for q in placed.pin_xy if q.pin == pin), None)


def pin_side(env: RouteEnv, sym: str, pin: str) -> Side:
    """The one lookup of the side a placed pin faces; a pin `env.sides` lacks raises CoreError."""
    key = (sym, pin, env.placed[sym].orient)
    if key not in env.sides:
        msg = f"the placed pin {sym}.{pin} turned {key[2]} has no side in the symdef layer's table; measure every orientation of every placed pin"
        raise CoreError(msg)
    return env.sides[key]


def body_keeps(placed: Iterable[Placed]) -> tuple[Keep, ...]:
    """A keep for each placed body, never its soft tag room: the one build the router and the marker stand read (R2282)."""
    return tuple(Keep("", p.body, "body", p.sym) for p in placed)


def hard_keeps(env: RouteEnv) -> tuple[Keep, ...]:
    """The one keep set a wire must not run through: each placed body and the page obstacles (layout-0495)."""
    return body_keeps(env.placed.values()) + tuple(env.obstacles)


def body_hit(env: RouteEnv, net: str, points: Sequence[XY]) -> Keep | None:
    """The first body a run of the wire `points` of `net` passes, through or along its outline, its own pins' bodies too (R1164, layout-0541)."""
    keeps, pins = tuple(k for k in hard_keeps(env) if k.kind == "body"), pin_points(env.placed)
    own, ends = own_syms(env, net_of_key(net), net), (points[0], points[-1])
    runs = (Box(min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)) for (ax, ay), (bx, by) in pairwise(points))
    return next((k for run in runs for k in through_keeps(run, keeps, ends, own, pins)), None)


def own_syms(env: RouteEnv, net: str, fan: str | None = None) -> frozenset[str]:
    """The symbols a wire belongs to: the net's pins and those of its fan (R515, R-A)."""
    own = frozenset(r.sym for r in env.net_pins.get(net, ()))
    home = env.fans.get(fan) or next((f for f in env.fans.values() if f.lanes > 1 and fan in f.nets), None)
    return own | fan_own(home) if home is not None else own


def _page_columns(cut: CutResult, page: int) -> tuple[Column, ...]:
    plan = next(p for p in cut.spec.pages if p.page == page)
    named = {c for row in plan.rows for c in row.columns}
    return tuple(c for c in cut.flow.columns if c.id in named)


def pin_sides(problem: PlacementProblem) -> dict[tuple[str, str, Orientation], Side]:
    """The side every pin faces at each orientation its symbol has a view for."""
    return {(s.id, p.id, o): turn.side for s in problem.symbols for o, view in s.views.items() for p, turn in zip(s.pins, view.pins, strict=True)}


def blocked_port_ends(
    pg: PagePlacement,
    problem: PlacementProblem,
    net_of: Mapping[PinRef, str],
    sides: Mapping[tuple[str, str, Orientation], Side],
    step: int,
) -> dict[str, tuple[XY, ...]]:
    """A box pin of no net still ends a stem (a reference arrow): its point and step-out cell."""
    boxes = frozenset(s.id for s in problem.symbols if s.box is not None)
    out: dict[str, tuple[XY, ...]] = {}
    for placed in pg.placed:
        for q in placed.pin_xy:
            side = sides.get((placed.sym, q.pin, placed.orient))
            if placed.sym in boxes and PinRef(placed.sym, q.pin) not in net_of and side:
                out[port_key(net_of, PinRef(placed.sym, q.pin))] = (
                    (q.x, q.y),
                    step_out(side, q.x, q.y, step),
                )
    return out


def dealt_pairs(fans: Mapping[str, Fan]) -> frozenset[tuple[str, PinRef, PinRef]]:
    """The (net, upper pin, lower pin) each fan deals from a driver to a leg of one lane.

    The trunk draws that connection (drop, trunk line, drop), so the column draws no wire for it (R1519).
    """
    return frozenset(
        (f.nets[d.pole], d.pin, g.pin)
        for f in fans.values()
        for d in f.drivers
        for g in f.legs
        if g.pole == d.pole < len(f.nets) and (g.column, g.lane) == (d.column, d.lane)
    )


def _page_env(
    pg: PagePlacement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    obstacles: Sequence[Keep],
) -> RouteEnv:
    net_of = {ref: n.id for n in problem.nets for ref in n.pins}
    net_pins = {n.id: n.pins for n in problem.nets}
    fans = {f.id: f for f in cut.flow.fans}
    cut_nets = frozenset(r.net for r in cut.spec.reference_plan)
    sides = pin_sides(problem)
    arrowed = arrow_rows(cut.spec.reference_plan, cut.spec.pages, cut.flow.fans)
    lines = leg_lines(
        pg.trunks,
        fans,
        leg_rows(cut.spec.reference_plan, pg.page),
        leg_fit(options, cut.spec.reference_plan, pg.page),
        (leg_feet(pg.placed, pg.hangings), arrowed, problem.area),
    )
    return RouteEnv(
        pg.page,
        {p.sym: p for p in pg.placed},
        _page_columns(cut, pg.page),
        net_of,
        net_pins,
        fans,
        pg.gaps,
        pg.trunks,
        pg.bands,
        cut.flow.cross_links,
        cut_nets,
        options,
        tuple(obstacles),
        sides,
        problem.area,
        cut.spec.leads,
        blocked_port_ends(pg, problem, net_of, sides, options.wiring_grid),
        dealt_pairs(fans),
        {pin: row for _, row, pin in lines},
        arrowed,
        lines,
        cut.flow.joined,
    )


def route_envs(
    placement: Placement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    obstacles: Sequence[Keep] = (),
) -> tuple[RouteEnv, ...]:
    """One env per placed page, in the placement's order; `obstacles` block cells on every page."""
    return tuple(_page_env(pg, cut, problem, options, obstacles) for pg in placement.pages)


def z_points(a: XY, b: XY, level: int) -> tuple[XY, ...]:
    """The one Z: a down to `level` in y, across to b's x, on to b."""
    pts = (a, (a[0], level), (b[0], level), b)
    return tuple(p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1])


def z_wire(net: str, page: int, ends: tuple[XY, XY], level: int, kind: WireKind = "straight") -> Wire:
    """A jog, a join, a drop of a crossed bundle: pin to `level` in y, across, on to the pin."""
    return Wire(net, page, z_points(ends[0], ends[1], level), kind)


def withheld(envs: Sequence[RouteEnv], lost: frozenset[LostKey]) -> tuple[RouteEnv, ...]:
    """The page envs with the lost conductors the loop withholds."""
    return tuple(replace(e, lost=lost) for e in envs)
