"""What one page's x and y need: its plan, placed columns, blocks and the cut's facts."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from .cut_drawn import cut_stands
from .errors import CoreError
from .hang_build import fold_page, page_owners
from .pack import Attached, PlacedColumn, attachments, placed_columns
from .ref_kind import kind_of
from .values import RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .flow_values import Block, Column, CutResult, FlowGraph
    from .hangings import Hanging
    from .sym_values import Sym
    from .values import Options, Orientation, PagePlan, PlacementProblem, Ref


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
    refs: tuple[Ref, ...] = ()
    reserves: Mapping[tuple[str, str], int] = field(default_factory=dict)
    under: frozenset[tuple[str, str, str]] = frozenset()  # (fan, card, pin): an anchored pin the fan's trunk runs over (R510)
    hangings: Mapping[tuple[str, str, Orientation], tuple[Hanging, ...]] = field(
        default_factory=dict
    )  # (symbol, pin, orientation) -> the boxes the page draws at that pin; the fold reads them
    row_tags: frozenset[str] = frozenset()  # fan ids a row cut wraps: no trunk (layout-0529)
    bare: Mapping[str, Sym] = field(default_factory=dict)  # the symbols before the fold: a Placed shows their footprints, no hanging in them
    wraps: Mapping[str, tuple[tuple[int, int], ...]] = field(default_factory=dict)  # net -> (first, last) row of each row-wrap arrow on this page


def _wraps(refs: tuple[Ref, ...], page: int) -> dict[str, tuple[tuple[int, int], ...]]:
    """The rows each row-wrap arrow of this page spans, by net, from the cut's arrows (layout-0511)."""
    out: dict[str, list[tuple[int, int]]] = {}
    for r in refs:
        if kind_of(r) is RefKind.ARROW and (a := r.ends[0]).page == (b := r.ends[1]).page == page:
            if a.row is None or b.row is None:
                msg = f"arrow {r.net} on page {page} has an end with no row: the cut sets the row of every arrow end"
                raise CoreError(msg)
            if a.row < b.row:
                out.setdefault(r.net, []).append((a.row, b.row))
    return {n: tuple(v) for n, v in out.items()}


def _env(plan: PagePlan, cut: CutResult, problem: PlacementProblem, options: Options, attach: Attached) -> PageEnv:
    """The page's env: its symbols hold the page's hangings, so every stage reads one footprint."""
    plain = {s.id: s for s in problem.symbols}
    columns = {c.id: c for c in cut.flow.columns}
    blocks = {b.id: b for lst in cut.blocks for b in lst.blocks}
    owners = page_owners(plan, placed_columns(plan, columns, blocks, attach, plain), blocks)
    refs = cut.spec.reference_plan
    stands = cut_stands(problem, cut)
    hangings, syms = fold_page(plain, refs, problem, (plan.page, owners, stands), (cut.spec.leads, options))
    page = replace(problem, symbols=tuple(syms[s.id] for s in problem.symbols))
    pcs = placed_columns(plan, columns, blocks, attach, syms)
    in_row = frozenset(s.id for s in syms.values() if s.row_group)
    return PageEnv(
        plan,
        pcs,
        blocks,
        attach,
        syms,
        options,
        in_row,
        cut.flow,
        page,
        columns,
        refs,
        hangings=hangings,
        bare=plain,
        row_tags=cut.row_tags,
        wraps=_wraps(refs, plan.page),
    )


def page_envs(
    cut: CutResult,
    problem: PlacementProblem,
    options: Options,
    reserves: Mapping[tuple[str, str], int] | None = None,
) -> tuple[PageEnv, ...]:
    """One env per page of the cut, in order; the flow and blocks are the cut's own.

    reserves: a (left column, right column) pair to the tracks its gap holds (stage 7).
    """
    blocks = {b.id: b for lst in cut.blocks for b in lst.blocks}
    attach = attachments(cut.flow.columns, blocks)
    envs = (_env(plan, cut, problem, options, attach) for plan in cut.spec.pages)
    return tuple(replace(env, reserves=reserves or {}) for env in envs)
