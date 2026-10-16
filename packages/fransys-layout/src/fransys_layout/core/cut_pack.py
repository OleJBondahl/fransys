"""Stage 4's left-pack of a unit: where each column stands in one row (layout-0280).

Every number comes from the pack modules: a run of free columns sits `separation` apart, a card
is `row_width` of its own row, and two segments meet at `join_gap`. Items i..j of a unit then
measure `at[j] - at[i] + lead[i] + tail[j]`, the width `row_width` gives the same row.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from .pack_row import extent, join_gap, row_width, segments
from .pack_sep import separation
from .rowspec import one_row

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .pack_row import RowSpec
    from .values import BlockList, FlowGraph, Options, PlacementProblem


class Pack(NamedTuple):
    """A column's x in the unit's one-row left-pack, with its reach to the left and the right."""

    at: int
    lead: int
    tail: int


class Edge(NamedTuple):
    """The right end of the segments so far: its x and the reach past it."""

    x: int
    reach: int


def left_pack(
    unit: BlockList, flow: FlowGraph, problem: PlacementProblem, options: Options
) -> dict[str, Pack]:
    """Pack of every column of the unit's blocks, taken in block order."""
    cols = tuple(c for b in unit.blocks for c in b.columns)
    spec = one_row(cols, unit.blocks, flow, problem, options)
    out: dict[str, Pack] = {}
    edge: Edge | None = None
    for block, here in segments(cols, unit.blocks):
        bare = block is not None and not here and block.seat != "none"
        if not here and not bare:
            continue
        if block is None:
            packs, edge = _run(spec, here, edge)
        else:
            width = row_width(one_row(here, (block,), flow, problem, options))
            packs, edge = _card(spec, here or [block.anchor or ""], width, edge)
        out.update(packs)
    return out


def _start(edge: Edge | None, left_reach: int, spec: RowSpec) -> int:
    """The x of a segment's entry node: after the previous segment's join, else at its own reach."""
    return left_reach if edge is None else edge.x + join_gap(edge.reach, left_reach, spec.options)


def _run(spec: RowSpec, here: Sequence[str], edge: Edge | None) -> tuple[dict[str, Pack], Edge]:
    """A run of free columns, each `separation` after the one before."""
    lead = -extent(spec, here[0])[0]
    x = _start(edge, lead, spec)
    packs: dict[str, Pack] = {}
    prev: str | None = None
    for col in here:
        if prev is not None:
            x += separation(spec.pcs[prev], spec.pcs[col], spec.syms, spec.in_row, spec.options)
        lo, hi = extent(spec, col)
        packs[col] = Pack(x, -lo, hi)
        prev = col
    return packs, Edge(x, packs[here[-1]].tail)


def _card(
    spec: RowSpec, here: Sequence[str], width: int, edge: Edge | None
) -> tuple[dict[str, Pack], Edge]:
    """A card is one segment as wide as its own row; its columns share its left edge."""
    x = _start(edge, 0, spec)
    return {c: Pack(x, 0, width) for c in here}, Edge(x + width, 0)
