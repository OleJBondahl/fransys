"""Stage 8b reads no id text beyond the natural key: respelling every id, or reversing the
unordered input tuples, changes no label but its spelling."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core import place_annexes
from fransys_layout.core.outputs import Annotations
from fransys_layout.core.place import place_pages
from fransys_layout.core.route import route_pages
from fransys_layout.core.text_markers import mark_pages

from . import pipeline_fixtures
from .conftest import MARKER
from .cut_respell import back_of, id_sets, make_maps, respell_cut, respell_problem
from .test_cut_rename import SPELLINGS
from .text_fixtures import PLANTS

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import AnnexBox

OPTIONS = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)


def _canon(labels: tuple[AnnexBox, ...], back: Callable[[str | None], str | None]) -> list:
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
    routes = route_pages(placement, cut2, prob2, OPTIONS)
    markers = mark_pages(cut2, placement, prob2, OPTIONS)
    labelled = pipeline_fixtures.with_annexes(prob2, OPTIONS)
    got, _ = place_annexes(placement, routes, Annotations(markers=markers), labelled, OPTIONS)
    assert got
    assert _canon(got, back_of(maps)) == _canon(want, back_of({}))


@pytest.mark.parametrize("name", PLANTS)
def test_labels_do_not_depend_on_the_order_of_the_input_tuples(name: str) -> None:
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want, _ = pipeline_fixtures.labelled_of(prob, OPTIONS)
    flow = cut.flow
    flipped = replace(
        flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1]
    )
    prob2 = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    cut2 = replace(cut, flow=flipped)
    placement = place_pages(cut2, prob2, OPTIONS)
    routes = route_pages(placement, cut2, prob2, OPTIONS)
    markers = mark_pages(cut2, placement, prob2, OPTIONS)
    # The annexes are the caller's, in the caller's order (R345: the core sorts nothing); the
    # symbol, net and flow tuples it is handed in reverse change no box.
    labelled = replace(prob2, annexes=pipeline_fixtures.with_annexes(prob, OPTIONS).annexes)
    got, _ = place_annexes(placement, routes, Annotations(markers=markers), labelled, OPTIONS)
    assert got == want
