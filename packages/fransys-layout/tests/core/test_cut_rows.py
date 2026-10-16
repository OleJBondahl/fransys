"""Stage 4's items measure every row the way `row_width` does (the oracle of layout-0280).

For every window of a unit's sequence that keeps whole blocks whole, the width the items give
is the width the pack modules give the same columns as one row.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Box, Hints, Options, PlacementProblem, order_blocks
from fransys_layout.core.cut_costs import sequence

from .cut_fixtures import AREA, box_sym, chain, elem, net
from .cut_oracle import window_misses
from .pipeline_fixtures import blocks_of, flow_of

OPTIONS = Options()
PAGE_H = AREA.h - 2 * OPTIONS.margin.h


def staggered(sym_id: str, body: int, text: int, group: str) -> object:
    """A column symbol whose text is wider than its body: the stagger packs it closer."""
    return replace(elem(sym_id, body, 32, group), footprint=Box(-text // 2, -16, text, 32))


def free_mixed() -> tuple[list, list, Hints | None]:
    """Columns of one to four cells and mixed widths, whose neighbours interleave by y."""
    syms, nets = [], []
    for k, (w, cells) in enumerate([(40, 1), (24, 4), (64, 2), (16, 3), (80, 1), (32, 4)]):
        ids = [f"c{k}z{n}" for n in range(cells)]
        syms += [elem(i, w, 32 + 8 * n, f"G{k}") for n, i in enumerate(ids)]
        nets += chain(ids, f"x{k}_")
    return syms, nets, Hints(group_order=tuple(f"G{k}" for k in range(6)))


def card_between() -> tuple[list, list, Hints | None]:
    syms = [box_sym(5), *(elem(f"k{i}", 40, 32, "CH") for i in range(1, 6))]
    syms += [
        elem("f0", 24, 32, "FR"),
        elem("f1", 24, 32, "FR"),
        elem("g0", 56, 64, "GR"),
        elem("g1", 56, 48, "GR"),
    ]
    nets = [net(f"n{i}", f"A1.p{i}", f"k{i}.n") for i in range(1, 6)]
    nets += [net("fr", "f0.s", "f1.n"), net("gr", "g0.s", "g1.n")]
    return syms, nets, Hints(group_order=("FR", "PLC", "CH", "GR"))


def two_cards() -> tuple[list, list, Hints | None]:
    second = replace(box_sym(4), id="A2", group="PLC2")
    syms = [box_sym(3), second]
    syms += [elem(f"k{i}", 32, 32, "CH") for i in range(1, 4)]
    syms += [elem(f"m{i}", 48, 32, "CM") for i in range(1, 5)]
    nets = [net(f"n{i}", f"A1.p{i}", f"k{i}.n") for i in range(1, 4)]
    nets += [net(f"q{i}", f"A2.p{i}", f"m{i}.n") for i in range(1, 5)]
    return syms, nets, Hints(group_order=("PLC", "CH", "PLC2", "CM"))


def staggered_pair() -> tuple[list, list, Hints | None]:
    syms = [staggered(f"{p}{i}", 24, 80, f"G{i}") for i in range(5) for p in "ab"]
    nets = [net(f"n{i}", f"a{i}.s", f"b{i}.n") for i in range(5)]
    return syms, nets, Hints(group_order=tuple(f"G{i}" for i in range(5)))


CASES = {
    "free_mixed": free_mixed,
    "card_between": card_between,
    "two_cards": two_cards,
    "staggered_pair": staggered_pair,
}


def unit_of(case: str, options: Options = OPTIONS):
    syms, nets, hints = CASES[case]()
    prob = PlacementProblem(AREA, tuple(syms), tuple(nets), hints=hints or Hints())
    flow = flow_of(prob, options)
    unit = order_blocks(blocks_of(prob, options), flow, options)[0]
    return prob, flow, unit


@pytest.mark.parametrize("case", CASES)
def test_every_window_of_the_sequence_is_as_wide_as_its_row(case: str) -> None:
    prob, flow, unit = unit_of(case)
    seq = sequence(unit, flow, prob, OPTIONS, PAGE_H)
    checked, bad = window_misses(seq, unit, (flow, prob, OPTIONS))
    assert checked > len({it.block for it in seq})  # windows across blocks are looked at
    assert bad == []


def test_the_cards_plants_hold_a_whole_block() -> None:
    for case in ("card_between", "two_cards"):
        prob, flow, unit = unit_of(case)
        assert any(it.whole for it in sequence(unit, flow, prob, OPTIONS, PAGE_H))
