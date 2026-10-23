"""Stage 5, place: place_pages(cut, problem, options) -> Placement of every page of the cut.

Per page the x of each row, then the y of the page, then the Placed symbols, gaps and trunks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .marker_flags import with_rooms
from .outputs import Placement
from .place_assemble import assemble, placed_rooms
from .place_env import page_envs
from .place_x import place_x
from .place_y import place_y

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .values import CutResult, Finding, Options, PlacementProblem


def place_pages(
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    reserves: Mapping[tuple[str, str], int] | None = None,
) -> Placement:
    """Place every page; its findings come page by page, rows past the page then dropped aligns.

    reserves (stage 7): a (left column, right column) pair to the tracks its gap must hold.
    """
    pages = []
    findings: list[Finding] = []
    for bare in page_envs(cut, problem, options, reserves):
        x, wide = place_x(bare)
        env = with_rooms(bare, x, placed_rooms(bare, x))
        y, dropped = place_y(env, x)
        pages.append(assemble(env, x, y))
        findings.extend((*wide, *dropped))
    return Placement(tuple(pages), tuple(findings))
