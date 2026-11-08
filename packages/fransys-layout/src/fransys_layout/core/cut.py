"""Stage 4, the cut: `cut_pages` puts a unit's blocks on rows and pages (layout-0280).

The DP is `cut_dp`'s, the references and findings `cut_refs`'s, the tall-column fold `cut_tall`'s;
this module runs them per unit and writes the page plans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .blocks_members import make_env
from .cut_costs import boundaries, column_items, positions
from .cut_dp import Cut, cut_unit, page_findings
from .cut_ends import ref_pins
from .cut_guard import unplaced
from .cut_ledger import account, copies
from .cut_measured import Measured, measured_blocks, row_key, with_legs
from .cut_pack import left_pack
from .cut_refs import across, copyable_fans, head_off_legs, on_pages, references, row_tags, spilled, tag_links
from .cut_tall import split_tall
from .flow_values import CutResult
from .values import PagePlan, PageSpec, RowPlan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .blocks_members import Env
    from .cut_costs import Item
    from .cut_dp import Plan, RowState
    from .flow_values import BlockList, FlowGraph
    from .values import Finding, Options, PlacementProblem, Ref


@dataclass(slots=True)
class Done:
    """What the units cut so far have produced; pages are numbered across units."""

    pages: list[PagePlan]
    refs: list[Ref]
    tags: set[str]
    findings: list[Finding]
    where: dict[str, int]


def cut_pages(
    blocks: tuple[BlockList, ...],
    flow: FlowGraph,
    problem: PlacementProblem,
    options: Options,
    measured: Measured | None = None,
) -> CutResult:
    """The page plans of every unit, the planned references and the findings.

    measured (stage 7): reserves and block heights read off a placement, in place of estimates.
    """
    flow, blocks, folds = split_tall(flow, blocks, problem, options)
    blocks = with_legs(blocks, measured.arrows) if measured else blocks
    copyable = copyable_fans(flow, problem)
    done = Done([], [], set(), [], {})
    for unit in blocks:
        _cut_unit(unit, (flow, problem, options), copyable, done, measured)
    for c in flow.columns:
        for cell in (cell for lane in c.lanes for cell in lane.cells):
            done.where.setdefault(cell.sym, done.where[c.id])
    where = done.where
    copied = copies(flow, where, copyable)
    tagged = across(flow, where, done.refs, problem.nets)
    flow = tag_links(flow, tagged)
    planned = [*(on_pages(r, where) for r in folds), *done.refs, *spilled(blocks, flow, where, problem), *tagged, *copied]
    ledger = account(problem, flow, where, planned, done.pages)
    refs = [*planned, *ledger.refs]
    findings = (
        *done.findings,
        *head_off_legs(flow, where),
        *unplaced(blocks, done.pages, problem.area.w - 2 * options.margin.w, options),
    )
    return CutResult(
        PageSpec(tuple(done.pages), tuple(refs), findings, drawn=ledger.ink, stubbed=ledger.stubbed, leads=ledger.leads, unjoined=ledger.unjoined),
        flow,
        blocks,
        frozenset(done.tags),
    )


def plan_unit(
    unit: BlockList,
    env: tuple[FlowGraph, PlacementProblem, Options],
    copyable: frozenset[str],
    measured: Measured | None = None,
) -> tuple[Cut, Plan, bool]:
    """The unit's DP input, its page plan, and whether min_fill was given up."""
    flow, problem, options = env
    page_w = problem.area.w - 2 * options.margin.w
    page_h = problem.area.h - options.page_headroom
    reserves = measured.reserves if measured else None
    seq = column_items(unit, flow, options, left_pack(unit, flow, problem, options, reserves), page_h)
    by_id = {b.id: b for b in unit.blocks}
    if measured:
        seq, by_id = measured_blocks(seq, by_id, measured, options.short_height * page_h)
    cut = Cut(
        seq,
        boundaries(seq, flow, by_id, copyable),
        by_id,
        page_w,
        page_h,
        options,
        measured.arrows if measured else {},
        measured.rows if measured else {},
    )
    plan, relaxed = cut_unit(cut)
    return cut, plan, relaxed


def _cut_unit(
    unit: BlockList,
    env: tuple[FlowGraph, PlacementProblem, Options],
    copyable: frozenset[str],
    done: Done,
    measured: Measured | None = None,
) -> None:
    cut, plan, relaxed = plan_unit(unit, env, copyable, measured)
    first = len(done.pages) + 1
    page_of = {q: first + p for p, (i, k, _) in enumerate(plan) for q in range(i, k + 1)}
    done.pages.extend(_page_plans(unit, cut, plan, first, make_env(*env)))
    pins = ref_pins(env[0], positions(cut.seq, cut.by_id))
    done.refs.extend(references(cut, plan, page_of, copyable, pins))
    done.tags |= row_tags(cut, plan, env[0])
    done.findings.extend(page_findings(cut, plan, first, unit.unit, relaxed=relaxed))
    done.where.update({n: page_of[i] for n, i in positions(cut.seq, cut.by_id).items()})


def _rows_of(seq: Sequence[Item], state: RowState, end: int) -> tuple[RowPlan, ...]:
    """The rows of a page, first to last, from its last row's state."""
    rows: list[RowPlan] = []
    st: RowState | None = state
    while st is not None:
        items = seq[st.start : end + 1]
        rows.append(RowPlan(*row_key(items)))
        end, st = st.start - 1, st.prev
    return tuple(reversed(rows))


def _drawn_groups(items: Sequence[Item], cut: Cut, env: Env) -> tuple[str, ...]:
    """The groups of every symbol drawn on a page and of its blocks' own symbols, in the authored order of `env.rank`."""
    cells = (c.sym for it in items if not it.bare for lane in env.columns[it.column].lanes for c in lane.cells)
    groups = dict.fromkeys((*(env.syms[s].group for s in cells), *(cut.by_id[it.block].group for it in items)))
    return (*(g for g in env.rank if g in groups), *(g for g in groups if g and g not in env.rank))


def _page_plans(unit: BlockList, cut: Cut, plan: Plan, first: int, env: Env) -> list[PagePlan]:
    """A page's groups are those of every symbol drawn on it, in authored order (R1344, R1360, R1361)."""
    seq = cut.seq
    return [PagePlan(first + p, unit.unit, _rows_of(seq, state, k), _drawn_groups(seq[i : k + 1], cut, env)) for p, (i, k, state) in enumerate(plan)]
