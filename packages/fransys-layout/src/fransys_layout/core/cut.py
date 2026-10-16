"""Stage 4, the cut: `cut_pages` puts a unit's blocks on rows and pages (layout-0280).

The DP is `cut_dp`'s, the references and findings `cut_refs`'s, the tall-column fold `cut_tall`'s;
this module runs them per unit and writes the page plans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .cut_costs import boundaries, positions, sequence
from .cut_dp import Cut, cut_unit, page_findings
from .cut_ends import ref_pins
from .cut_guard import unplaced
from .cut_refs import (
    copies,
    copyable_fans,
    head_off_legs,
    on_pages,
    references,
    spilled,
    stubs,
)
from .cut_tall import split_tall
from .values import CutResult, PagePlan, PageSpec, RowPlan

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from .cut_costs import Item
    from .cut_dp import Plan, RowState
    from .values import BlockList, Finding, FlowGraph, Options, PlacementProblem, Ref


@dataclass(slots=True)
class Done:
    """What the units cut so far have produced; pages are numbered across units."""

    pages: list[PagePlan]
    refs: list[Ref]
    findings: list[Finding]
    where: dict[str, int]


def cut_pages(
    blocks: tuple[BlockList, ...],
    flow: FlowGraph,
    problem: PlacementProblem,
    options: Options,
) -> CutResult:
    """The page plans of every unit, the planned references and the findings."""
    flow, blocks, folds = split_tall(flow, blocks, problem, options)
    copyable = copyable_fans(flow, problem)
    done = Done([], [], [], {})
    for unit in blocks:
        _cut_unit(unit, (flow, problem, options), copyable, done)
    for c in flow.columns:
        for cell in (cell for lane in c.lanes for cell in lane.cells):
            done.where.setdefault(cell.sym, done.where[c.id])
    where = done.where
    refs = [
        *(on_pages(r, where) for r in folds),
        *done.refs,
        *spilled(blocks, flow, where, problem),
        *copies(flow, where, copyable),
        *stubs(problem, where),
    ]
    findings = (
        *done.findings,
        *head_off_legs(flow, where),
        *unplaced(blocks, done.pages, flow),
    )
    return CutResult(PageSpec(tuple(done.pages), tuple(refs), findings), flow, blocks)


def plan_unit(
    unit: BlockList,
    env: tuple[FlowGraph, PlacementProblem, Options],
    copyable: frozenset[str],
) -> tuple[Cut, Plan, bool]:
    """The unit's DP input, its page plan, and whether min_fill was given up."""
    flow, problem, options = env
    page_w = problem.area.w - 2 * options.margin.w
    page_h = problem.area.h - 2 * options.margin.h
    seq = sequence(unit, flow, problem, options, page_h)
    by_id = {b.id: b for b in unit.blocks}
    cut = Cut(seq, boundaries(seq, flow, by_id, copyable), by_id, page_w, page_h, options)
    plan, relaxed = cut_unit(cut)
    return cut, plan, relaxed


def _cut_unit(
    unit: BlockList,
    env: tuple[FlowGraph, PlacementProblem, Options],
    copyable: frozenset[str],
    done: Done,
) -> None:
    cut, plan, relaxed = plan_unit(unit, env, copyable)
    first = len(done.pages) + 1
    page_of = {q: first + p for p, (i, k, _) in enumerate(plan) for q in range(i, k + 1)}
    done.pages.extend(_page_plans(unit, cut, plan, first))
    pins = ref_pins(env[0], positions(cut.seq, cut.by_id))
    done.refs.extend(references(cut, plan, page_of, copyable, pins))
    done.findings.extend(page_findings(cut, plan, first, unit.unit, relaxed=relaxed))
    done.where.update({n: page_of[i] for n, i in positions(cut.seq, cut.by_id).items()})


def _distinct(ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(ids))


def _rows_of(seq: Sequence[Item], state: RowState, end: int) -> tuple[RowPlan, ...]:
    """The rows of a page, first to last, from its last row's state."""
    rows: list[RowPlan] = []
    st: RowState | None = state
    while st is not None:
        items = seq[st.start : end + 1]
        height = st.height - (st.prev.height if st.prev else 0)
        columns = tuple(it.column for it in items if not it.bare)
        rows.append(RowPlan(columns, _distinct(it.block for it in items), height))
        end, st = st.start - 1, st.prev
    return tuple(reversed(rows))


def _page_plans(unit: BlockList, cut: Cut, plan: Plan, first: int) -> list[PagePlan]:
    seq = cut.seq
    out = []
    for p, (i, k, state) in enumerate(plan):
        forced = k == len(seq) - 1 or seq[k + 1].forced_break_before
        blocks = _distinct(it.block for it in seq[i : k + 1])
        groups = _distinct(g for g in (cut.by_id[b].group for b in blocks) if g)
        out.append(PagePlan(first + p, unit.unit, _rows_of(seq, state, k), forced, groups))
    return out
