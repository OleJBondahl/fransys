"""Stage 3, the column order of one block: hand-built flows, an independent cost, a oracle.

No builders and no topology: every FlowGraph here is made from the values by hand.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

import pytest
from options_fixtures import core_options

from fransys_layout.core import order, order_search
from fransys_layout.core.values import Block, BlockList, Fan, Finding, FlowGraph

from .order_fixtures import (
    OPTIONS,
    att,
    block,
    box_column,
    comb,
    dense,
    fan,
    flow,
    grouped,
    keeps_rules,
    kind_case,
    link,
    oracle,
    ordered,
    random_case,
    ref_cost,
    refuse_exact,
    shuffled,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core.order_search import Before, Span

# ---- the cost ------------------------------------------------------------------------------------


def test_order_cost_by_hand() -> None:
    assert (
        order.order_cost(["a", "b", "c"], flow([fan("f", ["a", "c"])])) == 1
    )  # one foreign column
    assert (
        order.order_cost(["a", "b", "c"], flow(links=[link("x", ["a", "c"])])) == 2
    )  # foreign plus between
    two = flow([fan("f", ["a", "c"]), fan("g", ["b", "d"])])
    assert order.order_cost(list("abcd"), two) == 3  # two foreign columns and one interleave
    assert order.order_cost(list("acbd"), two) == 0  # disjoint
    assert order.order_cost(list("abdc"), two) == 2  # nested: two foreign columns, no interleave
    three_ends = flow(
        links=[link("x", ["a", "b", "d"])]
    )  # a decision: the outermost two ends count as its two ends
    assert order.order_cost(list("abcd"), three_ends) == 3


@pytest.mark.parametrize("seed", range(8))
def test_order_cost_equals_the_reference_on_any_order(seed: int) -> None:
    blk, fl = random_case(seed)
    rng = random.Random(seed)  # noqa: S311 - seeded test data
    for _ in range(20):
        perm = rng.sample(list(blk.columns), len(blk.columns))
        assert order.order_cost(perm, fl) == ref_cost(perm, fl)


# ---- the search ----------------------------------------------------------------------------------


def test_twelve_columns_of_three_interleaved_hubs_reach_cost_zero_in_a_deterministic_order() -> (
    None
):
    blk, fl = comb(12)
    got = ordered(blk, fl)
    assert got == grouped(12)
    assert ref_cost(got, fl) == 0
    assert ref_cost(sorted(blk.columns), fl) > 0  # natural order is not already the answer
    for seed in range(3):  # the order the block lists its columns in does not matter
        assert ordered(block(shuffled(blk.columns, seed)), fl) == got


def test_thirteen_columns_go_through_the_median_sweep_and_reach_the_same_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(order, "exact_search", refuse_exact)
    blk, fl = comb(13)
    got = ordered(blk, fl)
    assert sorted(got) == sorted(blk.columns)
    assert ref_cost(got, fl) == 0
    for seed in range(3):
        assert ordered(block(shuffled(blk.columns, seed)), fl) == got


def test_exact_order_limit_option_picks_the_search(monkeypatch: pytest.MonkeyPatch) -> None:
    blk13, fl13 = comb(13)
    assert ordered(
        blk13,
        fl13,
        core_options(
            exact_order_limit=13,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    ) == grouped(13)  # exact: natural-first of the best
    monkeypatch.setattr(order, "exact_search", refuse_exact)
    blk12, fl12 = comb(12)
    assert (
        ref_cost(
            ordered(
                blk12,
                fl12,
                core_options(
                    exact_order_limit=11,
                    flip_turn="R180",
                    tag_stagger=True,
                    label_gap=8,
                    parallel_pitch=48,
                    driver_first=True,
                    arrow_sides=("E", "W"),
                ),
            ),
            fl12,
        )
        == 0
    )  # sweep


@pytest.mark.parametrize("seed", range(12))
def test_a_swept_order_keeps_the_rules_and_no_allowed_swap_of_two_columns_lowers_its_cost(
    seed: int,
) -> None:
    blk, fl = random_case(seed, sizes=(13, 14, 15, 16), more_fans=(4, 8))
    got = tuple(ordered(blk, fl))
    assert sorted(got) == sorted(blk.columns)
    assert keeps_rules(got, blk, fl)
    for i, j in itertools.combinations(range(len(got)), 2):
        swapped = list(got)
        swapped[i], swapped[j] = swapped[j], swapped[i]
        if keeps_rules(tuple(swapped), blk, fl):
            assert ref_cost(swapped, fl) >= ref_cost(got, fl)


@pytest.mark.parametrize("n", [4, 14])
def test_rules_that_conflict_still_return_every_column_once(n: int) -> None:
    """Driver first wants c3 before c1, the bundle wants c1 before c3: the stage degrades, it does
    not fail."""
    cols = [f"c{i:02d}" for i in range(1, n + 1)]
    fl = flow(
        [
            fan("f", ["c02", "c04"], ["c03"]),
            fan("b", ["c01", "c03"], lanes=2),
            *[fan(f"h{h}", cols[h::3]) for h in range(3)],
        ]
    )
    got = ordered(block(cols, "f"), fl)
    assert sorted(got) == cols
    assert ordered(block(cols, "f"), fl) == got


def test_without_spans_the_columns_stand_in_natural_order() -> None:
    assert ordered(block(["c10", "c3", "c2"]), flow()) == ["c2", "c3", "c10"]
    assert ordered(block(["c10", "c3", "c2"]), flow([fan("f", ["c3"])], [link("x", ["c2"])])) == [
        "c2",
        "c3",
        "c10",
    ]


@pytest.mark.parametrize("seed", range(40))
def test_exact_search_matches_brute_force_with_natural_order_winning_ties(seed: int) -> None:
    blk, fl = random_case(seed)
    assert ordered(blk, fl) == oracle(blk, fl)


# ---- swaps of any two columns --------------------------------------------------------------------


def adjacent_descent(perm: list[str], fl: FlowGraph) -> list[str]:
    """What the sweep used to end with: swap neighbours while the cost strictly falls."""
    perm = list(perm)
    improved = True
    while improved:
        improved = False
        for i in range(len(perm) - 1):
            swapped = [*perm[:i], perm[i + 1], perm[i], *perm[i + 2 :]]
            if ref_cost(swapped, fl) < ref_cost(perm, fl):
                perm, improved = swapped, True
    return perm


def test_swapping_any_two_columns_beats_swapping_neighbours_only() -> None:
    """a b c d with hubs {a, d} and {b, c}: no neighbour swap lowers the cost of 2, but a pair swap
    reaches 0."""
    fl = flow([fan("h1", ["a", "d"]), fan("h2", ["b", "c"])])
    start = list("abcd")
    assert ref_cost(start, fl) == 2
    assert adjacent_descent(start, fl) == start  # a local minimum for neighbour swaps
    spans = [s for s in order._spans(start, fl) if len(s[0]) < len(start)]
    got = order._swap_pairs(start, spans, {c: frozenset() for c in start})
    assert ref_cost(got, fl) == 0


def obeys(arrangement: list[str], before: dict[str, frozenset[str]]) -> bool:
    return all(arrangement.index(p) < arrangement.index(c) for c in arrangement for p in before[c])


@pytest.mark.parametrize("seed", range(6))
def test_a_swap_is_allowed_exactly_when_every_predecessor_stays_ahead(seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 - seeded test data
    perm = [f"c{i}" for i in rng.sample(range(8), 8)]
    before = {
        c: frozenset(rng.sample(perm[:k], rng.randint(0, min(k, 3)))) for k, c in enumerate(perm)
    }  # perm obeys it
    assert obeys(perm, before)
    for i, j in itertools.combinations(range(8), 2):
        swapped = list(perm)
        swapped[i], swapped[j] = swapped[j], swapped[i]
        assert order._swappable(perm, i, j, before) == obeys(swapped, before)


# ---- the median passes ---------------------------------------------------------------------------


def test_median_passes_get_past_a_cost_that_swaps_of_two_columns_cannot_lower() -> None:
    """Two fans share a: the natural order costs 3, no swap of two columns passes 2, the sweep
    reaches 1."""
    fl = flow([fan("f1", ["a", "b", "e"]), fan("f2", ["a", "c", "d"])])
    start = list("abcde")
    assert ref_cost(start, fl) == 3
    spans = [s for s in order._spans(start, fl) if len(s[0]) < len(start)]
    assert (
        ref_cost(order._swap_pairs(start, spans, {c: frozenset() for c in start}), fl) == 2
    )  # swaps alone stop here
    assert (
        ref_cost(
            ordered(
                block(start),
                fl,
                core_options(
                    exact_order_limit=0,
                    flip_turn="R180",
                    tag_stagger=True,
                    label_gap=8,
                    parallel_pitch=48,
                    driver_first=True,
                    arrow_sides=("E", "W"),
                ),
            ),
            fl,
        )
        == 1
    )


def test_the_sweep_keeps_the_best_order_a_median_pass_gave_not_the_last() -> None:
    """The one median pass raises the cost from 4 to 5; the swaps go on from the order before it
    and reach 2."""
    fl = flow([fan("f1", list("cae")), fan("f2", list("bd"))], [link("x", list("ba"))])
    start = list("abcde")
    spans = [s for s in order._spans(start, fl) if len(s[0]) < len(start)]
    assert ref_cost(start, fl) == 4
    assert ref_cost(order._median_pass(start, spans, {c: frozenset() for c in start}), fl) == 5
    assert (
        ref_cost(
            ordered(
                block(start),
                fl,
                core_options(
                    exact_order_limit=0,
                    flip_turn="R180",
                    tag_stagger=True,
                    label_gap=8,
                    parallel_pitch=48,
                    driver_first=True,
                    arrow_sides=("E", "W"),
                ),
            ),
            fl,
        )
        == 2
    )


# ---- the node budget -----------------------------------------------------------------------------


class Counted(order_search.Search):
    """A search that notes itself, so that a test can read how many nodes it expanded."""

    made: ClassVar[list[order_search.Search]] = []

    def __init__(
        self, cols: Sequence[str], spans: Sequence[Span], before: Before, bound: int, budget: int
    ) -> None:
        super().__init__(cols, spans, before, bound, budget)
        Counted.made.append(self)


def test_a_search_cut_short_returns_the_sweeps_order_deterministically() -> None:
    blk, fl = dense()
    sweep = ordered(
        blk,
        fl,
        core_options(
            exact_order_limit=0,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert ref_cost(ordered(blk, fl), fl) < ref_cost(
        sweep, fl
    )  # planted: the default budget finds a better order
    for budget in (0, 1, 12):  # fewer nodes than the 13 that reach one leaf
        assert (
            ordered(
                blk,
                fl,
                core_options(
                    exact_order_nodes=budget,
                    flip_turn="R180",
                    tag_stagger=True,
                    label_gap=8,
                    parallel_pitch=48,
                    driver_first=True,
                    arrow_sides=("E", "W"),
                ),
            )
            == sweep
        )
        assert (
            ordered(
                blk,
                fl,
                core_options(
                    exact_order_nodes=budget,
                    flip_turn="R180",
                    tag_stagger=True,
                    label_gap=8,
                    parallel_pitch=48,
                    driver_first=True,
                    arrow_sides=("E", "W"),
                ),
            )
            == sweep
        )


def test_a_cut_search_expands_exactly_its_budget_in_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(order_search, "Search", Counted)
    blk, fl = dense()
    for budget in (0, 1, 5, 13, 100, 1000):
        Counted.made.clear()
        ordered(
            blk,
            fl,
            core_options(
                exact_order_nodes=budget,
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
        (search,) = Counted.made
        assert search.nodes == budget
    Counted.made.clear()
    ordered(
        blk,
        fl,
        core_options(
            exact_order_nodes=10**9,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )
    assert Counted.made[0].nodes < 10_000  # this search finishes by itself


def test_more_nodes_never_give_a_worse_order_and_none_is_worse_than_the_sweep() -> None:
    blk, fl = dense()
    sweep_cost = ref_cost(
        ordered(
            blk,
            fl,
            core_options(
                exact_order_limit=0,
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        ),
        fl,
    )
    costs = []
    for budget in (0, 1, 12, 13, 14, 40, 200, 1000, 5000, 10**9):
        got = ordered(
            blk,
            fl,
            core_options(
                exact_order_nodes=budget,
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
        assert sorted(got) == sorted(blk.columns)
        costs.append(ref_cost(got, fl))
    assert costs == sorted(costs, reverse=True)
    assert costs[0] == sweep_cost
    assert costs[-1] < sweep_cost


# ---- a card, the driver, a bundle, a fixed block -------------------------------------------------


def test_a_card_keeps_its_pin_order() -> None:
    """Pins 7, 3, 5 in box order; a column on a pin the box does not list stands last, natural
    order among those."""
    pins = {"c1": "5", "c2": "7", "c3": "3", "c4": "9", "c5": "8"}
    fl = flow(
        [fan("f", ["c1", "c2"])], columns=[box_column(c, p) for c, p in pins.items()]
    )  # f pulls c1 and c2 together
    card = block(
        ["c5", "c4", "c3", "c2", "c1"], kind="card", pin_edges=(("7", "N"), ("3", "N"), ("5", "N"))
    )
    assert ordered(card, fl) == ["c2", "c3", "c1", "c4", "c5"]
    (out,) = order.order_blocks((BlockList("u", (card,)),), fl, OPTIONS)
    assert out.blocks[0].columns == ("c2", "c3", "c1", "c4", "c5")


def test_the_driver_column_stands_first_unless_it_is_a_leg_too() -> None:
    blk = block(["c1", "c2", "c3", "c4"], "f")
    assert ordered(blk, flow([fan("f", ["c1", "c2", "c4"], ["c3"])])) == ["c3", "c1", "c2", "c4"]
    both = flow(
        [fan("f", ["c1", "c2", "c4", "c3"], ["c3"])]
    )  # the driver is a leg too: no rule, natural order
    assert ordered(blk, both) == ["c1", "c2", "c3", "c4"]


def test_a_bundles_legs_keep_pole_order() -> None:
    reverse = flow(
        [fan("b", ["c3", "c2", "c1"], lanes=3)]
    )  # pole order is the reverse of natural order
    assert ordered(block(["c1", "c2", "c3"]), reverse) == ["c3", "c2", "c1"]


def test_pole_order_holds_against_a_pull_to_natural_order() -> None:
    """Without the rule the best order is c1 c4 c2 c3; the bundle lists c3 before c2."""
    blk = block(["c1", "c2", "c3", "c4"])
    fl = flow([fan("b", ["c3", "c2"], lanes=2), fan("a", ["c1", "c4"])])
    assert ordered(blk, fl) == ["c1", "c4", "c3", "c2"]
    assert ref_cost(["c1", "c4", "c3", "c2"], fl) == 0


def test_pole_order_holds_through_the_median_sweep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(order, "exact_search", refuse_exact)
    cols = [f"c{i:02d}" for i in range(1, 15)]
    fans = [fan(f"h{h}", cols[h::3]) for h in range(3)] + [fan("b", ["c14", "c09", "c02"], lanes=3)]
    got = ordered(block(cols), flow(fans))
    assert sorted(got) == cols
    assert got.index("c14") < got.index("c09") < got.index("c02")


def test_legs_sharing_a_column_have_no_pole_order() -> None:
    """The rule is for one column per leg: two legs in c3 leave the search free to put c1 first."""
    legs = (att("c3"), replace(att("c3"), lane=1), att("c1"))
    fl = flow([Fan("b", ("b",), (), legs, None, 3, "above")])
    assert ordered(block(["c1", "c2", "c3"]), fl) == ["c1", "c3", "c2"]


def test_a_fixed_order_block_keeps_its_columns_and_reads_no_pin_order() -> None:
    """Stage 2 fixed this order from a chain hint: no search, no driver first, no box pin to look
    up."""
    cols = ["c4", "c2", "c3", "c1"]
    fl = flow(
        [fan("f1", ["c1", "c2", "c4"], ["c3"]), fan("f2", ["c1", "c3"])]
    )  # flow.columns is empty
    fixed = block(cols, "f1", fixed_order=True)
    assert ordered(fixed, fl) == cols
    assert (
        ordered(replace(fixed, fixed_order=False), fl) != cols
    )  # the same block, not fixed, is searched
    (out,) = order.order_blocks((BlockList("u", (fixed,)),), fl, OPTIONS)
    assert out.blocks[0] == fixed


def test_order_blocks_keeps_findings_and_every_block_field() -> None:
    """Rebuilding a BlockList or a Block loses nothing: findings, fixed_order, pin_edges, group,
    sizes and flags."""
    odd = Block(
        "b1",
        "fan",
        "u7",
        ("c3", "c1", "c2"),
        "=A1",
        "f1",
        "g9",
        321,
        654,
        short=True,
        keep_whole=True,
        forced_break_before=True,
        seat="none",
        pin_edges=(("1", "N"),),
        fixed_order=False,
    )
    fixed = replace(odd, id="b2", fixed_order=True)
    card = replace(
        odd, id="b3", kind="card", columns=("c2", "c1"), pin_edges=(("2", "S"), ("1", "N"))
    )
    fl = flow([fan("f1", ["c1", "c3"])], columns=[box_column("c1", "1"), box_column("c2", "2")])
    findings = (Finding("KEEP_TOGETHER_UNMET", "text", 2, "g9"),)
    lists = (BlockList("u7", (odd, fixed, card), findings), BlockList("u8", ()))
    out = order.order_blocks(lists, fl, OPTIONS)
    assert [(bl.unit, bl.findings) for bl in out] == [("u7", findings), ("u8", ())]
    assert [b.id for b in out[0].blocks] == ["b1", "b2", "b3"]
    for before, after in zip(lists[0].blocks, out[0].blocks, strict=True):
        assert replace(after, columns=before.columns) == before  # only the columns may move
    assert out[0].blocks[1].fixed_order is True
    assert out[0].blocks[1].columns == fixed.columns
    assert out[0].blocks[2].columns == ("c2", "c1")  # the card: pin 2 then pin 1


# ---- T4: the stage never asks what a thing is ----------------------------------------------------


@pytest.mark.parametrize("col", ["c{}", "{}", "=X{}:1.terminal"])
def test_a_terminal_hub_and_a_plain_box_hub_give_equal_orders(col: str) -> None:
    """Two flows equal apart from symbol ids: a hub named like a terminal against a plain box."""
    t_cols, t_flow = kind_case("=X{}:1.terminal", col)
    b_cols, b_flow = kind_case("=K{}.box", col.replace("X", "K").replace(":1.terminal", ".box"))
    at_t = [t_cols.index(c) for c in ordered(block(t_cols), t_flow)]
    at_b = [b_cols.index(c) for c in ordered(block(b_cols), b_flow)]
    assert at_t == at_b
    assert at_t != sorted(at_t)  # the order moved: the check is not vacuous
    assert ref_cost([t_cols[i] for i in at_t], t_flow) < ref_cost(t_cols, t_flow)
