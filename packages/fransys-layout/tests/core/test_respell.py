"""Every stage reads no id text beyond the natural key: respelling every id (a map that keeps the
natural order), or reversing the unordered input tuples, changes nothing in a stage's result but
its spelling. One section per stage, 2 (blocks) to 8b (labels), in stage order."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from options_fixtures import core_options

from fransys_layout.core import Facts, Hints, PinRef, PlacementProblem, Size, natural_key, order_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.order import order_columns
from fransys_layout.core.place import place_pages
from fransys_layout.core.route import route_page, route_pages
from fransys_layout.core.text_markers import placed_marks
from fransys_layout.core.widen import Round, route_round, widen

from . import align_fixtures as fx
from . import pipeline_fixtures
from .blocks_fixtures import box_case, build, fan, loose
from .conftest import MARKER
from .cut_fixtures import AREA, box_sym, chain, elem, free, net
from .cut_respell import (
    back_by_parts,
    back_of,
    canon,
    canon_placement,
    id_sets,
    make_maps,
    respell_blocks,
    respell_cut,
    respell_flow,
    respell_problem,
)
from .order_fixtures import OPTIONS as ORDER_OPTIONS
from .order_fixtures import block, box_column, comb, flow
from .pipeline_fixtures import blocks_of, cut_of, flow_of, placed_from, routed_from
from .place_fixtures import bundle_fan, two_edge_card
from .route_fixtures import jog_stair, link_env
from .test_widen import PLAIN, three_columns
from .test_widen_pass import run
from .text_fixtures import PLANTS

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from fransys_layout.core import AnnexBox, Placement
    from fransys_layout.core.flow_values import Attach, Block, Column, CutResult, End, Fan, FlowGraph, Lane
    from fransys_layout.core.outputs import Marker, Routes
    from fransys_layout.core.sym_values import Sym

OPTIONS = core_options(marker=MARKER)


# --- stage: cut
SPELLINGS = ("{}", "{:04d}")  # each keeps the natural order of the ranks, spells it anew


def two_page_fan() -> PlacementProblem:
    """Two fans with free-sided hubs, each cut onto three pages: copies named feed2, feed10."""
    syms, nets = [], []
    for tag in ("2", "10"):
        syms += [free(f"t{tag}"), *(elem(f"a{tag}x{i}", 700, 400, f"G{tag}") for i in (1, 2, 3))]
        legs = (f"a{tag}x{i}.n" for i in (1, 2, 3))
        nets.append(net(f"feed{tag}", f"t{tag}.e", *legs))
    hints = Hints(group_order=("G2", "G10"))
    return PlacementProblem(AREA, tuple(syms), tuple(nets), hints=hints, facts=Facts(far_ends=()))


def card_that_wraps() -> PlacementProblem:
    """A 16-pin card with free columns either side: the free column on the right wraps."""
    syms = [box_sym(16), *(elem(f"k{i:02d}", 64, 32, "CH") for i in range(1, 17))]
    for name, w, group in (("f", 58, "FR"), ("g", 64, "GR")):
        syms += [elem(f"{name}{n}", w, 32, group) for n in (0, 1)]
    nets = [net(f"n{i:02d}", f"A1.p{i}", f"k{i:02d}.n") for i in range(1, 17)]
    nets += [net("fr", "f0.s", "f1.n"), net("gr", "g0.s", "g1.n")]
    hints = Hints(group_order=("FR", "PLC", "CH", "GR"))
    return PlacementProblem(AREA, tuple(syms), tuple(nets), hints=hints, facts=Facts(far_ends=()))


def tall_column() -> PlacementProblem:
    """Twelve cells of 96 G in one column: the cut folds it into c#a and c#b over one tag."""
    ids = [f"k{i:02d}" for i in range(12)]
    syms = tuple(elem(i, 40, 96) for i in ids)
    return PlacementProblem(AREA, syms, tuple(chain(ids)), facts=Facts(far_ends=()))


CASES = {
    "two_page_fan": two_page_fan,
    "card_that_wraps": card_that_wraps,
    "tall_column": tall_column,
}


