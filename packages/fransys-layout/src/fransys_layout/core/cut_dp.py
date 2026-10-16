"""Stage 4, the cut: rows are lines and pages paragraphs, by a two-level dynamic program.

Exact for the block order it is given. A row's width is `cut_pack`'s (the width `row_width` gives
it); its height is an estimate. Rows after a page's first hold only short items (L7); no page is
under `min_fill` unless it is last or ends at a forced break; a page cut through a two-pin net is
P2. Nothing is refused: one item, or one whole block, is a row however wide, a page's first row
however tall (layout-0280); when `min_fill` cannot be met the cut is redone without it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .cut_costs import cut_cost
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .cut_costs import Boundary, Item
    from .values import Block, Options

INF = float("inf")


@dataclass(frozen=True, slots=True)
class Cut:
    """What the DP reads about one unit: its items, boundaries, blocks and the page."""

    seq: Sequence[Item]
    bounds: Sequence[Boundary]
    by_id: Mapping[str, Block]
    page_w: int
    page_h: int
    options: Options


@dataclass(frozen=True, slots=True)
class RowState:
    """Rows covering a prefix of a page: cost so far, height used, area filled, last row start."""

    cost: float
    height: int
    area: int
    start: int
    prev: RowState | None


Plan = list[tuple[int, int, RowState]]


def splits_block(seq: Sequence[Item], i: int, j: int) -> bool:
    """True when items i..j cut through a whole block at either end."""
    left = i > 0 and seq[i - 1].whole and seq[i - 1].block == seq[i].block
    right = j + 1 < len(seq) and seq[j].whole and seq[j + 1].block == seq[j].block
    return left or right


def row_size(cut: Cut, i: int, j: int) -> tuple[int, int]:
    """Width (the pack modules' own) and estimated height of items i..j in one row."""
    seq = cut.seq
    height = 0
    seen: set[str] = set()
    for item in seq[i : j + 1]:
        if not item.whole:
            height = max(height, item.height)
        elif item.block not in seen:
            seen.add(item.block)
            height = max(height, cut.by_id[item.block].height_est)
    return seq[j].at - seq[i].at + seq[i].lead + seq[j].tail, height


def _unbreakable(cut: Cut, i: int, j: int) -> bool:
    """One item, or the items of one whole block: a row however wide (layout-0280)."""
    first = cut.seq[i]
    return i == j or (first.whole and all(it.block == first.block for it in cut.seq[i : j + 1]))


def rows(cut: Cut, i: int) -> list[dict[int, RowState]]:
    """For page start i: the best row states for every end j, keyed by height used."""
    states: list[dict[int, RowState]] = [{} for _ in cut.seq]
    base = RowState(0.0, 0, 0, i, None)
    for j in range(i, len(cut.seq)):
        found: list[RowState] = []
        for s in range(j, i - 1, -1):
            fit = row_size(cut, s, j)
            if fit[0] > cut.page_w and not _unbreakable(cut, s, j):
                break
            if _refused(cut, i, s, j):
                continue
            for prev in [base] if s == i else states[s - 1].values():
                state = _extend(cut, (prev, s), fit)
                if state is not None:
                    found.append(state)
        states[j] = _by_height(found)
    return states


def _refused(cut: Cut, i: int, s: int, j: int) -> bool:
    """A row through a whole block, a shared lone-card row, or after a first not short (L7)."""
    if splits_block(cut.seq, s, j) or (j > s and any(it.own_row for it in cut.seq[s : j + 1])):
        return True
    return s > i and not all(it.short for it in cut.seq[s : j + 1])


def _by_height(found: Sequence[RowState]) -> dict[int, RowState]:
    """The cheapest state for each height used; the first found wins a tie."""
    best: dict[int, RowState] = {}
    for st in found:
        if st.height not in best or best[st.height].cost > st.cost:
            best[st.height] = st
    return best


def _extend(cut: Cut, row: tuple[RowState, int], fit: tuple[int, int]) -> RowState | None:
    """The row starting at row[1] after row[0]; a page's first row may overflow its height."""
    prev, s = row
    width, height = fit
    options = cut.options
    total = prev.height + height + (options.row_gap if prev.height else 0)
    if total > cut.page_h and prev.height:
        return None
    cost = prev.cost + options.w_row
    if prev.height:
        cost += cut_cost(cut.bounds[s - 1], options, page=False)
    return RowState(cost, total, prev.area + width * height, s, prev if prev.height else None)


def fill(state: RowState, cut: Cut) -> float:
    """The share of the page's area its rows fill: the one number min_fill and findings read."""
    return state.area / (cut.page_w * cut.page_h)


def _best_state(states: Mapping[int, RowState], cut: Cut, *, last: bool) -> RowState | None:
    chosen: RowState | None = None
    chosen_cost = INF
    for st in states.values():
        share = fill(st, cut)
        if share < cut.options.min_fill and not last:
            continue
        cost = st.cost + cut.options.w_f * (1 - share) ** 2
        if cost < chosen_cost:
            chosen, chosen_cost = replace(st, cost=cost), cost
    return chosen


Best = list[tuple[float, int, RowState | None]]


def _relax(best: Best, i: int, states: Sequence[Mapping[int, RowState]], cut: Cut) -> None:
    n = len(cut.seq)
    forced = {b for b in range(n - 1) if cut.seq[b + 1].forced_break_before}
    cost_in = cut_cost(cut.bounds[i - 1], cut.options, page=True) if i > 0 else 0.0
    for k in range(i, n):
        if k - 1 in forced and k > i:
            break
        state = _best_state(states[k], cut, last=k == n - 1 or k in forced)
        if state is None:
            continue
        total = best[i][0] + state.cost + cut.options.w_p + cost_in
        if total < best[k + 1][0]:
            best[k + 1] = (total, i, state)


def pages(cut: Cut) -> Plan | None:
    """Best page partition: (first, last, rows) per page, by F(k) = min F(i-1) + page(i, k) + w_p.

    None when no partition meets min_fill; the caller redoes the cut without it.
    """
    n = len(cut.seq)
    best: Best = [(INF, -1, None)] * (n + 1)
    best[0] = (0.0, -1, None)
    for i in range(n):
        if best[i][0] < INF:
            _relax(best, i, rows(cut, i), cut)
    return _unwind(best, n)


def _unwind(best: Best, n: int) -> Plan | None:
    out: Plan = []
    k = n
    while k > 0:
        _, i, state = best[k]
        if state is None:
            return None
        out.append((i, k - 1, state))
        k = i
    return out[::-1]


def cut_unit(cut: Cut) -> tuple[Plan, bool]:
    """The page plan, and whether min_fill had to be given up to place every item."""
    plan = pages(cut)
    if plan is not None:
        return plan, False
    relaxed = replace(cut, options=replace(cut.options, min_fill=0.0))
    return pages(relaxed) or [], True


def first_row(state: RowState) -> RowState:
    """The state of a page's first row."""
    while state.prev is not None:
        state = state.prev
    return state


def _thin_page(cut: Cut, unit: str, i: int, share: float, page: int) -> Finding:
    block = cut.seq[i].block
    floor = cut.options.min_fill
    text = (
        f"unit {unit}, block {block}: page filled {share:.0%} (below min_fill {floor:.0%}): "
        "the cut kept the block whole; lower min_fill or split the unit"
    )
    return Finding("FILL_UNDER_MIN", text, page, block)


def page_findings(
    cut: Cut, plan: Plan, first: int, unit: str, *, relaxed: bool
) -> tuple[Finding, ...]:
    """PAGE_OVERFLOW for a first row taller than the page, FILL_UNDER_MIN for a thin page kept."""
    out: list[Finding] = []
    for p, (i, k, state) in enumerate(plan):
        block = cut.seq[first_row(state).start].block
        if first_row(state).height > cut.page_h:
            text = f"{block}: a row {first_row(state).height} G high on a page {cut.page_h} G high"
            out.append(Finding("PAGE_OVERFLOW", text, first + p, block))
        last = k == len(cut.seq) - 1 or cut.seq[k + 1].forced_break_before
        if relaxed and not last and fill(state, cut) < cut.options.min_fill:
            out.append(_thin_page(cut, unit, i, fill(state, cut), first + p))
    return tuple(out)
