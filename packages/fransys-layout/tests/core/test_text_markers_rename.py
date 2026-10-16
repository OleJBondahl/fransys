"""Stage 8a reads no id text beyond the natural key: respelling every id, or reversing the
unordered input tuples, changes no marker but its spelling."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Options, mark_pages, place_pages

from . import pipeline_fixtures
from .conftest import MARKER_BOX
from .cut_respell import back_of, id_sets, make_maps, respell_cut, respell_problem
from .test_cut_rename import SPELLINGS
from .text_fixtures import PLANTS

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core import Marker

OPTIONS = Options(marker=MARKER_BOX)


def _canon(markers: tuple[Marker, ...], back: Callable[[str | None], str | None]) -> list:
    return [
        (back(m.net), m.kind, m.page, m.cell, m.x, m.y, m.end and (back(m.end.sym), m.end.pin))
        for m in markers
    ]


@pytest.mark.parametrize("name", PLANTS)
@pytest.mark.parametrize("form", SPELLINGS)
def test_markers_do_not_depend_on_how_ids_are_spelled(name: str, form: str) -> None:
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want = _canon(mark_pages(cut, place_pages(cut, prob, OPTIONS), prob, OPTIONS), back_of({}))
    assert want
    maps = make_maps(id_sets(prob, cut.flow, cut.blocks), form)
    cut2, prob2 = respell_cut(cut, maps), respell_problem(prob, maps)
    got = mark_pages(cut2, place_pages(cut2, prob2, OPTIONS), prob2, OPTIONS)
    assert _canon(got, back_of(maps)) == want


@pytest.mark.parametrize("name", PLANTS)
def test_markers_do_not_depend_on_the_order_of_the_input_tuples(name: str) -> None:
    prob = PLANTS[name]()
    cut = pipeline_fixtures.cut_of(prob, OPTIONS)
    want = _canon(mark_pages(cut, place_pages(cut, prob, OPTIONS), prob, OPTIONS), back_of({}))
    flow = cut.flow
    flipped = replace(
        flow, columns=flow.columns[::-1], fans=flow.fans[::-1], cross_links=flow.cross_links[::-1]
    )
    prob2 = replace(prob, symbols=prob.symbols[::-1], nets=prob.nets[::-1])
    cut2 = replace(cut, flow=flipped)
    got = mark_pages(cut2, place_pages(cut2, prob2, OPTIONS), prob2, OPTIONS)
    assert _canon(got, back_of({})) == want
