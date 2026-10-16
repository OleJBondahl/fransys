"""What one page's x and y need: its plan, placed columns, blocks and the cut's facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pack import Attached, PlacedColumn, attachments, placed_columns

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .values import (
        Block,
        Column,
        CutResult,
        FlowGraph,
        Options,
        PagePlan,
        PlacementProblem,
        Sym,
    )


@dataclass(frozen=True, slots=True)
class PageEnv:
    """Everything a page's x and y read, so no function takes more than five parameters."""

    plan: PagePlan
    pcs: Mapping[str, PlacedColumn]
    blocks: Mapping[str, Block]
    attach: Attached
    syms: Mapping[str, Sym]
    options: Options
    in_row: frozenset[str]
    flow: FlowGraph
    problem: PlacementProblem
    columns: Mapping[str, Column]


def _env(
    plan: PagePlan, cut: CutResult, problem: PlacementProblem, options: Options, attach: Attached
) -> PageEnv:
    syms = {s.id: s for s in problem.symbols}
    columns = {c.id: c for c in cut.flow.columns}
    blocks = {b.id: b for lst in cut.blocks for b in lst.blocks}
    pcs = placed_columns(plan, columns, blocks, attach, syms)
    in_row = frozenset(s.id for s in syms.values() if s.row_group)
    return PageEnv(plan, pcs, blocks, attach, syms, options, in_row, cut.flow, problem, columns)


def page_envs(cut: CutResult, problem: PlacementProblem, options: Options) -> tuple[PageEnv, ...]:
    """One env per page of the cut, in order; the flow and blocks are the cut's own."""
    blocks = {b.id: b for lst in cut.blocks for b in lst.blocks}
    attach = attachments(cut.flow.columns, blocks)
    return tuple(_env(plan, cut, problem, options, attach) for plan in cut.spec.pages)
