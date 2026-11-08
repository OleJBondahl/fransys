"""Stage 5, place: place_pages(cut, problem, options) -> Placement of every page of the cut.

Per page the x of each row, then the y of the page, then the Placed symbols, gaps and trunks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .fold_page import refolded
from .outline import unit_hulls
from .outputs import Placement
from .place_assemble import assemble
from .place_env import page_envs
from .place_pairs import settled
from .place_x import place_x
from .place_y import place_y

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .flow_values import CutResult
    from .values import Finding, Options, PlacementProblem


def place_pages(
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    reserves: Mapping[tuple[str, str], int] | None = None,
) -> Placement:
    """Place every page; its findings come page by page, rows past the page then dropped aligns.

    reserves (stage 7): a (left column, right column) pair to the tracks its gap must hold.
    """
    stages, pages = [], []
    findings: list[Finding] = []
    for page in page_envs(cut, problem, options, reserves):
        x, wide = place_x(page)
        env = refolded(page, x)
        y, dropped = place_y(env, x)
        stages.append((env, x, y))
        pages.append(assemble(env, x, y, {f.subject for f in dropped}))
        findings.extend((*wide, *dropped))
    placement = Placement(tuple(settled(stages, pages)))
    outlines, room = unit_hulls(placement, problem, options)
    return Placement(placement.pages, (*findings, *room), outlines)