def stages(prob: PlacementProblem):
    flow = flow_of(prob, OPTIONS)
    return order_blocks(blocks_of(prob, OPTIONS), flow, OPTIONS), flow


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("form", SPELLINGS)
def test_the_cut_does_not_depend_on_how_ids_are_spelled(case: str, form: str) -> None:
    prob = CASES[case]()
    lists, flow = stages(prob)
    want = canon(cut_pages(lists, flow, prob, OPTIONS), back_of({}))
    assert want[1] or len(want[0]) > 1 or len(want[0][0][1]) > 1  # something is cut: not vacuous
    maps = make_maps(id_sets(prob, flow, lists), form)
    got = cut_pages(respell_blocks(lists, maps), respell_flow(flow, maps), respell_problem(prob, maps), OPTIONS)
    assert canon(got, back_of(maps)) == want


@pytest.mark.parametrize("case", CASES)
def test_the_cut_does_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    prob = CASES[case]()
    lists, flow = stages(prob)
    want = canon(cut_pages(lists, flow, prob, OPTIONS), back_of({}))
    flipped = replace(flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1])
    reversed_prob = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    got = canon(cut_pages(lists, flipped, reversed_prob, OPTIONS), back_of({}))
    assert got[0] == want[0]
    assert sorted(got[1], key=repr) == sorted(want[1], key=repr)
    assert got[2] == want[2]


# --- stage: order
# (column id format, symbol id format): both keep the natural order of the ids, each spells it anew
SPELLINGS_order = (("C{}", "=Y{}"), ("Q{:04d}", "=Z{:04d}"))


def card() -> tuple[Block, FlowGraph]:
    """Twelve columns on box pins 1 to 12; the box lists pins 3, 1, 2 and the rest tie."""
    cols = [f"c{i:02d}" for i in range(1, 13)]
    edges = (("3", "N"), ("1", "N"), ("2", "N"))
    columns = [box_column(c, str(i)) for i, c in enumerate(cols, 1)]
    return block(cols, kind="card", pin_edges=edges), flow(columns=columns)


CASES_order = {"twelve": lambda: comb(12), "thirteen": lambda: comb(13), "card": card}


def attaches(fl: FlowGraph) -> list[Attach]:
    found = [a for f in fl.fans for a in (*f.drivers, *f.legs)]
    return found + [a for x in fl.cross_links for a in x.ends]


