"""Stage 5, place: place_pages(cut, problem, options) -> Placement of every page of the cut.

Per page the x of each row, then the y of the page, then the Placed symbols, gaps and trunks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .outputs import Placement
from .place_assemble import assemble
from .place_env import page_envs
from .place_x import place_x
from .place_y import place_y

if TYPE_CHECKING:
    from .values import CutResult, Finding, Options, PlacementProblem


def place_pages(cut: CutResult, problem: PlacementProblem, options: Options) -> Placement:
    """Place every page; its findings come page by page, rows past the page then dropped aligns."""
    pages = []
    findings: list[Finding] = []
    for env in page_envs(cut, problem, options):
        x, wide = place_x(env)
        y, dropped = place_y(env, x)
        pages.append(assemble(env, x, y))
        findings.extend((*wide, *dropped))
    return Placement(tuple(pages), tuple(findings))
