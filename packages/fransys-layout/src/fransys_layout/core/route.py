"""Stage 6, route: route_pages(placement, cut, problem, options) -> Routes.

Per page: lane wires and joins, jogs nested by E6, trunks with drops, then cross-links by A*
(`negotiate`: soft rounds that price R391, a final check, a hard repair of what failed). Every conductor
no path was found for is a `Refused` the reference loop draws as a reference (ROUTE-FALLBACK-REFERENCE).
"""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from .band import lane_offset
from .flow_values import CrossLink
from .geometry import row_of
from .jog_rows import taken_rows
from .junctions import page_junctions
from .net_keys import net_of_key
from .occupancy import Occupancy
from .outputs import PageRoutes, Refused, Routes, Wire
from .route_counts import counts, demand
from .route_env import Drawn, body_hit, hard_keeps, lost_key, pin_point, route_envs, withheld
from .route_fixed import Fixed, Laid, fixed_page, fixed_wires
from .route_guard import guard
from .route_labels import page_labels
from .route_leads import lead_wires
from .route_negotiate import Negotiated, negotiate
from .route_tree import mark_anchors, tree
from .route_wires import join_wires, lane_wires, nest_jogs
from .score_wiring import bundles
from .values import Box, Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .clearance import Keep
    from .flow_values import CutResult
    from .jog_rows import Taken
    from .outputs import Placement
    from .route_env import RouteEnv
    from .values import Options, PlacementProblem


def _taken(env: RouteEnv, laid: Drawn) -> tuple[Taken, ...]:
    """The rows a jog bend must not land on: trunk lane lines, laid runs and wire ends (R428)."""
    grid = env.options.wiring_grid
    lines = [(t.y + (lane_offset(k, grid) if env.fans[t.fan].lanes > 1 else 0), t.x0, t.x1) for t in env.trunks for k in range(t.lanes)]
    runs = [s for w in laid.wires for s in pairwise(w.points)]
    ends = [(w.points[i][1], w.points[i][0], w.points[i][0]) for w in laid.wires for i in (0, -1)]
    return (*lines, *taken_rows(runs), *ends)


def _fixed_wires(env: RouteEnv, fixed: Fixed) -> Drawn:
    """Lane wires, joins and nested jogs of one page, between its leads and its trunks (stage 6a's)."""
    out = lead_wires(env)
    for col in env.columns:
        out += lane_wires(env, col) + join_wires(env, col)
    jogs = tuple(j for j in out.jogs if lost_key(j.net, j.ends) not in env.lost)
    nested = nest_jogs(env, jogs, _taken(env, out), hard_keeps(env))
    out = Drawn(out.wires + nested.wires, (), out.findings + nested.findings, out.rises, out.lost + nested.lost)
    return out + fixed.trunks