def spell_maps(fl: FlowGraph, blk: Block, fmt: tuple[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Column and symbol id maps: rank by `natural_key`, spell_order the rank anew."""
    cols = {*blk.columns, *(c.id for c in fl.columns)}
    syms = {a.pin.sym for a in attaches(fl)}
    syms |= {e.pin.sym for c in fl.columns for e in (*c.heads, *c.feet) if e.pin}

    def spell_order(ids: set[str], form: str) -> dict[str, str]:
        ranked = sorted(ids, key=natural_key)
        return {i: form.format(n) for n, i in enumerate(ranked, 1)}

    return spell_order(cols, fmt[0]), spell_order(syms, fmt[1])


def respell_order(fl: FlowGraph, blk: Block, cm: dict[str, str], sm: dict[str, str]) -> tuple[Block, FlowGraph]:
    def attach(a: Attach) -> Attach:
        return replace(a, column=cm[a.column] if a.column else None, pin=replace(a.pin, sym=sm[a.pin.sym]))

    def end(e: End) -> End:
        return replace(e, pin=replace(e.pin, sym=sm[e.pin.sym])) if e.pin else e

    fans = tuple(replace(f, drivers=tuple(map(attach, f.drivers)), legs=tuple(map(attach, f.legs))) for f in fl.fans)
    links = tuple(replace(x, ends=tuple(map(attach, x.ends))) for x in fl.cross_links)
    cols = tuple(replace(c, id=cm[c.id], heads=tuple(map(end, c.heads)), feet=tuple(map(end, c.feet))) for c in fl.columns)
    return (
        replace(blk, columns=tuple(cm[c] for c in blk.columns)),
        replace(fl, fans=fans, cross_links=links, columns=cols),
    )


def result_order(blk: Block, fl: FlowGraph) -> tuple[str, ...]:
    return order_columns(blk, fl, ORDER_OPTIONS).columns


@pytest.mark.parametrize("case", CASES_order)
def test_order_does_not_depend_on_how_ids_are_spelled(case: str) -> None:
    blk, fl = CASES_order[case]()
    want = result_order(blk, fl)
    assert list(want) != sorted(blk.columns, key=natural_key)  # the order moved: not vacuous
    for fmt in SPELLINGS_order:
        cm, sm = spell_maps(fl, blk, fmt)
        back = {new: old for old, new in cm.items()}
        got = result_order(*respell_order(fl, blk, cm, sm))
        assert tuple(back[c] for c in got) == want


@pytest.mark.parametrize("case", CASES_order)
def test_order_does_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    blk, fl = CASES_order[case]()
    flipped = replace(
        fl,
        fans=fl.fans[::-1],
        cross_links=fl.cross_links[::-1],
        columns=fl.columns[::-1],
    )
    assert result_order(replace(blk, columns=blk.columns[::-1]), flipped) == result_order(blk, fl)


# --- stage: blocks

# (column, symbol, fan, group) formats: each keeps the natural order of the ids and spells it anew
SPELLINGS_world = (("C{}", "=Y{}", "F{}", "G{}"), ("Q{:04d}", "=Z{:04d}", "R{:04d}", "H{:04d}"))


@dataclass(frozen=True)
class World:
    syms: tuple[Sym, ...]
    cols: tuple[Column, ...]
    fans: tuple[Fan, ...]
    hints: Hints


def card_case() -> World:
    """A box with twelve columns on its pins."""
    syms, cols = box_case(12, 64)
    return World(tuple(syms), tuple(cols), (), Hints(group_order=("PLC", "CH")))


def fan_case() -> World:
    """A fan of three columns of group A beside a column of group B."""
    syms, cols = loose("A", "A", "A", "B")
    hints = Hints(group_order=("A", "B"))
    return World(tuple(syms), tuple(cols), (fan("f1", "c1", "c2", "c3"),), hints)


def groups_case() -> World:
    """Twelve free columns in two groups, a pair hint: c2 sorts before c10."""
    syms, cols = loose(*["A"] * 10, "B", "B")
    hints = Hints(group_order=("A", "B"), order_pairs=(("s12", "s1"),))
    return World(tuple(syms), tuple(cols), (), hints)


CASES_world: dict[str, Callable[[], World]] = {
    "card": card_case,
    "fan": fan_case,
    "groups": groups_case,
}


def spell_world(ids: Iterable[str], form: str) -> dict[str, str]:
    """Rank by `natural_key`, spell_world the rank anew."""
    return {i: form.format(n) for n, i in enumerate(sorted(set(ids), key=natural_key), 1)}


def maps(w: World, fmt: tuple[str, str, str, str]) -> dict[str, str]:
    """One map over column, symbol, fan and group ids (they never collide)."""
    out = spell_world((c.id for c in w.cols), fmt[0])
    out |= spell_world((s.id for s in w.syms), fmt[1])
    out |= spell_world((f.id for f in w.fans), fmt[2])
    out |= spell_world((s.group for s in w.syms if s.group), fmt[3])
    return out


def respell_world(w: World, m: dict[str, str]) -> World:
    def pin(p: PinRef) -> PinRef:
        return replace(p, sym=m.get(p.sym, p.sym))

    def end(e: End) -> End:
        return replace(e, pin=pin(e.pin)) if e.pin else e

    def attach(a: Attach) -> Attach:
        return replace(a, column=m[a.column] if a.column else None, pin=pin(a.pin))

    def lane(ln: Lane) -> Lane:
        return replace(ln, cells=tuple(replace(c, sym=m[c.sym]) for c in ln.cells))

    syms = tuple(replace(s, id=m[s.id], group=m[s.group] if s.group else None) for s in w.syms)
    cols = tuple(
        replace(
            c,
            id=m[c.id],
            lanes=tuple(map(lane, c.lanes)),
            heads=tuple(map(end, c.heads)),
            feet=tuple(map(end, c.feet)),
        )
        for c in w.cols
    )
    fans = tuple(replace(f, id=m[f.id], drivers=tuple(map(attach, f.drivers)), legs=tuple(map(attach, f.legs))) for f in w.fans)
    h = w.hints
    hints = Hints(
        group_order=tuple(m[g] for g in h.group_order),
        order_pairs=tuple((m[a], m[b]) for a, b in h.order_pairs),
    )
    return World(syms, cols, fans, hints)


def reverse(w: World) -> World:
    """Every input tuple reversed but the group order, which is the meaning of the hint."""
    h = w.hints
    hints = replace(
        h,
        order_pairs=h.order_pairs[::-1],
    )
    fans = tuple(replace(f, legs=f.legs[::-1], drivers=f.drivers[::-1]) for f in w.fans[::-1])
    return World(w.syms[::-1], w.cols[::-1], fans, hints)


class Row(NamedTuple):
    """A block without its opaque id."""

    kind: str
    unit: str
    group: str | None
    anchor: str | None
    cols: tuple[str, ...]
    fan: str | None
    sizes: tuple[int, int, bool, bool, bool]
    pin_edges: tuple[tuple[str, str], ...]
    fixed: bool


def summary(b: Block) -> Row:
    sizes = (b.width_est, b.height_est, b.short, b.keep_whole, b.forced_break_before)
    return Row(b.kind, b.unit, b.group, b.anchor, b.columns, b.fan, sizes, b.pin_edges, b.fixed_order)


def result_world(w: World) -> list[tuple[str, list[Row], list[str]]]:
    lists = build(w.syms, w.cols, w.fans, w.hints)
    return [(bl.unit, [summary(b) for b in bl.blocks], [f.code for f in bl.findings]) for bl in lists]


def through(want: list[tuple[str, list[Row], list[str]]], m: dict[str, str]) -> list[tuple[str, list[Row], list[str]]]:
    """The original's listing with its group, anchor, column and fan ids sent through the map."""

    def one(x: str | None) -> str | None:
        return m[x] if x else None

    def row(r: Row) -> Row:
        cols = tuple(m[c] for c in r.cols)
        return r._replace(group=one(r.group), anchor=one(r.anchor), cols=cols, fan=one(r.fan))

    return [(unit, [row(r) for r in rows], codes) for unit, rows, codes in want]


@pytest.mark.parametrize("case", CASES_world)
def test_blocks_do_not_depend_on_how_ids_are_spelled(case: str) -> None:
    world = CASES_world[case]()
    want = result_world(world)
    for fmt in SPELLINGS_world:
        m = maps(world, fmt)
        assert result_world(respell_world(world, m)) == through(want, m)


@pytest.mark.parametrize("case", CASES_world)
def test_blocks_do_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    world = CASES_world[case]()
    assert result_world(reverse(world)) == result_world(world)


# --- stage: align

ALIGN_OPTIONS = core_options()
CASES_align: dict[str, Callable[[], PlacementProblem]] = {
    "band": fx.two_band_columns,
    "mate": fx.mate_columns,
}


def _mates(prob: PlacementProblem, maps: dict[str, str]) -> Facts:
    return Facts(
        mates=tuple((PinRef(maps[a.sym], a.pin), PinRef(maps[b.sym], b.pin)) for a, b in prob.facts.mates),
        far_ends=(),
    )


@pytest.mark.parametrize("case", CASES_align)
@pytest.mark.parametrize("form", SPELLINGS)
def test_banded_placement_does_not_depend_on_how_ids_are_spelled(case: str, form: str) -> None:
    prob = CASES_align[case]()
    cut = cut_of(prob, ALIGN_OPTIONS)
    want = canon_placement(place_pages(cut, prob, ALIGN_OPTIONS), back_of({}))
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    spelled = replace(respell_problem(prob, maps), facts=_mates(prob, maps))
    got = place_pages(respell_cut(cut, maps), spelled, ALIGN_OPTIONS)
    assert canon_placement(got, back_of(maps)) == want
    assert any(p.placed for p in got.pages)


@pytest.mark.parametrize("case", CASES_align)
def test_banded_placement_does_not_depend_on_the_order_of_the_input(case: str) -> None:
    prob = CASES_align[case]()
    want = canon_placement(place_pages(cut_of(prob, ALIGN_OPTIONS), prob, ALIGN_OPTIONS), back_of({}))
    mates = tuple((b, a) for a, b in reversed(prob.facts.mates))
    flipped = replace(
        prob,
        symbols=tuple(reversed(prob.symbols)),
        nets=tuple(reversed(prob.nets)),
        facts=Facts(mates=mates, far_ends=()),
    )
    got = place_pages(cut_of(flipped, ALIGN_OPTIONS), flipped, ALIGN_OPTIONS)
    assert canon_placement(got, back_of({})) == want


# --- stage: place


def _wide_trunk(pl: Placement) -> bool:
    return any(t.lanes > 1 for p in pl.pages for t in p.trunks)


def _two_edges(pl: Placement) -> bool:
    """The card's pins stand on its top edge and on its bottom edge."""
    box = next(s for p in pl.pages for s in p.placed if s.sym == "A1")
    ys = {q.y for q in box.pin_xy}
    return box.body.y in ys and box.body.y + box.body.h in ys


def _two_rows(pl: Placement) -> bool:
    return any(len(p.rows) >= 2 for p in pl.pages)


def _two_pages(pl: Placement) -> bool:
    return len(pl.pages) >= 2


# each case: its builder and the feature that makes it non-vacuous
CASES_place: dict[str, tuple[Callable[[], PlacementProblem], Callable[[Placement], bool]]] = {
    "two_edge_card": (lambda: two_edge_card(16, 96), _two_edges),
    "card_that_wraps": (card_that_wraps, _two_rows),
    "two_page_fan": (two_page_fan, _two_pages),
    "bundle_fan": (bundle_fan, _wide_trunk),
}


def _checked_place(case: str) -> tuple[PlacementProblem, tuple[Any, ...]]:
    build, feature = CASES_place[case]
    prob = build()
    cut = cut_of(prob, OPTIONS)
    pl = place_pages(cut, prob, OPTIONS)
    assert sum(len(p.placed) for p in pl.pages) >= 3
    assert feature(pl), case
    return prob, (cut, canon_placement(pl, back_of({})))


@pytest.mark.parametrize("case", CASES_place)
@pytest.mark.parametrize("form", SPELLINGS)
def test_placement_does_not_depend_on_how_ids_are_spelled(case: str, form: str) -> None:
    prob, (cut, want) = _checked_place(case)
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    got = place_pages(respell_cut(cut, maps), respell_problem(prob, maps), OPTIONS)
    assert canon_placement(got, back_of(maps)) == want


@pytest.mark.parametrize("case", CASES_place)
def test_placement_does_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    prob, (cut, want) = _checked_place(case)
    flow = cut.flow
    flipped = replace(flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1])
    reversed_prob = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    got = place_pages(replace(cut, flow=flipped), reversed_prob, OPTIONS)
    assert canon_placement(got, back_of({})) == want


# --- stage: route

STEP = OPTIONS.wiring_grid


class Case(NamedTuple):
    """A builder, an edit of its cut, the symbols moved after placement, and its feature."""

    build: Callable[[], PlacementProblem]
    edit: Callable[[CutResult], CutResult]
    moved: tuple[tuple[str, int, int], ...]
    feature: Callable[[Routes], bool]


def _jogs(routes: Routes) -> bool:
    return sum(len(w.points) == 4 for p in routes.pages for w in p.wires if w.kind == "straight") >= 3


def _links(routes: Routes) -> bool:
    return any(w.kind == "routed" for p in routes.pages for w in p.wires)


def _same(cut: CutResult) -> CutResult:
    return cut


def _ring() -> PlacementProblem:
    from .route_fixtures import link_across_box

    return link_across_box()


CASES_route: dict[str, Case] = {
    "two_edge_card": Case(lambda: two_edge_card(16, 96), _same, (), lambda r: len(r.pages) >= 1),
    "two_rows": Case(card_that_wraps, _same, (), lambda r: len(r.pages[0].wires) > 3),
    "jog_stair": Case(jog_stair, _same, tuple((f"v{k}", 90, 40) for k in range(3)), _jogs),
    "cross_link_ring": Case(_ring, _same, (), _links),
}


def moved(pl: Placement, shifts: dict[str, tuple[int, int]]) -> Placement:
    """The placement with some symbols moved (body, footprint and pins), as a router input."""

    def shift(p: Any) -> Any:
        dx, dy = shifts.get(p.sym, (0, 0))
        return replace(
            p,
            x=p.x + dx,
            y=p.y + dy,
            body=replace(p.body, x=p.body.x + dx, y=p.body.y + dy),
            footprint=replace(p.footprint, x=p.footprint.x + dx, y=p.footprint.y + dy),
            pin_xy=tuple(replace(q, x=q.x + dx, y=q.y + dy) for q in p.pin_xy),
        )

    pages = tuple(replace(pg, placed=tuple(shift(p) for p in pg.placed)) for pg in pl.pages)
    return replace(pl, pages=pages)


def canon_routes(routes: Routes, back: Callable[[str | None], str | None]) -> tuple[Any, ...]:
    """The routes as plain tuples with every id mapped back; wires sorted, no finding text."""
    pages = tuple(
        (
            p.page,
            tuple(sorted((back(w.net), w.points, w.kind, w.lane) for w in p.wires)),
            tuple((d.tracks) for d in p.demand),
            p.counts,
        )
        for p in routes.pages
    )
    finds = tuple(sorted((f.code, f.page, back(f.subject)) for f in routes.findings))
    return pages, tuple(sorted(back(r.net) or "" for r in routes.failed)), finds


def routed(case: Case, cut: CutResult, prob: PlacementProblem, ids: dict[str, str]) -> Routes:
    """Stages 5 and 6 on a cut, with the case's symbols moved by their (possibly respelled) ids."""
    shifts = {ids.get(sym, sym): (dx, dy) for sym, dx, dy in case.moved}
    return route_pages(moved(place_pages(cut, prob, OPTIONS), shifts), cut, prob, OPTIONS)


def _checked_route(name: str) -> tuple[Case, PlacementProblem, CutResult, tuple[Any, ...]]:
    case = CASES_route[name]
    prob = case.build()
    cut = case.edit(cut_of(prob, OPTIONS))
    routes = routed(case, cut, prob, {})
    assert case.feature(routes), name
    assert routes.failed == ()
    return case, prob, cut, canon_routes(routes, back_of({}))


@pytest.mark.parametrize("name", CASES_route)
@pytest.mark.parametrize("form", SPELLINGS)
def test_routes_do_not_depend_on_how_ids_are_spelled(name: str, form: str) -> None:
    case, prob, cut, want = _checked_route(name)
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    got = routed(case, respell_cut(cut, maps), respell_problem(prob, maps), maps)
    assert canon_routes(got, back_of(maps)) == want


@pytest.mark.parametrize("name", CASES_route)
def test_routes_do_not_depend_on_the_order_of_the_input_tuples(name: str) -> None:
    case, prob, cut, want = _checked_route(name)
    flow = cut.flow
    flipped = replace(flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1])
    reversed_prob = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    got = routed(case, replace(cut, flow=flipped), reversed_prob, {})
    assert canon_routes(got, back_of({})) == want


