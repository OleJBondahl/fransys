"""Planted problems and gap readers for the stage 7 (widen) tests.

Builders take the page size as an argument where the size matters; the default is the cut AREA.
"""

from __future__ import annotations

from dataclasses import replace

from fransys_layout.core import Facts, Placement, PlacementProblem, Size

from .cut_fixtures import AREA, chain, elem, net
from .route_fixtures import two_links_one_gap

AREA_144W = Size(144, 854)
AREA_144X128 = Size(144, 128)
AREA_96W = Size(96, 854)


def gap_width(placement: Placement, gap_id: str, page: int = 1) -> int:
    """The width in G of the gap with this id on one page."""
    gap = next(g for pp in placement.pages if pp.page == page for g in pp.gaps if g.id == gap_id)
    return gap.x1 - gap.x0


def page_count(placement: Placement) -> int:
    """How many pages the placement holds."""
    return len(placement.pages)


def cross_link_through_gap(area: Size = AREA) -> PlacementProblem:
    """Two routed rings on one page whose cross-links share one 8 G gap."""
    return replace(two_links_one_gap(), area=area)


def overflowing_row(area: Size = AREA) -> PlacementProblem:
    """One element 8 G wider than the page, wired to a small one: the row overflows by one block."""
    wide = elem("wide", area.w + 8)
    return PlacementProblem(area, (wide, elem("e")), (net("w", "wide.s", "e.n"),), facts=Facts())


def tall_by_trunk_levels(area: Size = AREA_144X128) -> PlacementProblem:
    """Eight elements stacked in one column, too tall for the page, with no gap between columns."""
    names = [f"t{k}" for k in range(8)]
    return PlacementProblem(
        area,
        tuple(elem(k) for k in names),
        tuple(chain(names)),
        facts=Facts(),
    )
