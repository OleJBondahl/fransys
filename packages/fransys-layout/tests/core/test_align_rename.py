"""Stage 5 with bands and mates reads no id text beyond the natural key: respelled ids and
reordered input tuples (a mate's pair swapped too) give the same placement."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core import Facts, PinRef
from fransys_layout.core.place import place_pages

from . import align_fixtures as fx
from .cut_respell import (
    back_of,
    canon_placement,
    id_sets,
    make_maps,
    respell_cut,
    respell_problem,
)
from .pipeline_fixtures import cut_of
from .test_cut_rename import SPELLINGS

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import PlacementProblem

OPTIONS = core_options(
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)
CASES: dict[str, Callable[[], PlacementProblem]] = {
    "band": fx.two_band_columns,
    "mate": fx.mate_columns,
}


def _mates(prob: PlacementProblem, maps: dict[str, str]) -> Facts:
    return Facts(
        mates=tuple(
            (PinRef(maps[a.sym], a.pin), PinRef(maps[b.sym], b.pin)) for a, b in prob.facts.mates
        ),
    )


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("form", SPELLINGS)
def test_placement_does_not_depend_on_how_ids_are_spelled(case: str, form: str) -> None:
    prob = CASES[case]()
    cut = cut_of(prob, OPTIONS)
    want = canon_placement(place_pages(cut, prob, OPTIONS), back_of({}))
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    spelled = replace(respell_problem(prob, maps), facts=_mates(prob, maps))
    got = place_pages(respell_cut(cut, maps), spelled, OPTIONS)
    assert canon_placement(got, back_of(maps)) == want
    assert any(p.placed for p in got.pages)


@pytest.mark.parametrize("case", CASES)
def test_placement_does_not_depend_on_the_order_of_the_input(case: str) -> None:
    prob = CASES[case]()
    want = canon_placement(place_pages(cut_of(prob, OPTIONS), prob, OPTIONS), back_of({}))
    mates = tuple((b, a) for a, b in reversed(prob.facts.mates))
    flipped = replace(
        prob,
        symbols=tuple(reversed(prob.symbols)),
        nets=tuple(reversed(prob.nets)),
        facts=Facts(mates=mates),
    )
    got = place_pages(cut_of(flipped, OPTIONS), flipped, OPTIONS)
    assert canon_placement(got, back_of({})) == want