def crossed_pair(first: str, second: str) -> dict[str, tuple[Any, ...]]:
    """Two cross-links of equal bounding box, an X: the one routed first shapes the other."""
    pins = {
        "p0": (40, 40, "E"),
        "p1": (200, 200, "W"),
        "q0": (40, 200, "E"),
        "q1": (200, 40, "W"),
    }
    opts = replace(OPTIONS, crossing_penalty=40, reroute_rounds=0)
    env = link_env(pins, {first: ("p0", "p1"), second: ("q0", "q1")}, opts)
    page = route_page(env)[0]
    return {w.net: w.points for w in page.wires}


def test_links_of_equal_size_are_routed_in_natural_order_not_string_order() -> None:
    """n9 and n10 tie on size: natural order puts n9 first, as n1 and n2 do (string order, n10)."""
    spelled = crossed_pair("n9", "n10")
    plain = crossed_pair("n1", "n2")
    back = {"n9": "n1", "n10": "n2"}
    assert {back[n]: pts for n, pts in spelled.items()} == plain


# --- stage: text_markers


def _ranked(name: str) -> PlacementProblem:
    """The plant with every symbol ranked, as el hands it (SYMBOL-TIE): the rank, never the id text, orders ends."""
    prob = PLANTS[name]()
    return replace(prob, symbols=tuple(replace(sym, rank=i) for i, sym in enumerate(prob.symbols)))


