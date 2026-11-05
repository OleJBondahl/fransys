"""RANK-INVARIANCE repros at the core seam, no salt (FABLE-SYMBOL-TIE section 8; spec s4 P0).

The cut and the router each break a tie by the text of an id. Each repro has a baseline half that
passes today, so its strict xfail (tests/gap_flip_other.toml, R272) fails only on the tie: P2
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Facts, Hints, PlacementProblem, Size
from fransys_layout.core.route import route_page

from .cut_fixtures import net, side
from .pipeline_fixtures import cut_of
from .route_fixtures import link_env
from .test_route_rename import OPTIONS

if TYPE_CHECKING:
    from collections.abc import Mapping

SWAP = {"A 1": "A 2", "A 2": "A 1", "B 1": "B 1", "B 2": "B 2"}
IDS = tuple(SWAP)


def _cut_problem(spelling: Mapping[str, str]) -> PlacementProblem:
    """Four equal symbols in one group, two items, one net over A 1, B 1, B 2; a page fits two."""
    items = {"A 1": "I1", "A 2": "I1", "B 1": "I2", "B 2": "I2"}
    syms = tuple(replace(side(spelling[i], 40, 40, "G"), item=items[i]) for i in IDS)
    pins = (f"{spelling['A 1']}.e", f"{spelling['B 1']}.e", f"{spelling['B 2']}.e")
    return PlacementProblem(Size(150, 200), syms, (net("n", *pins),), Facts(), Hints())


def _pages(spelling: Mapping[str, str]) -> set[frozenset[str]]:
    """The symbols of each page, named by the first spelling (the cut's columns are `c:<sym>`)."""
    back = {new: old for old, new in spelling.items()}
    result = cut_of(_cut_problem(spelling), OPTIONS)
    return {frozenset(back[c.removeprefix("c:").split("#")[0]] for r in p.rows for c in r.columns) for p in result.spec.pages}


def test_the_four_symbols_page_in_two_pages_of_two_whatever_they_are_named() -> None:
    """Baseline: exactly one split fits, so two pages of two columns, in either spelling."""
    for spelling in ({i: i for i in IDS}, SWAP):
        pages = _pages(spelling)
        assert sorted(len(p) for p in pages) == [2, 2], spelling


@pytest.mark.rule("RANK-INVARIANCE")
def test_swapping_two_symbol_ids_leaves_the_cut_as_it_was() -> None:
    """The start order of `_search` is the id text: A 1 and A 2 swapped moves the split."""
    assert _pages({i: i for i in IDS}) == _pages(SWAP)


PINS = {  # four single-pin symbols; the p link and the q link have the same bounding box
    "p0": (56, 24, "W"),
    "p1": (32, 72, "W"),
    "q0": (16, 72, "W"),
    "q1": (40, 24, "E"),
}


def _routed(first: str, second: str, links: tuple[str, ...] = ("p", "q")) -> dict[str, str]:
    """Route page with the p link named `first` and the q link `second`: {physical link: net id}.

    Only the nets that got a wire are returned.
    """
    names = {"p": first, "q": second}
    pins = {k: v for k, v in PINS.items() if k[0] in links}
    env = link_env(pins, {names[k]: (f"{k}0", f"{k}1") for k in links}, OPTIONS)
    page, _refused, _findings = route_page(env)
    drawn = {w.net for w in page.wires}
    return {k: names[k] for k in links if names[k] in drawn}


def test_each_link_routes_alone() -> None:
    """Baseline: neither link needs the other's room, so each gets a wire when alone."""
    assert _routed("a", "b", ("p",)) == {"p": "a"}
    assert _routed("a", "b", ("q",)) == {"q": "b"}


@pytest.mark.rule("RANK-INVARIANCE")
def test_both_links_route_whichever_net_id_sorts_first() -> None:
    """Equal bounding boxes tie, the id text decides who routes first, and the other is refused."""
    for first, second in (("a", "b"), ("b", "a")):
        assert sorted(_routed(first, second)) == ["p", "q"], (first, second)
