"""Planted problems, CutResult edits and readers of Routes, for the stage 6 tests."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations, pairwise
from typing import TYPE_CHECKING

from options_fixtures import core_options

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

from fransys_layout.core import (
    Box,
    Bundle,
    Facts,
    Net,
    Options,
    PinRef,
    Placement,
    PlacementProblem,
)
from fransys_layout.core.outputs import PagePlacement, PageRoutes, PinXY, Placed, Routes, Wire
from fransys_layout.core.route import route_page
from fransys_layout.core.route_env import Drawn, RouteEnv, route_envs
from fransys_layout.core.values import Attach, Column, CrossLink, CutResult, End, Fan

from .conftest import MARKER
from .cut_fixtures import AREA, elem
from .cycle_fixtures import ring_problem
from .flow_builders import net, poles
from .pipeline_fixtures import cut_of, placed_from
from .place_fixtures import all_pins

XY = tuple[int, int]


def jog_stair(*, mirror: bool = False) -> PlacementProblem:
    """Three upper elements each wired down to a lower one; mirror reverses the net order."""
    order = (2, 1, 0) if mirror else (0, 1, 2)
    syms = [elem(f"u{k}", 16) for k in range(3)] + [elem(f"v{k}", 16) for k in range(3)]
    nets = [net(f"j{k}", f"u{k}.s", f"v{k}.n") for k in order]
    return PlacementProblem(AREA, tuple(syms), tuple(nets), facts=Facts())


def reversing_pair(perm: Sequence[int] = (2, 1, 0)) -> PlacementProblem:
    """Q1 feeds K1 pole for pole and K2 with net k on pole perm[k]; K1 and K2 feed M1."""
    syms = [poles(name) for name in ("Q1", "K1", "K2", "M1")]
    nets = [
        net(f"L{k + 1}", f"Q1.s{k}", f"K1.n{k}", f"K2.n{perm[k]}", bundle=Bundle("bL", k))
        for k in range(3)
    ]
    nets += [
        net(f"T{k + 1}", f"K1.s{k}", f"K2.s{k}", f"M1.n{k}", bundle=Bundle("bT", k))
        for k in range(3)
    ]
    return PlacementProblem(AREA, tuple(syms), tuple(nets), facts=Facts())


def with_crossed(
    cut: CutResult, fan_id: str, crossed: tuple[tuple[str, tuple[int, ...]], ...]
) -> CutResult:
    """The cut with Fan.crossed set on one fan; stage 1 never fills it (layout-0275)."""
    fans = tuple(replace(f, crossed=crossed) if f.id == fan_id else f for f in cut.flow.fans)
    return replace(cut, flow=replace(cut.flow, fans=fans))


def link_across_box() -> PlacementProblem:
    """The t01 ring: stage 1 splits it into one cross-link whose ends sit in three columns."""
    return ring_problem()


def two_links_one_gap() -> PlacementProblem:
    """Two t01 rings on one page (ids prefixed a and b): two cross-links that may share a gap."""
    rings = (("a", ring_problem()), ("b", ring_problem()))
    syms = tuple(replace(s, id=f"{k}{s.id}") for k, p in rings for s in p.symbols)
    nets = tuple(
        replace(n, id=f"{k}{n.id}", pins=tuple(replace(r, sym=f"{k}{r.sym}") for r in n.pins))
        for k, p in rings
        for n in p.nets
    )
    return PlacementProblem(AREA, syms, nets, facts=Facts())


def _wires(routes: Routes) -> list[Wire]:
    return [w for page in routes.pages for w in page.wires]


def segments(routes: Routes) -> list[tuple[XY, XY]]:
    """Every (a, b) pair of consecutive points of every wire, over all pages."""
    return [seg for w in _wires(routes) for seg in pairwise(w.points)]


def net_points(routes: Routes, net_id: str) -> tuple[tuple[XY, ...], ...]:
    """The polylines of one net, one tuple of points per wire."""
    return tuple(w.points for w in _wires(routes) if w.net == net_id)


def pin_reached(
    routes: Routes, placement: Placement, problem: PlacementProblem
) -> set[tuple[str, str]]:
    """Each (sym, pin) whose placed point is an end point of some wire of its own net.

    A bundle's wires carry the fan id `f:<bundle>`; a net of the bundle owns them too.
    """
    xy = all_pins(placement)
    reached: set[tuple[str, str]] = set()
    for n in problem.nets:
        owners = [n.id, *([f"f:{n.bundle.id}"] if n.bundle else [])]
        ends = {pts[e] for o in owners for pts in net_points(routes, o) for e in (0, -1)}
        reached |= {(r.sym, r.pin) for r in n.pins if xy.get((r.sym, r.pin)) in ends}
    return reached


def own_crossings(routes: Routes) -> int:
    """Points where a horizontal run strictly crosses a vertical one, whatever their nets."""
    runs = segments(routes)
    points = set()
    for a, b in (s for s in runs if s[0][1] == s[1][1]):
        x0, x1 = sorted((a[0], b[0]))
        for c, d in (s for s in runs if s[0][0] == s[1][0]):
            y0, y1 = sorted((c[1], d[1]))
            if x0 < c[0] < x1 and y0 < a[1] < y1:
                points.add((c[0], a[1]))
    return len(points)


def overlaps(routes: Routes) -> list[tuple[tuple[XY, XY], tuple[XY, XY]]]:
    """Pairs of collinear runs that share more than a point."""
    bad = []
    for (a, b), (c, d) in combinations(segments(routes), 2):
        axis = 0 if a[0] == b[0] == c[0] == d[0] else 1 if a[1] == b[1] == c[1] == d[1] else None
        if axis is None:
            continue
        other = 1 - axis
        lo = max(min(a[other], b[other]), min(c[other], d[other]))
        hi = min(max(a[other], b[other]), max(c[other], d[other]))
        if lo < hi:
            bad.append(((a, b), (c, d)))
    return bad


def inherent(xs: Sequence[int], perm: Sequence[int]) -> int:
    """Pairs of lanes whose order in x differs between where they leave and where they land."""
    return sum(
        (xs[a] - xs[b]) * (xs[perm[a]] - xs[perm[b]]) < 0
        for a, b in combinations(range(len(perm)), 2)
    )


def envs_of(
    prob: PlacementProblem, options: Options | None = None, cut: CutResult | None = None
) -> tuple[RouteEnv, ...]:
    """The stage 6 environments of a problem; a test may pass an edited cut (Fan.crossed)."""
    opts = options or core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    cut = cut or cut_of(prob, opts)
    return route_envs(placed_from(cut, prob, opts), cut, prob, opts)


BODY = {  # side the wire leaves -> the 8 by 8 footprint's corner offset from the pin
    "N": (-4, 0),
    "S": (-4, -8),
    "E": (-8, -4),
    "W": (0, -4),
}


def link_env(
    pins: Mapping[str, tuple[int, int, str]],
    links: Mapping[str, Sequence[str]],
    options: Options | None = None,
) -> RouteEnv:
    """A page of single-pin symbols and cross-links between them.

    `pins` maps a symbol id to its pin's (x, y, side the wire leaves); the 8 by 8 footprint
    lies behind the pin. `links` maps a net id to the symbols it joins.
    """
    placed = {}
    for sym, (x, y, side) in pins.items():
        dx, dy = BODY[side]
        box = Box(x + dx, y + dy, 8, 8)
        placed[sym] = Placed(sym, 1, x, y, "R0", box, box, (PinXY("p", x, y),))
    cross = tuple(
        CrossLink(n, tuple(Attach(None, 0, 0, PinRef(s, "p"), net="n") for s in ends))
        for n, ends in links.items()
    )
    return RouteEnv(
        1,
        placed,
        (),
        {},
        {},
        {},
        (),
        (),
        (),
        cross,
        frozenset(),
        options
        or core_options(
            marker=MARKER,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def row_wrap_env(options: Options | None = None) -> RouteEnv:
    """L1: a two-pin net x across two rows of one page, with no planned Ref and no trunk.

    Symbol `a` stands in row 0 (y 16 to 56) and `z` in row 1 (y 88 to 136), both with their wire
    leaving north; the fan has one driver and one leg, one in each row.
    """
    env = link_env({"a": (40, 40, "N"), "z": (104, 120, "N")}, {}, options)
    ends = tuple(Attach(None, 0, 0, PinRef(s, "p"), net="n") for s in ("a", "z"))
    fan = Fan("f:x", ("x",), ends[:1], ends[1:], None, 1, "S")
    return replace(
        env,
        net_of={PinRef("a", "p"): "x", PinRef("z", "p"): "x"},
        net_pins={"x": (PinRef("a", "p"), PinRef("z", "p"))},
        fans={"f:x": fan},
        bands=((16, 56), (88, 136)),
    )


def three_end_env(options: Options | None = None) -> RouteEnv:
    """A cross-link t with three ends in one row, the third off to the side of the first two."""
    pins = {"a": (40, 40, "S"), "b": (200, 40, "S"), "c": (120, 40, "S")}
    env = link_env(pins, {"t": ("a", "b", "c")}, options)
    return replace(env, bands=((16, 64),))


def env_view(env: RouteEnv, page: PageRoutes, net_id: str) -> tuple[Routes, Placement, Net]:
    """A hand-built env's routes and placement as the oracle reads them, and net `net_id` on it."""
    pins = tuple(PinRef(sym, "p") for sym in env.placed)
    placed = PagePlacement(
        env.page, tuple(env.placed.values()), env.gaps, env.trunks, (), env.bands
    )
    return Routes((page,)), Placement((placed,)), Net(net_id, pins)


