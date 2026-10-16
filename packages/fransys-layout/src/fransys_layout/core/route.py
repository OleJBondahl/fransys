"""Stage 6, route: route_pages(placement, cut, problem, options) -> Routes.

Per page: lane wires and joins, jogs nested by E6, trunks with drops, then cross-links by A*
(smallest bounding box first, `reroute_rounds` rip-ups of the three worst). Every refusal is a
`ROUTE_FAILED` finding naming the thing and the fix; no wire is drawn for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .keys import natural_key
from .outputs import PageRoutes, Routes, Wire
from .route_astar import GridMap, Leg, anchor, astar, simplify, tidy
from .route_counts import counts, demand
from .route_env import Drawn, failed, pin_point, route_envs
from .route_trunk import trunk_wires
from .route_wires import join_wires, lane_wires, nest_jogs

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .outputs import Placement
    from .route_env import RouteEnv
    from .values import XY, CrossLink, CutResult, Finding, Options, PlacementProblem

WORST = 3  # links ripped up and rerouted per round


@dataclass(slots=True)
class LinkState:
    """The links of one page while they are routed: wires per net, nets given up, findings."""

    env: RouteEnv
    grid: GridMap
    routed: dict[str, tuple[Wire, ...]] = field(default_factory=dict)
    failed: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


def _fixed_wires(env: RouteEnv) -> Drawn:
    """Lane wires, joins, nested jogs and trunks of one page."""
    out = Drawn()
    for col in env.columns:
        out += lane_wires(env, col) + join_wires(env, col)
    nested = nest_jogs(env, out.jogs)
    out = Drawn(out.wires + nested.wires, (), out.findings + nested.findings)
    for trunk in env.trunks:
        out += trunk_wires(env, trunk)
    return out


def _grid(env: RouteEnv, fixed: Sequence[Wire]) -> GridMap:
    """A map that holds every footprint, wire and pin of the page, so none indexes off it."""
    step = env.options.wiring_grid
    xs = [p.footprint.x + p.footprint.w for p in env.placed.values()]
    ys = [p.footprint.y + p.footprint.h for p in env.placed.values()]
    pts = [pt for w in fixed for pt in w.points]
    xs += [x for x, _ in pts]
    ys += [y for _, y in pts]
    low = min(
        [p.footprint.x for p in env.placed.values()] + [p.footprint.y for p in env.placed.values()]
    )
    if low < 0:
        msg = f"page {env.page} has a footprint left of or above the origin ({low})"
        raise ValueError(msg)
    grid = GridMap(max(xs, default=0) // step + 3, max(ys, default=0) // step + 3, step)
    for p in env.placed.values():
        grid.block_box(p.footprint)
    for w in fixed:
        grid.add_wire(w.net, w.points)
    return grid


def _ends(env: RouteEnv, link: CrossLink) -> list[XY]:
    return [pt for a in link.ends if (pt := pin_point(env, a.pin.sym, a.pin.pin)) is not None]


def _bbox(env: RouteEnv, link: CrossLink) -> int:
    pts = _ends(env, link)
    return (max(p[0] for p in pts) - min(p[0] for p in pts)) + (
        max(p[1] for p in pts) - min(p[1] for p in pts)
    )


def _legs(env: RouteEnv, link: CrossLink) -> list[tuple[XY, ...]]:
    """Each end's anchor: its pin, then the grid point outside its footprint where A* starts."""
    step = env.options.wiring_grid
    out: list[tuple[XY, ...]] = []
    for a in link.ends:
        pin = pin_point(env, a.pin.sym, a.pin.pin)
        if pin is not None:
            out.append(anchor(pin, env.placed[a.pin.sym].footprint, step))
    return out