def _canon_markers(markers: tuple[Marker, ...], back: Callable[[str | None], str | None]) -> list[Any]:
    return [(back(m.net), m.kind, m.page, m.cell, m.x, m.y, m.end and (back(m.end.sym), m.end.pin)) for m in markers]


@pytest.mark.parametrize("name", PLANTS)
@pytest.mark.parametrize("form", SPELLINGS)
def test_markers_do_not_depend_on_how_ids_are_spelled(name: str, form: str) -> None:
    prob = _ranked(name)
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want = _canon_markers(placed_marks(cut, place_pages(cut, prob, OPTIONS), prob, OPTIONS, {})[0], back_of({}))
    assert want
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    cut2, prob2 = respell_cut(cut, maps), respell_problem(prob, maps)
    got = placed_marks(cut2, place_pages(cut2, prob2, OPTIONS), prob2, OPTIONS, {})[0]
    assert _canon_markers(got, back_of(maps)) == want


@pytest.mark.parametrize("name", PLANTS)
def test_markers_do_not_depend_on_the_order_of_the_input_tuples(name: str) -> None:
    prob = _ranked(name)
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want = _canon_markers(placed_marks(cut, place_pages(cut, prob, OPTIONS), prob, OPTIONS, {})[0], back_of({}))
    flow = cut.flow
    flipped = replace(flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1])
    prob2 = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    cut2 = replace(cut, flow=flipped)
    got = placed_marks(cut2, place_pages(cut2, prob2, OPTIONS), prob2, OPTIONS, {})[0]
    assert _canon_markers(got, back_of({})) == want


