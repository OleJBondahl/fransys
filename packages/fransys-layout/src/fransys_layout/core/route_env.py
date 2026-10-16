"""Stage 6 environment: what one page's wires read, built once per page from stages 1 to 5.

`Drawn` is what a wire-making function returns; nothing here draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .outputs import Wire
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .outputs import Gap, PagePlacement, Placed, Placement, Trunk
    from .values import (
        XY,
        Box,
        Column,
        CrossLink,
        CutResult,
        Fan,
        Options,
        PinRef,
        PlacementProblem,
        Side,
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
    sides: Mapping[tuple[str, str], Side] = field(default_factory=dict)


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


def pin_sides(problem: PlacementProblem) -> dict[tuple[str, str], Side]:
    """The turned side of every pin, keyed by (symbol id, pin id)."""
    return {(s.id, p.id): p.side for s in problem.symbols for p in s.pins}


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
        pin_sides(problem),
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