def _cell(p: XY, step: int) -> XY:
    return (p[0] // step, p[1] // step)


def _tree(st: LinkState, link: CrossLink) -> tuple[Wire, ...] | None:
    """A spanning tree of the net's ends, each to the nearest routed point; None on a dead end."""
    env, step = st.env, st.env.options.wiring_grid
    anchors = _legs(env, link)
    done: list[XY] = [anchors[0][-1]]
    out: list[Wire] = []
    for i, goal in enumerate(anchors[1:], 1):
        start = min(done, key=lambda p: (abs(p[0] - goal[-1][0]) + abs(p[1] - goal[-1][1]), p))
        cells = (_cell(start, step), _cell(goal[-1], step))
        path = astar(st.grid, Leg(link.net, *cells, frozenset(cells)), env.options)
        if path is None:
            return None
        pts = simplify(path, step)
        st.grid.add_wire(link.net, pts)
        head = anchors[0][:-1] if i == 1 else ()
        out.append(Wire(link.net, env.page, tidy([*head, *pts, *reversed(goal[:-1])]), "routed"))
        done.extend(pts)
    return tuple(out)


def _route_one(st: LinkState, link: CrossLink) -> bool:
    """Route one link; on failure its partial wires leave the map and a finding names it."""
    wires = _tree(st, link)
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
        if link.net not in st.failed:
            st.failed.append(link.net)
        return False
    st.routed[link.net] = wires
    return True


def _crossings_of(st: LinkState, fixed: Sequence[Wire], net: str) -> int:
    others = [*fixed, *(w for n, ws in st.routed.items() if n != net for w in ws)]
    return counts([*st.routed.get(net, ()), *others]).crossings - counts(others).crossings


def _reroute(st: LinkState, fixed: Sequence[Wire], links: Sequence[CrossLink]) -> None:
    """One round: rip up the worst links by crossings and route each again."""
    worst = sorted(
        (ln for ln in links if ln.net in st.routed),
        key=lambda ln: (-_crossings_of(st, fixed, ln.net), natural_key(ln.net)),
    )[:WORST]
    for link in worst:
        old = st.routed[link.net]
        st.grid.remove_net(link.net)
        if not _route_one(st, link):
            st.routed[link.net] = old
            st.failed.remove(link.net)
            st.findings.pop()
            for w in old:
                st.grid.add_wire(w.net, w.points)


def _links_here(env: RouteEnv) -> tuple[list[CrossLink], list[Finding]]:
    """Cross-links with an end on this page; one cut into references is drawn as references."""
    todo: list[CrossLink] = []
    out: list[Finding] = []
    for link in env.cross_links:
        here = [a for a in link.ends if a.pin.sym in env.placed]
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


def _route_links(env: RouteEnv, fixed: Sequence[Wire]) -> LinkState:
    todo, refused = _links_here(env)
    st = LinkState(env, _grid(env, fixed))
    st.findings.extend(refused)
    st.failed.extend(f.subject for f in refused if f.subject)
    todo.sort(key=lambda ln: (_bbox(env, ln), natural_key(ln.net)))
    for link in todo:
        _route_one(st, link)
    for _ in range(env.options.reroute_rounds):
        _reroute(st, fixed, todo)
    return st


def route_page(env: RouteEnv) -> tuple[PageRoutes, tuple[str, ...], tuple[Finding, ...]]:
    """One page's routes, the nets it gave up on, and its findings."""
    fixed = _fixed_wires(env)
    st = _route_links(env, fixed.wires)
    wires = fixed.wires + tuple(w for ws in st.routed.values() for w in ws)
    page = PageRoutes(env.page, wires, demand(wires, env.gaps), counts(wires))
    return page, tuple(st.failed), fixed.findings + tuple(st.findings)


def route_pages(
    placement: Placement, cut: CutResult, problem: PlacementProblem, options: Options
) -> Routes:
    """Stage 6: the wires of every placed page, with demand and counts."""
    results = [route_page(env) for env in route_envs(placement, cut, problem, options)]
    return Routes(
        tuple(r[0] for r in results),
        tuple(n for r in results for n in r[1]),
        tuple(f for r in results for f in r[2]),
    )