def _cells(extent: int, room: int | None, step: int, spare: int) -> int:
    """Grid cells along one axis: the content box `room` the caller passes, else extent and spare.

    The box is the bound, not the drawn extent (R424); layout-0334: what stands past it keeps
    the cells it needs.
    """
    if room is None:
        return extent // step + spare
    return max(room // step + 1, extent // step + 1)


def _admit_port(grid: Occupancy, port: tuple[int, int], owner: str, net: str) -> None:
    """The owner's wire of `net` may enter the cell that holds its pin's real point (R-A).

    An off-grid pin is admitted at the cell holding its point, never skipped.
    """
    grid.admit((port[0] // grid.step, port[1] // grid.step), owner, net)


def _mark_edge_ring(grid: Occupancy) -> None:
    """A lane keeps one step inside the content box: the grid's outer ring is hard (G09-PAGE)."""
    s, w, h = grid.step, grid.cols * grid.step, grid.rows * grid.step
    for edge in (Box(0, 0, w, s), Box(0, h - s, w, s), Box(0, 0, s, h), Box(w - s, 0, s, h)):
        grid.mark_box(edge)


def _mark_fixed(env: RouteEnv, grid: Occupancy) -> None:
    """Every footprint and obstacle box is hard; each owner is admitted at its pins' port cells."""
    _mark_edge_ring(grid)
    nets = {(r.sym, r.pin): n for n, refs in env.net_pins.items() for r in refs}
    for sym, p in env.placed.items():
        grid.mark_closed(p.footprint)
        for q in p.pin_xy:
            if (sym, q.pin) in nets:
                _admit_port(grid, (q.x, q.y), sym, nets[sym, q.pin])
    for k in env.obstacles:
        grid.mark_closed(k.box)
        if k.port is not None and k.net is not None:
            _admit_port(grid, k.port, k.owner, k.net)
    for net, points in env.blocked_ends.items():  # the blocked foreign port ends no wire passes (R472)
        for point in points:
            grid.mark_end(net, point)


def _grid(env: RouteEnv, fixed: Sequence[Wire], texts: Sequence[Keep] = ()) -> Occupancy:
    """A map that holds every footprint, wire, label and pin of the page, so none indexes off it."""
    step = env.options.wiring_grid
    xs = [p.footprint.x + p.footprint.w for p in env.placed.values()]
    ys = [p.footprint.y + p.footprint.h for p in env.placed.values()]
    pts = [pt for w in fixed for pt in w.points]
    xs += [x for x, _ in pts] + [k.box.x + k.box.w for k in (*env.obstacles, *texts)]
    ys += [y for _, y in pts] + [k.box.y + k.box.h for k in (*env.obstacles, *texts)]
    area = env.area
    grid = Occupancy(
        _cells(max(xs, default=0), None if area is None else area.w, step, env.options.spare_cells),
        _cells(max(ys, default=0), None if area is None else area.h, step, env.options.spare_cells),
        step,
    )
    _mark_fixed(env, grid)
    for w in fixed:
        grid.mark_wire(w.net, w.points)
    for k in texts:  # a label's interior: touching its side is clear, as it is for the label (layout-0472)
        grid.mark_box(k.box)
    return grid


def _row_wrapped(env: RouteEnv, linked: frozenset[str]) -> list[CrossLink]:
    """A fan with no trunk and no arrow whose attachments stand in different rows is a link."""
    trunked = {t.fan for t in env.trunks}
    out = []
    for fan in env.fans.values():
        net, ends = fan.nets[0], (*fan.drivers, *fan.legs)
        pts = [pin_point(env, a.pin.sym, a.pin.pin) for a in ends]
        if fan.lanes != 1 or fan.id in trunked or net in env.cut_nets or net in linked:
            continue
        if all(pts) and len({row_of(env.bands, p[1]) for p in pts if p}) > 1:
            out.append(CrossLink(net, ends))
    return out


def _links_here(env: RouteEnv) -> tuple[list[CrossLink], list[Refused]]:
    """Cross-links with an end on this page; a cut one still joins its ends here (R417).

    A link already lost is withheld; one with ends on another page and no reference is lost here.
    """
    todo: list[CrossLink] = _row_wrapped(env, frozenset(ln.net for ln in env.cross_links))
    out: list[Refused] = []
    for link in env.cross_links:
        here = [a for a in link.ends if a.pin.sym in env.placed]
        ends = tuple(a.pin for a in here)
        if link.tagged or (here and lost_key(link.net, ends) in env.lost):
            continue  # a tag pair joins its ends (layout-0440); a lost link's pins carry a reference (ROUTE-FALLBACK-REFERENCE)
        if link.net in env.cut_nets and len(here) > 1:
            todo.append(CrossLink(link.net, tuple(here)))
        if not here or link.net in env.cut_nets:
            continue
        if len(here) == len(link.ends):
            todo.append(link)
        else:
            out.append(Refused(link.net, ends))
    return todo, out


def _bare_routes(env: RouteEnv, todo: Sequence[CrossLink]) -> dict[str, tuple[Wire, ...]]:
    """Each link routed alone on footprints and obstacles only: the wires `demand` is read from."""
    bare = _grid(env, ())
    out: dict[str, tuple[Wire, ...]] = {}
    for link in todo:
        wires = tree(env, bare, link)
        bare.remove_net(link.net)
        if wires:
            out[link.net] = wires
    return out


def _lost(todo: Sequence[CrossLink], nego: Negotiated) -> list[Refused]:
    """A `Refused` for each rise and link no legal route was found for."""
    rises = [Refused(r.net, (r.pin,)) for r in nego.lost]
    links = [Refused(ln.net, tuple(a.pin for a in ln.ends)) for ln in todo if ln.net in nego.failed]
    return [*rises, *links]


def _span(env: RouteEnv, link: CrossLink) -> int:
    """The half-perimeter of the link's pins: the lay order, shortest first, ties as given."""
    xs, ys = zip(*(pt for a in link.ends if (pt := pin_point(env, a.pin.sym, a.pin.pin))), strict=True)
    return int(max(xs) - min(xs) + max(ys) - min(ys))


def through_bodies(env: RouteEnv, wires: Sequence[Wire]) -> list[Finding]:
    """WIRE_THROUGH_BODY (an error, layout-0480, layout-0541): one finding per wire with a run through a drawn body or along its outline.

    The outline is the symdef body_box, closed; a point touch is looks (R1164).
    """
    out: list[Finding] = []
    for w in wires:
        if hit := body_hit(env, w.net, w.points):
            net = net_of_key(w.net)
            text = f"net {net} draws a {w.kind} wire from {w.points[0]} to {w.points[-1]} through the body of {hit.owner}"
            out.append(Finding("WIRE_THROUGH_BODY", text, env.page, net))
    return out


def route_page(env: RouteEnv, fixed: Fixed | None = None) -> tuple[PageRoutes, tuple[Refused, ...], tuple[Finding, ...]]:
    """One page's routes, the nets it gave up on, and its findings; `fixed` is stage 6a's, laid before the markers."""
    drawn = guard(env, _grid(env, ()), _fixed_wires(env, fixed or fixed_page(env)))
    labels, standing, unplaced, needs = page_labels(env, drawn.wires)
    todo, split = _links_here(env)
    todo = sorted(todo, key=lambda ln: _span(env, ln))
    grid = _grid(env, drawn.wires, standing)
    for link in todo:
        mark_anchors(env, grid, link)
    nego = negotiate(env, grid, todo, drawn.rises)
    lost = {lost_key(r.net, r.ends or ()): r for r in (*drawn.lost, *split, *_lost(todo, nego))}
    wires = drawn.wires + nego.risen + tuple(w for ws in nego.routed.values() for w in ws)
    bare = _bare_routes(env, todo)
    wanted = drawn.wires + nego.risen + tuple(w for ws in bare.values() for w in ws)
    page = PageRoutes(
        env.page,
        wires,
        demand(wanted, env.gaps),
        counts(wires, bundles(env.fans.values())),
        page_junctions(env, wires),
        labels,
        needs,
    )
    return page, tuple(lost.values()), (*drawn.findings, *through_bodies(env, wires), *unplaced)


def _laid_on(env: RouteEnv, problem: PlacementProblem, laid: Laid) -> RouteEnv:
    """The page env with its markers, its annexes and the labels the round before stood."""
    return replace(
        env,
        markers=tuple(m for m in laid.markers if m.page == env.page),
        annexes=tuple(a for a in problem.annexes if a.owner in env.placed),
        labels=(laid.fixed or {}).get(env.page, Fixed(Drawn())).labels,
    )


def route_pages(
    placement: Placement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    laid: Laid | None = None,
) -> Routes:
    """Stage 6: the wires of every placed page, with demand and counts.

    `laid.keeps` are boxes no wire cell may enter but its owner's wires; `laid.fixed` is stage 6a's
    trunks, laid here when none is given.
    """
    laid = laid or Laid()
    fixed = fixed_wires(placement, cut, problem, options) if laid.fixed is None else laid.fixed
    envs = withheld(route_envs(placement, cut, problem, options, laid.keeps), laid.lost)
    results = [route_page(env, fixed[env.page]) for env in (_laid_on(e, problem, laid) for e in envs)]
    return Routes(
        tuple(r[0] for r in results),
        tuple(n for r in results for n in r[1]),
        tuple(f for r in results for f in r[2]),
    )
