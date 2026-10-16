"""Stage 4 reads no id text: respelling every id, or reordering the unordered input tuples,
changes nothing in the cut but the spelling (as test_order_rename does for stage 3)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Hints, Options, PlacementProblem, order_blocks
from fransys_layout.core.cut import cut_pages

from .conftest import MARKER_BOX
from .cut_fixtures import AREA, box_sym, chain, elem, free, net
from .cut_respell import (
    back_of,
    canon,
    id_sets,
    make_maps,
    respell_blocks,
    respell_flow,
    respell_problem,
)
from .pipeline_fixtures import blocks_of, flow_of

OPTIONS = Options(marker=MARKER_BOX)
SPELLINGS = ("{}", "{:04d}")  # each keeps the natural order of the ranks, spells it anew


def two_page_fan() -> PlacementProblem:
    """Two fans with free-sided hubs, each cut onto three pages: copies named feed2, feed10."""
    syms, nets = [], []
    for tag in ("2", "10"):
        syms += [free(f"t{tag}"), *(elem(f"a{tag}x{i}", 700, 400, f"G{tag}") for i in (1, 2, 3))]
        legs = (f"a{tag}x{i}.n" for i in (1, 2, 3))
        nets.append(net(f"feed{tag}", f"t{tag}.e", *legs))
    hints = Hints(group_order=("G2", "G10"))
    return PlacementProblem(AREA, tuple(syms), tuple(nets), hints=hints)


def card_that_wraps() -> PlacementProblem:
    """A 16-pin card with free columns either side: the free column on the right wraps."""
    syms = [box_sym(16), *(elem(f"k{i:02d}", 64, 32, "CH") for i in range(1, 17))]
    for name, w, group in (("f", 58, "FR"), ("g", 64, "GR")):
        syms += [elem(f"{name}{n}", w, 32, group) for n in (0, 1)]
    nets = [net(f"n{i:02d}", f"A1.p{i}", f"k{i:02d}.n") for i in range(1, 17)]
    nets += [net("fr", "f0.s", "f1.n"), net("gr", "g0.s", "g1.n")]
    hints = Hints(group_order=("FR", "PLC", "CH", "GR"))
    return PlacementProblem(AREA, tuple(syms), tuple(nets), hints=hints)


def forced_break() -> PlacementProblem:
    """Groups G2, G10 and G11 with a break before G10: the unit's second page starts there."""
    syms, nets = [], []
    for g in ("2", "10", "11"):
        syms += [elem(f"a{g}", 100, 32, f"G{g}"), elem(f"b{g}", 100, 32, f"G{g}")]
        nets.append(net(f"n{g}", f"a{g}.s", f"b{g}.n"))
    hints = Hints(group_order=("G2", "G10", "G11"), break_before=frozenset({"G10"}))
    return PlacementProblem(AREA, tuple(syms), tuple(nets), hints=hints)


def tall_column() -> PlacementProblem:
    """Twelve cells of 96 G in one column: the cut folds it into c#a and c#b over one tag."""
    ids = [f"k{i:02d}" for i in range(12)]
    syms = tuple(elem(i, 40, 96) for i in ids)
    return PlacementProblem(AREA, syms, tuple(chain(ids)))


CASES = {
    "two_page_fan": two_page_fan,
    "card_that_wraps": card_that_wraps,
    "break": forced_break,
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
    got = cut_pages(
        respell_blocks(lists, maps), respell_flow(flow, maps), respell_problem(prob, maps), OPTIONS
    )
    assert canon(got, back_of(maps)) == want


@pytest.mark.parametrize("case", CASES)
def test_the_cut_does_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    prob = CASES[case]()
    lists, flow = stages(prob)
    want = canon(cut_pages(lists, flow, prob, OPTIONS), back_of({}))
    flipped = replace(
        flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1]
    )
    reversed_prob = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    got = canon(cut_pages(lists, flipped, reversed_prob, OPTIONS), back_of({}))
    assert got[0] == want[0]
    assert sorted(got[1], key=repr) == sorted(want[1], key=repr)
    assert got[2] == want[2]