# --- stage: labels


def _canon_labels(labels: tuple[AnnexBox, ...], back: Callable[[str | None], str | None]) -> list[Any]:
    # Respelling can change the order of owners within a page, so the labels compare as sorted
    # (page, canonical id, box, spot) rows; the order of the stage's own output is not the claim.
    return sorted((lab.page, back(lab.owner), lab.box, lab.spot) for lab in labels)


@pytest.mark.parametrize("name", PLANTS)
@pytest.mark.parametrize("form", SPELLINGS)
def test_labels_do_not_depend_on_how_ids_are_spelled(name: str, form: str) -> None:
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want, _ = pipeline_fixtures.labelled_of(prob, OPTIONS)
    assert want
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    cut2, prob2 = respell_cut(cut, maps), respell_problem(prob, maps)
    placement = place_pages(cut2, prob2, OPTIONS)
    labelled = pipeline_fixtures.with_annexes(prob2, OPTIONS)
    got = route_round(cut2, placement, labelled, OPTIONS).routes.labels
    assert got
    assert _canon_labels(got, back_of(maps)) == _canon_labels(want, back_of({}))


@pytest.mark.parametrize("name", PLANTS)
def test_labels_do_not_depend_on_the_order_of_the_input_tuples(name: str) -> None:
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want, _ = pipeline_fixtures.labelled_of(prob, OPTIONS)
    flow = cut.flow
    flipped = replace(flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1])
    prob2 = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    cut2 = replace(cut, flow=flipped)
    placement = place_pages(cut2, prob2, OPTIONS)
    # The annexes are the caller's, in the caller's order (R345: the core sorts nothing); the
    # symbol, net and flow tuples it is handed in reverse change no box.
    labelled = replace(prob2, annexes=pipeline_fixtures.with_annexes(prob, OPTIONS).annexes)
    got = route_round(cut2, placement, labelled, OPTIONS).routes.labels
    assert got == want


