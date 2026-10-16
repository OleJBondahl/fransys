"""Stage 7 reads no id text beyond the natural key: respelling every symbol and net id changes
nothing in the widened placement but the spelling (as test_place_rename does for stage 5).

The whole pipeline runs on the respelled problem: widen cuts again from the problem, so a cut
respelled by hand would not carry the column ids the re-cut spells for its reserves."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Size
from fransys_layout.core.widen import widen

from .cut_respell import (
    back_of,
    canon_placement,
    id_sets,
    make_maps,
    respell_problem,
)
from .pipeline_fixtures import cut_of, placed_from, routed_from
from .test_cut_rename import SPELLINGS
from .test_widen import PLAIN, three_columns
from .test_widen_pass import run

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import Placement, PlacementProblem


def _gap_growth() -> PlacementProblem:
    return three_columns()


def _block_move() -> PlacementProblem:
    return replace(three_columns(), area=Size(96, 128))


def _grew(_before: Placement, after: Placement) -> bool:
    return [g.tracks for g in after.pages[0].gaps] == [1, 2]


def _moved(before: Placement, after: Placement) -> bool:
    return (len(before.pages), len(after.pages)) == (1, 2)


CASES: dict[str, tuple[Callable[[], PlacementProblem], Callable[[Placement, Placement], bool]]] = {
    "gap_growth": (_gap_growth, _grew),
    "block_move": (_block_move, _moved),
}


def _back(maps: dict[str, str]) -> Callable[[str | None], str | None]:
    """`back_of`, and the ids stage 3 spells from a symbol id ("c:S0001") by their parts."""
    inv = back_of(maps)

    def back(i: str | None) -> str | None:
        return None if i is None else ":".join(inv(part) or part for part in i.split(":"))

    return back


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("form", SPELLINGS)
def test_widen_does_not_depend_on_how_ids_are_spelled(case: str, form: str) -> None:
    build, feature = CASES[case]
    prob = build()
    (cut, before, _), (_, want, _, _) = run(prob, demand=2)
    assert feature(before, want), case
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    respelled = respell_problem(prob, maps)
    _, (_, got, _, _) = run(respelled, demand=2)
    assert canon_placement(got, _back(maps)) == canon_placement(want, _back({}))


@pytest.mark.parametrize("case", CASES)
def test_the_case_is_not_vacuous_without_the_demand(case: str) -> None:
    """Without the planted demand `_gap_growth` stays as placed: the demand is what grows it."""
    build, _ = CASES[case]
    prob = build()
    cut = cut_of(prob, PLAIN)
    placement = placed_from(cut, prob, PLAIN)
    routes = routed_from(cut, prob, PLAIN)
    _, after, _, _ = widen(cut, placement, routes, prob, PLAIN)
    assert [g.tracks for g in after.pages[0].gaps] != [1, 2]
