"""Stage 6 environment: what one page's wires read, built once per page from stages 1 to 5.

`Drawn` is what a wire-making function returns; nothing here draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .outputs import Wire
from .sides import step_out
from .values import Finding, PinRef

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from .outputs import Gap, PagePlacement, Placed, Placement, Trunk
    from .values import (
        XY,
        Box,
        Column,
        CrossLink,
        CutResult,
        Fan,
        Options,
        Orientation,
        PlacementProblem,
        Side,
        Size,
        WireKind,
    )


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
    sym: str
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

    def __add__(self, other: Drawn) -> Drawn:
        return Drawn(
            self.wires + other.wires,
            self.jogs + other.jogs,
            self.findings + other.findings,
            self.rises + other.rises,
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
    obstacles: tuple[Box, ...] = ()
    sides: Mapping[tuple[str, str, Orientation], Side] = field(default_factory=dict)
    # layout-0334: the content box; the router searches no cell past it (None: no bound)
    area: Size | None = None
    leads: Mapping[PinRef, str] = field(default_factory=dict)
    # R472, layout-0390: the foreign port ends no wire passes, built once: a sentinel net per
    # box pin of no net, to its pin point and the cell its stem steps out to
    blocked_ends: Mapping[str, tuple[XY, ...]] = field(default_factory=dict)
    # (net, upper pin, lower pin) of each lane a bundle fan carries between two cells (BUNDLE)
    bundled: frozenset[tuple[str, PinRef, PinRef]] = frozenset()


def failed(env: RouteEnv, subject: str, text: str) -> Finding:
    """A ROUTE_FAILED finding on this page; the text names the thing and the fix."""
    return Finding("ROUTE_FAILED", text, env.page, subject)


def row_band(env: RouteEnv, trunk: Trunk) -> tuple[int, int]:
    """(top, bottom) of the row a trunk stands in: the band its drops are limited to."""
    return env.bands[trunk.row]


def pin_point(env: RouteEnv, sym: str, pin: str) -> XY | None:
    """The one lookup of a placed pin; None when the symbol or the pin is not on this page."""
    placed = env.placed.get(sym)
    if placed is None:
        return None
    return next(((q.x, q.y) for q in placed.pin_xy if q.pin == pin), None)


def _page_columns(cut: CutResult, page: int) -> tuple[Column, ...]:
    plan = next(p for p in cut.spec.pages if p.page == page)
    named = {c for row in plan.rows for c in row.columns}
    return tuple(c for c in cut.flow.columns if c.id in named)


def pin_sides(problem: PlacementProblem) -> dict[tuple[str, str, Orientation], Side]:
    """The side every pin faces at each orientation its symbol has a view for."""
    return {
        (s.id, p.id, o): turn.side
        for s in problem.symbols
        for o, view in s.views.items()
        for p, turn in zip(s.pins, view.pins, strict=True)
    }


def lone_cut_pins(problem: PlacementProblem) -> frozenset[PinRef]:
    """The pins of cut nets with no other end: the ones a bundle fan may take as lanes (R499)."""
    return frozenset(c.pin for n in problem.nets if len(n.pins) == 1 for c in n.cut)


def lead_pins(problem: PlacementProblem, fans: Iterable[Fan]) -> dict[PinRef, str]:
    """The cut pins alone on their net and on no fan, each with its line: no wire joins them."""
    laned = {a.pin for f in fans for a in (*f.drivers, *f.legs)}
    return {
        c.pin: c.line for n in problem.nets if len(n.pins) == 1 for c in n.cut if c.pin not in laned
    }


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
                out[f"pin:{placed.sym}.{q.pin}"] = ((q.x, q.y), step_out(side, q.x, q.y, step))
    return out


def bundled_pairs(fans: Mapping[str, Fan]) -> frozenset[tuple[str, PinRef, PinRef]]:
    """The (net, upper pin, lower pin) each bundle lane carries from a driver to a leg of one lane.

    The bundle draws that connection (drop, lane line, drop), so the column draws no wire for it.
    """
    return frozenset(
        (f.nets[d.pole], d.pin, g.pin)
        for f in fans.values()
        if f.lanes > 1
        for d in f.drivers
        for g in f.legs
        if g.pole == d.pole < len(f.nets) and (g.column, g.lane) == (d.column, d.lane)
    )


def _page_env(
    pg: PagePlacement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    obstacles: Sequence[Box],
) -> RouteEnv:
    net_of = {ref: n.id for n in problem.nets for ref in n.pins}
    net_pins = {n.id: n.pins for n in problem.nets}
    fans = {f.id: f for f in cut.flow.fans}
    cut_nets = frozenset(r.net for r in cut.spec.reference_plan)
    sides = pin_sides(problem)
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
        lead_pins(problem, cut.flow.fans),
        blocked_port_ends(pg, problem, net_of, sides, options.wiring_grid),
        bundled_pairs(fans),
    )


def route_envs(
    placement: Placement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    obstacles: Sequence[Box] = (),
) -> tuple[RouteEnv, ...]:
    """One env per placed page, in the placement's order; `obstacles` block cells on every page."""
    return tuple(_page_env(pg, cut, problem, options, obstacles) for pg in placement.pages)


def z_points(a: XY, b: XY, level: int) -> tuple[XY, ...]:
    """The one Z: a down to `level` in y, across to b's x, on to b."""
    pts = (a, (a[0], level), (b[0], level), b)
    return tuple(p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1])


def z_wire(
    net: str, page: int, ends: tuple[XY, XY], level: int, kind: WireKind = "straight"
) -> Wire:
    """A jog, a join, a drop of a crossed bundle: pin to `level` in y, across, on to the pin."""
    return Wire(net, page, z_points(ends[0], ends[1], level), kind)
