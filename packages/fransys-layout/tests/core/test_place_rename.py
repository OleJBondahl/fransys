"""Stage 5 reads no id text beyond the natural key: respelling every id, or reordering the
unordered input tuples, changes nothing in the placement but the spelling (as test_cut_rename
does for stage 4)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Options, place_pages

from .cut_respell import (
    back_of,
    canon_placement,
    id_sets,
    make_maps,
    respell_cut,
    respell_problem,
)
from .pipeline_fixtures import cut_of
from .place_fixtures import bundle_fan, two_edge_card
from .test_cut_rename import SPELLINGS, card_that_wraps, two_page_fan

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import Placement, PlacementProblem

OPTIONS = Options()


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
CASES: dict[str, tuple[Callable[[], PlacementProblem], Callable[[Placement], bool]]] = {
    "two_edge_card": (lambda: two_edge_card(16, 96), _two_edges),
    "card_that_wraps": (card_that_wraps, _two_rows),
    "two_page_fan": (two_page_fan, _two_pages),
    "bundle_fan": (bundle_fan, _wide_trunk),
}


def _checked(case: str) -> tuple[PlacementProblem, tuple]:
    build, feature = CASES[case]
    prob = build()
    cut = cut_of(prob, OPTIONS)
    pl = place_pages(cut, prob, OPTIONS)
    assert sum(len(p.placed) for p in pl.pages) >= 3
    assert feature(pl), case
    return prob, (cut, canon_placement(pl, back_of({})))


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("form", SPELLINGS)
def test_placement_does_not_depend_on_how_ids_are_spelled(case: str, form: str) -> None:
    prob, (cut, want) = _checked(case)
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    got = place_pages(respell_cut(cut, maps), respell_problem(prob, maps), OPTIONS)
    assert canon_placement(got, back_of(maps)) == want


@pytest.mark.parametrize("case", CASES)
def test_placement_does_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    prob, (cut, want) = _checked(case)
    flow = cut.flow
    flipped = replace(
        flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1]
    )
    reversed_prob = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    got = place_pages(replace(cut, flow=flipped), reversed_prob, OPTIONS)
    assert canon_placement(got, back_of({})) == want
