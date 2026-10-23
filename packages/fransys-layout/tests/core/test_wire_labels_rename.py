"""Stage 8c reads no id text beyond the natural key: respelling every id, or reversing the
unordered input tuples, changes no wire label but its spelling."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from options_fixtures import core_options

from fransys_layout.core import Size, place_annexes
from fransys_layout.core.outputs import Annotations
from fransys_layout.core.place import place_pages
from fransys_layout.core.route import route_pages
from fransys_layout.core.text_markers import mark_pages
from fransys_layout.core.text_wires import label_nets

from . import pipeline_fixtures
from .conftest import MARKER
from .cut_respell import back_of, id_sets, make_maps, respell_cut, respell_problem
from .test_cut_rename import SPELLINGS
from .text_fixtures import PLANTS

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import PlacementProblem
    from fransys_layout.core.outputs import WireLabel
    from fransys_layout.core.values import CutResult

OPTIONS = core_options(
    marker=MARKER,
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    driver_first=True,
    arrow_sides=("E", "W"),
)
NO_WIRE: set[str] = set()  # plants whose pages draw no wire, so carry no wire label


def _labelled(prob: PlacementProblem) -> PlacementProblem:
    """Every net asks for a 24 by 8 wire label."""
    return replace(prob, nets=tuple(replace(n, label=Size(24, 8)) for n in prob.nets))


def _run(
    cut: CutResult, prob: PlacementProblem, order: PlacementProblem | None = None
) -> tuple[WireLabel, ...]:
    """Stages 6 to 8c; the annexes are `order`'s when given (the caller's order, R345)."""
    placement = place_pages(cut, prob, OPTIONS)
    routes = route_pages(placement, cut, prob, OPTIONS)
    markers = mark_pages(cut, placement, prob, OPTIONS)
    annexes = pipeline_fixtures.with_annexes(order or prob, OPTIONS).annexes
    seed = Annotations(markers=markers)
    boxes, _ = place_annexes(placement, routes, seed, replace(prob, annexes=annexes), OPTIONS)
    notes = Annotations(markers=markers, annexes=boxes)
    return label_nets(placement, routes, notes, prob, OPTIONS)[0]


def _canon(labels: tuple[WireLabel, ...], back: Callable[[str | None], str | None]) -> list:
    return sorted((w.page, back(w.net), w.box) for w in labels)


@pytest.mark.parametrize("name", PLANTS)
@pytest.mark.parametrize("form", SPELLINGS)
def test_wire_labels_do_not_depend_on_how_ids_are_spelled(name: str, form: str) -> None:
    prob = _labelled(PLANTS[name]())
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want = pipeline_fixtures.wire_labelled_of(prob, OPTIONS)[0]
    assert want or name in NO_WIRE
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    got = _run(respell_cut(cut, maps), respell_problem(prob, maps))
    assert got or name in NO_WIRE
    assert _canon(got, back_of(maps)) == _canon(want, back_of({}))


@pytest.mark.parametrize("name", PLANTS)
def test_wire_labels_do_not_depend_on_the_order_of_the_input_tuples(name: str) -> None:
    prob = _labelled(PLANTS[name]())
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want = pipeline_fixtures.wire_labelled_of(prob, OPTIONS)[0]
    flow = cut.flow
    flipped = replace(
        flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1]
    )
    prob2 = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    assert _run(replace(cut, flow=flipped), prob2, prob) == want


def test_the_plants_with_wires_carry_wire_labels() -> None:
    assert [
        n
        for n in PLANTS
        if not pipeline_fixtures.wire_labelled_of(_labelled(PLANTS[n]()), OPTIONS)[0]
    ] == sorted(NO_WIRE)