def oracle_on(env: RouteEnv, net_id: str) -> bool:
    """Route a hand-built page and ask the oracle whether net `net_id` is drawn whole on it."""
    from .route_oracle import connected_or_referenced

    page = route_page(env)[0]
    routes, placement, net = env_view(env, page, net_id)
    return connected_or_referenced(routes, placement, (), net, env.page)


def open_end_env(
    orient: str = "R0", open_stub: int = 8, *, has_pin: bool = True
) -> tuple[RouteEnv, Column]:
    """Coil k2 of a card page with its foot an open end on `pin`; k2 is turned to `orient`."""
    from .place_fixtures import card_with_coils

    env = envs_of(
        card_with_coils(3),
        core_options(
            marker=MARKER,
            open_stub=open_stub,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )[0]
    col = env.columns[1]
    placed = replace(env.placed["k2"], orient=orient)
    env = replace(env, placed={**env.placed, "k2": placed})
    return env, replace(
        col, feet=(End("open", "dangling", PinRef("k2", "s")) if has_pin else End("open"),)
    )


def stub_of(drawn: Drawn) -> tuple[Wire, ...]:
    """The wires of the one-pin net dangling in a Drawn."""
    return tuple(w for w in drawn.wires if w.net == "dangling")


def by_bundle(routes: Routes, problem: PlacementProblem) -> Routes:
    """Routes with each bundle member's wires renamed to the bundle's fan id `f:<bundle>`.

    Stage 1 does not fill Fan.crossed (layout-0275), so a reversing plant is drawn plain and a
    pole's drop lands on another member's line: the plants check connection per bundle.
    """
    fan_of = {n.id: f"f:{n.bundle.id}" for n in problem.nets if n.bundle}
    pages = tuple(
        replace(pg, wires=tuple(replace(w, net=fan_of.get(w.net, w.net)) for w in pg.wires))
        for pg in routes.pages
    )
    return replace(routes, pages=pages)
