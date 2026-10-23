"""Stage 2, blocks: cards, fans and columns per unit in group order (layout-0279).

A card is a box with the columns on its pins, a fan the free columns of one trunk, a column
stands alone. Two edges (E4) split a box's pins by halves; the columns a half cannot hold leave
the card as free blocks (CARD_OVERFULL). Every width is `row_width` of `one_row`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING

from .blocks_card import CardEdges, card_edges, overfull
from .blocks_check import box_findings
from .blocks_hints import apply_hints
from .blocks_members import (
    Env,
    attached_boxes,
    chain_boxes,
    draft_block,
    height_est,
    make_env,
    members,
)
from .keys import natural_key
from .pack_row import row_width
from .rowspec import one_row
from .values import BlockList

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .values import Block, Finding, FlowGraph, Options, PlacementProblem


def assign_blocks(
    flow: FlowGraph, problem: PlacementProblem, options: Options
) -> tuple[BlockList, ...]:
    """One BlockList per unit (one empty list for an empty flow), blocks in group order."""
    env = make_env(flow, problem, options)
    box_of = attached_boxes(flow)
    by_box: dict[str, list[str]] = defaultdict(list)
    for col, box in box_of.items():
        by_box[box].append(col)
    edges = {
        b: card_edges(b, cols, flow, problem, options)
        for b, cols in sorted(by_box.items(), key=lambda kv: natural_key(kv[0]))
    }
    spill = [c for e in edges.values() for c in e.spilled]
    blocks = [
        _sized(draft_block(m, edges.get(m.anchor or ""), env), env)
        for m in members(env, box_of, spill)
    ]
    notes = _notes(edges, by_box, blocks, env)
    units = sorted({b.unit for b in blocks}, key=natural_key) or [""]
    return tuple(
        _unit_list(u, [b for b in blocks if b.unit == u], notes.get(u, ()), env, spill)
        for u in units
    )


def _sized(block: Block, env: Env) -> Block:
    """The block with width_est from the row's own packing, height_est and short."""
    row = one_row(block.columns, (block,), env.flow, env.problem, env.options)
    height = height_est(block, env)
    short = height < env.options.short_height * env.problem.area.h
    return replace(block, width_est=row_width(row), height_est=height, short=short)


def _notes(
    edges: Mapping[str, CardEdges],
    by_box: Mapping[str, Sequence[str]],
    blocks: Sequence[Block],
    env: Env,
) -> dict[str, tuple[Finding, ...]]:
    """The findings of each unit: overfull cards, then drawn boxes held by other than one block."""
    notes = _overfull_notes(edges, by_box, env)
    cells = chain_boxes(env.flow)
    for f in box_findings([d for d in env.flow.drawn if d not in cells], env.syms, blocks):
        unit = _unit_of(f.subject or "", env)
        notes[unit] = (*notes.get(unit, ()), f)
    return notes


def _unit_of(sym: str, env: Env) -> str:
    return env.syms[sym].unit


def _overfull_notes(
    edges: Mapping[str, CardEdges], by_box: Mapping[str, Sequence[str]], env: Env
) -> dict[str, tuple[Finding, ...]]:
    notes: dict[str, list[Finding]] = defaultdict(list)
    for box, e in edges.items():
        if e.spilled:
            notes[_unit_of(box, env)].append(overfull(box, e.spilled, len(by_box[box])))
    return {u: tuple(fs) for u, fs in notes.items()}


def _unit_list(
    unit: str, blocks: Sequence[Block], notes: Sequence[Finding], env: Env, spill: Sequence[str]
) -> BlockList:
    """Group order, then natural key of the anchor or first column, then the authored hints.

    The spilled columns stand after the cards and the first starts a page (PAGE-CUT).
    """
    rank = env.rank
    ordered = sorted(
        blocks,
        key=lambda b: (rank.get(b.group or "", len(rank)), natural_key(b.anchor or b.columns[0])),
    )
    out, findings = apply_hints(ordered, env.problem.hints, env)
    out = _spilled_last(out, spill)
    return BlockList(unit, tuple(out), (*notes, *findings))


def _spilled_last(blocks: Sequence[Block], spill: Sequence[str]) -> list[Block]:
    """The blocks of spilled columns moved behind the rest, the first of them breaking the page."""
    gone = [b for b in blocks if set(b.columns) & set(spill)]
    kept = [b for b in blocks if b not in gone]
    return [*kept, *(replace(b, forced_break_before=i == 0) for i, b in enumerate(gone))]