# --- stage: widen


def _gap_growth() -> PlacementProblem:
    return three_columns()


def _block_move() -> PlacementProblem:
    return replace(three_columns(), area=Size(96, 128))


def _grew(_before: Placement, after: Placement) -> bool:
    return [g.tracks for g in after.pages[0].gaps] == [1, 2]


def _moved(before: Placement, after: Placement) -> bool:
    return (len(before.pages), len(after.pages)) == (1, 2)


CASES_widen: dict[str, tuple[Callable[[], PlacementProblem], Callable[[Placement, Placement], bool]]] = {
    "gap_growth": (_gap_growth, _grew),
    "block_move": (_block_move, _moved),
}


@pytest.mark.parametrize("case", CASES_widen)
@pytest.mark.parametrize("form", SPELLINGS)
def test_widen_does_not_depend_on_how_ids_are_spelled(case: str, form: str) -> None:
    build, feature = CASES_widen[case]
    prob = build()
    (cut, before, _), (_, want, _, _) = run(prob, demand=2)
    assert feature(before, want), case
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    respelled = respell_problem(prob, maps)
    _, (_, got, _, _) = run(respelled, demand=2)
    assert canon_placement(got, back_by_parts(maps)) == canon_placement(want, back_by_parts({}))


@pytest.mark.parametrize("case", CASES_widen)
def test_the_case_is_not_vacuous_without_the_demand(case: str) -> None:
    """Without the planted demand `_gap_growth` stays as placed: the demand is what grows it."""
    build, _ = CASES_widen[case]
    prob = build()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    routes = routed_from(cut, prob, PLAIN)
    _, after, _, _, _ = widen(cut, placement, Round((), (), routes, ()), prob, PLAIN)
    assert [g.tracks for g in after.pages[0].gaps] != [1, 2]
