"""Stage 6, route: route_pages(placement, cut, problem, options) -> Routes.

Per page: lane wires and joins, jogs nested by E6, trunks with drops, then cross-links by A*
(smallest bounding box first, `reroute_rounds` rip-ups of the three worst). Every refusal is a
`ROUTE_FAILED` finding naming the thing and the fix; no wire is drawn for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING

from .band import lane_offset
from .jog_rows import taken_rows
from .keys import natural_key
from .occupancy import Occupancy
from .outputs import PageRoutes, Refused, Routes, Wire
from .route_counts import counts, crossings_by_net, demand
from .route_env import Drawn, failed, pin_point, route_envs
from .route_guard import guard
from .route_leads import lead_wires
from .route_tree import mark_anchors, rise_wire, tree
from .route_trunk import trunk_wires
from .route_wires import join_wires, lane_wires, nest_jogs
from .score_wiring import bundles
from .values import CrossLink

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .jog_rows import Taken
    from .outputs import Placement
    from .route_env import RouteEnv
    from .values import Box, CutResult, Finding, Options, PlacementProblem

WORST = 3  # links ripped up and rerouted per round


@dataclass(slots=True)
class LinkState:
    """The links of one page while they are routed: wires per net, nets given up, findings."""

    env: RouteEnv
    grid: Occupancy
    routed: dict[str, tuple[Wire, ...]] = field(default_factory=dict)
    bare: dict[str, tuple[Wire, ...]] = field(default_factory=dict)
    failed: dict[str, Refused] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


def _taken(env: RouteEnv, laid: Drawn) -> tuple[Taken, ...]:
    """The rows a jog bend must not land on: trunk lane lines, laid runs and wire ends (R428)."""
    grid = env.options.wiring_grid
    lines = [
        (t.y + (lane_offset(k, grid) if env.fans[t.fan].lanes > 1 else 0), t.x0, t.x1)
        for t in env.trunks
        for k in range(t.lanes)
    ]
    runs = [s for w in laid.wires for s in pairwise(w.points)]
    ends = [(w.points[i][1], w.points[i][0], w.points[i][0]) for w in laid.wires for i in (0, -1)]
    return (*lines, *taken_rows(runs), *ends)


def _fixed_wires(env: RouteEnv) -> Drawn:
    """Lane wires, joins, nested jogs and trunks of one page."""
    out = lead_wires(env)
    for col in env.columns:
        out += lane_wires(env, col) + join_wires(env, col)
    nested = nest_jogs(env, out.jogs, _taken(env, out))
    out = Drawn(out.wires + nested.wires, (), out.findings + nested.findings, out.rises)
    for trunk in env.trunks:
        out += trunk_wires(env, trunk)
    return out


def _cells(extent: int, room: int | None, step: int, spare: int) -> int:
    """Grid cells along one axis: the content box `room` the caller passes, else extent and spare.

    The box is the bound, not the drawn extent (R424); layout-0334: what stands past it keeps
    the cells it needs.
    """
    if room is None:
        return extent // step + spare
    return max(room // step + 1, extent // step + 1)


def _mark_pins(env: RouteEnv, grid: Occupancy) -> None:
    """The blocked foreign port ends are ends no wire passes (R472): `env.blocked_ends`."""
    for net, points in env.blocked_ends.items():
        for point in points:
            grid.mark_end(net, point)


def _mark_fixed(env: RouteEnv, grid: Occupancy) -> None:
    """Every footprint and obstacle box, then the pins of no net."""
    for box in (*(p.footprint for p in env.placed.values()), *env.obstacles):
        grid.mark_box(box)
    _mark_pins(env, grid)


def _grid(env: RouteEnv, fixed: Sequence[Wire]) -> Occupancy:
    """A map that holds every footprint, wire and pin of the page, so none indexes off it."""
    step = env.options.wiring_grid
    xs = [p.footprint.x + p.footprint.w for p in env.placed.values()]
    ys = [p.footprint.y + p.footprint.h for p in env.placed.values()]
    pts = [pt for w in fixed for pt in w.points]
    xs += [x for x, _ in pts] + [b.x + b.w for b in env.obstacles]
    ys += [y for _, y in pts] + [b.y + b.h for b in env.obstacles]
    low = min(
        [p.footprint.x for p in env.placed.values()] + [p.footprint.y for p in env.placed.values()]
    )
    if low < 0:
        msg = f"page {env.page} has a footprint left of or above the origin ({low})"
        raise ValueError(msg)
    area = env.area
    grid = Occupancy(
        _cells(max(xs, default=0), None if area is None else area.w, step, env.options.spare_cells),
        _cells(max(ys, default=0), None if area is None else area.h, step, env.options.spare_cells),
        step,
    )
    _mark_fixed(env, grid)
    for w in fixed:
        grid.mark_wire(w.net, w.points)
    return grid


def _bbox(env: RouteEnv, link: CrossLink) -> int:
    pts = [pt for a in link.ends if (pt := pin_point(env, a.pin.sym, a.pin.pin)) is not None]
    return (max(p[0] for p in pts) - min(p[0] for p in pts)) + (
        max(p[1] for p in pts) - min(p[1] for p in pts)
    )


def _route_one(st: LinkState, link: CrossLink) -> bool:
    """Route one link; on failure its partial wires leave the map and a finding names it."""
    wires = tree(st.env, st.grid, link)
    if wires is None:
        st.grid.remove_net(link.net)
        st.routed.pop(link.net, None)
        ends = ", ".join(f"{a.pin.sym}.{a.pin.pin}" for a in link.ends)
        text = (
            f"net {link.net} on page {st.env.page} has no free path on the wiring grid "
            f"between {ends}, so no wire is drawn for it: move a symbol out of the way, or "
            "lower Options.crossing_penalty so it may cross"
        )
        st.findings.append(failed(st.env, link.net, text))
        first, second = (a.pin for a in link.ends[:2])
        st.failed.setdefault(link.net, Refused(link.net, (first, second)))
        return False
    st.routed[link.net] = wires
    return True


def _reroute(st: LinkState, fixed: Sequence[Wire], links: Sequence[CrossLink]) -> None:
    """One round: rip up the worst links by crossings and route each again."""
    wires = [*fixed, *(w for ws in st.routed.values() for w in ws)]
    by_net = crossings_by_net(wires, bundles(st.env.fans.values()))
    worst = sorted(
        (ln for ln in links if ln.net in st.routed),
        key=lambda ln: (-by_net.get(ln.net, 0), natural_key(ln.net)),
    )[:WORST]
    for link in worst:
        old = st.routed[link.net]
        st.grid.remove_net(link.net)
        mark_anchors(st.env, st.grid, link)
        if not _route_one(st, link):
            st.routed[link.net] = old
            del st.failed[link.net]
            st.findings.pop()
            for w in old:
                st.grid.mark_wire(w.net, w.points)


def _row_of(env: RouteEnv, y: int) -> int:
    return next((i for i, (top, bottom) in enumerate(env.bands) if top <= y <= bottom), -1)


def _row_wrapped(env: RouteEnv, linked: frozenset[str]) -> list[CrossLink]:
    """A fan with no trunk and no arrow whose attachments stand in different rows is a link."""
    trunked = {t.fan for t in env.trunks}
    out = []
    for fan in env.fans.values():
        net, ends = fan.nets[0], (*fan.drivers, *fan.legs)
        pts = [pin_point(env, a.pin.sym, a.pin.pin) for a in ends]
        if fan.lanes != 1 or fan.id in trunked or net in env.cut_nets or net in linked:
            continue
        if all(pts) and len({_row_of(env, p[1]) for p in pts if p}) > 1:
            out.append(CrossLink(net, ends))
    return out


def _links_here(env: RouteEnv) -> tuple[list[CrossLink], list[Finding]]:
    """Cross-links with an end on this page; a cut one still joins its ends here (R417)."""
    todo: list[CrossLink] = _row_wrapped(env, frozenset(ln.net for ln in env.cross_links))
    out: list[Finding] = []
    for link in env.cross_links:
        here = [a for a in link.ends if a.pin.sym in env.placed]
        if link.net in env.cut_nets and len(here) > 1:
            todo.append(CrossLink(link.net, tuple(here)))
        if not here or link.net in env.cut_nets:
            continue
        if len(here) == len(link.ends):
            todo.append(link)
        else:
            text = (
                f"net {link.net} has ends on page {env.page} and on another page but is not "
                "drawn as references, so no wire is drawn for it: cut it as references or "
                "place its ends on one page"
            )
            out.append(failed(env, link.net, text))
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


def _route_links(env: RouteEnv, fixed: Sequence[Wire]) -> LinkState:
    todo, refused = _links_here(env)
    st = LinkState(env, _grid(env, fixed))
    st.findings.extend(refused)
    st.failed.update({f.subject: Refused(f.subject) for f in refused if f.subject})
    todo.sort(key=lambda ln: (_bbox(env, ln), natural_key(ln.net)))
    st.bare = _bare_routes(env, todo)
    for link in todo:
        mark_anchors(env, st.grid, link)
    for link in todo:
        _route_one(st, link)
    for _ in range(env.options.reroute_rounds):
        _reroute(st, fixed, todo)
    return st


def _rise_wires(env: RouteEnv, fixed: Drawn) -> tuple[tuple[Wire, ...], tuple[Finding, ...]]:
    """Each rise by A* to its trunk cell; one that cannot be routed is a finding, never a wire."""
    if not fixed.rises:
        return (), ()
    grid = _grid(env, fixed.wires)
    wires: list[Wire] = []
    lost: list[Finding] = []
    for r in fixed.rises:
        wire = rise_wire(env, grid, r)
        if wire is not None:
            wires.append(wire)
            continue
        text = (
            f"net {r.net} on page {env.page} has no free path from {r.sym} to its trunk at "
            f"{r.target}, so no wire is drawn for it: move a symbol out of the way, or "
            "widen the gap beside the trunk"
        )
        lost.append(failed(env, r.net, text))
    return tuple(wires), tuple(lost)


def route_page(env: RouteEnv) -> tuple[PageRoutes, tuple[Refused, ...], tuple[Finding, ...]]:
    """One page's routes, the nets it gave up on, and its findings."""
    drawn = guard(env, _grid(env, ()), _fixed_wires(env))
    rises, lost = _rise_wires(env, drawn)
    fixed = Drawn(drawn.wires + rises, (), drawn.findings + lost)
    st = _route_links(env, fixed.wires)
    wires = fixed.wires + tuple(w for ws in st.routed.values() for w in ws)
    wanted = fixed.wires + tuple(w for ws in st.bare.values() for w in ws)
    page = PageRoutes(
        env.page, wires, demand(wanted, env.gaps), counts(wires, bundles(env.fans.values()))
    )
    nets = {f.subject: Refused(f.subject) for f in lost if f.subject} | st.failed
    return page, tuple(nets.values()), fixed.findings + tuple(st.findings)


def route_pages(
    placement: Placement,
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    obstacles: Sequence[Box] = (),
) -> Routes:
    """Stage 6: the wires of every placed page, with demand and counts.

    `obstacles` are boxes (marker boxes) no wire cell may enter; demand is read from each link
    routed on footprints and obstacles alone.
    """
    results = [route_page(env) for env in route_envs(placement, cut, problem, options, obstacles)]
    return Routes(
        tuple(r[0] for r in results),
        tuple(n for r in results for n in r[1]),
        tuple(f for r in results for f in r[2]),
    )
