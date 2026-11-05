"""Planted problems and gap readers for the stage 7 (widen) tests.

Builders take the page size as an argument where the size matters; the default is the cut AREA.
"""

from __future__ import annotations

from fransys_layout.core import Facts, Placement, PlacementProblem, Size

from .cut_fixtures import AREA, elem, net


def gap_width(placement: Placement, gap_id: str, page: int = 1) -> int:
    """The width in G of the gap with this id on one page."""
    gap = next(g for pp in placement.pages if pp.page == page for g in pp.gaps if g.id == gap_id)
    return gap.x1 - gap.x0


def overflowing_row(area: Size = AREA) -> PlacementProblem:
    """One element 8 G wider than the page, wired to a small one: the row overflows by one block."""
    wide = elem("wide", area.w + 8)
    return PlacementProblem(area, (wide, elem("e")), (net("w", "wide.s", "e.n"),), facts=Facts())
