"""Stage 2 members: the columns of a card, a fan or a column block, and their group (layout-0279).

A block's id is made once from its kind and anchor or first column and is never read back; a
`Member` carries the box and the fan it stands on, so nothing here parses an id.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .blocks_card import box_pin, pin_order
from .keys import natural_key
from .unionfind import UnionFind
from .values import Block

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .blocks_card import CardEdges
    from .values import BlockKind, Column, Fan, FlowGraph, Options, PlacementProblem, Sym


@dataclass(frozen=True, slots=True)
class Env:
    """The lookups every stage 2 helper reads, built once per call."""

    flow: FlowGraph
    problem: PlacementProblem
    options: Options
    syms: Mapping[str, Sym]
    columns: Mapping[str, Column]
    col_group: Mapping[str, str | None]
    rank: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Member:
    """What one block stands on: a box, a fan or neither, and its columns in block order."""

    kind: BlockKind
    anchor: str | None
    fan: str | None
    cols: tuple[str, ...]


@dataclass(slots=True)
class _Acc:
    boxes: list[str] = field(default_factory=list)
    fans: list[str] = field(default_factory=list)
    cols: list[str] = field(default_factory=list)


def make_env(flow: FlowGraph, problem: PlacementProblem, options: Options) -> Env:
    syms = {s.id: s for s in problem.symbols}
    return Env(
        flow,
        problem,
        options,
        syms,
        {c.id: c for c in flow.columns},
        {c.id: column_group(c, syms) for c in flow.columns},
        {g: i for i, g in enumerate(problem.hints.group_order)},
    )


def column_group(column: Column, syms: Mapping[str, Sym]) -> str | None:
    """The most frequent group of the column's symbols; a tie goes to the foot symbol's group."""
    cells = (syms[c.sym].group for lane in column.lanes for c in lane.cells)
    votes = Counter(g for g in cells if g)
    if not votes:
        return None
    best = max(votes.values())
    foot = syms[column.lanes[0].cells[-1].sym].group
    if votes.get(foot) == best:
        return foot
    return min((g for g, n in votes.items() if n == best), key=natural_key)


def attached_boxes(flow: FlowGraph) -> dict[str, str]:
    """Column to the box whose pin its head or foot meets, the first found."""
    out: dict[str, str] = {}
    for c in flow.columns:
        for end in (*c.heads, *c.feet):
            if end.kind == "boxpin" and end.pin is not None:
                out.setdefault(c.id, end.pin.sym)
    return out


def _free_columns(fan: Fan, box_of: Mapping[str, str]) -> list[str]:
    """The columns of a fan that hang on no box, in the fan's order."""
    found = (a.column for a in (*fan.drivers, *fan.legs) if a.column and a.column not in box_of)
    return list(dict.fromkeys(found))


def _unite(
    box_of: Mapping[str, str], spill: Sequence[str], live: Sequence[tuple[Fan, list[str]]]
) -> UnionFind:
    uf = UnionFind()
    for col, box in box_of.items():
        if col not in spill:
            uf.union(f"box:{box}", f"col:{col}")
    for fan, free in live:
        for col in free:
            uf.union(f"fan:{fan.id}", f"col:{col}")
    return uf


def members(env: Env, box_of: Mapping[str, str], spill: Sequence[str]) -> list[Member]:
    """Union attached columns with their box, and a fan's free columns with the fan.

    A spilled column joins no box and, being in box_of, no fan: it stands alone.
    """
    live = [(f, _free_columns(f, box_of)) for f in env.flow.fans]
    uf = _unite(box_of, spill, live)
    acc: dict[str, _Acc] = {}
    for box in sorted(set(box_of.values()), key=natural_key):
        acc.setdefault(uf.find(f"box:{box}")[0], _Acc()).boxes.append(box)
    for fan, free in live:
        if free:
            acc.setdefault(uf.find(f"fan:{fan.id}")[0], _Acc()).fans.append(fan.id)
    for c in env.flow.columns:
        acc.setdefault(uf.find(f"col:{c.id}")[0], _Acc()).cols.append(c.id)
    return [*(_member(a, env) for a in acc.values()), *_free_boxes(env, box_of)]


def chain_boxes(flow: FlowGraph) -> set[str]:
    """The boxes that are cells of a chain column: the column's block holds them (layout-0289)."""
    return {c.sym for col in flow.columns if col.is_chain for c in col.lanes[0].cells}


def _free_boxes(env: Env, box_of: Mapping[str, str]) -> list[Member]:
    """A card with no columns for each drawn box no column meets: the empty case of a card.

    A box that is a cell of a chain column is held by that column's block (layout-0289).
    """
    held = set(box_of.values()) | chain_boxes(env.flow)
    free = (s for s in env.flow.drawn if env.syms[s].box is not None and s not in held)
    return [Member("card", s, None, ()) for s in sorted(free, key=natural_key)]


def _member(acc: _Acc, env: Env) -> Member:
    if acc.boxes:
        box = min(acc.boxes, key=natural_key)
        spec = env.syms[box].box
        cols = pin_order(acc.cols, env.columns, spec) if spec else sorted(acc.cols, key=natural_key)
        return Member("card", box, None, tuple(cols))
    cols = tuple(sorted(acc.cols, key=natural_key))
    if acc.fans:
        return Member("fan", None, min(acc.fans, key=natural_key), cols)
    return Member("column", None, None, cols)


def block_group(m: Member, env: Env) -> str | None:
    """A card takes its box's group; a fan the majority of its legs (L2); a column its own."""
    if m.anchor is not None:
        return env.syms[m.anchor].group
    fan = next((f for f in env.flow.fans if f.id == m.fan), None)
    if fan is not None:
        legs = (env.col_group.get(a.column or "") for a in fan.legs if a.column)
        votes = Counter(g for g in legs if g)
        if votes:
            best = max(votes.values())
            return min(
                (g for g, n in votes.items() if n == best),
                key=lambda g: (env.rank.get(g, len(env.rank)), natural_key(g)),
            )
    return env.col_group.get(m.cols[0]) if m.cols else None


def block_unit(m: Member, env: Env) -> str:
    """A card is in its box's unit, any other block in the unit of its first symbol."""
    if m.anchor is not None:
        return env.syms[m.anchor].unit
    return env.syms[env.columns[m.cols[0]].lanes[0].cells[0].sym].unit


def draft_block(m: Member, edges: CardEdges | None, env: Env) -> Block:
    """The block of a member with its estimates left at 0; blocks.py measures them."""
    fan = next((f for f in env.flow.fans if f.id == m.fan), None)
    keep_whole = (
        m.kind == "card"
        or (fan is not None and fan.lanes > 1)
        or any(len(env.columns[c].lanes) > 1 for c in m.cols)
    )
    return Block(
        f"{m.kind}:{m.anchor or m.cols[0]}",
        m.kind,
        block_unit(m, env),
        m.cols,
        m.anchor,
        m.fan,
        block_group(m, env),
        0,
        0,
        short=False,
        keep_whole=keep_whole,
        forced_break_before=False,
        seat="none",
        pin_edges=edges.pin_edges if edges else (),
    )


def height_est(block: Block, env: Env) -> int:
    """A card: the box body plus, per edge, its tallest column and a wire; else the tallest column.

    A fan adds two trunk lanes' worth of grid.
    """
    o = env.options
    if block.kind == "card" and block.anchor is not None:
        edge_of = dict(block.pin_edges)
        tall: dict[str, int] = {}
        for c in block.columns:
            edge = edge_of.get(box_pin(env.columns[c]) or "", "S")
            tall[edge] = max(tall.get(edge, 0), env.columns[c].height)
        return env.syms[block.anchor].body.h + sum(h + o.wire_min for h in tall.values())
    fan = next((f for f in env.flow.fans if f.id == block.fan), None)
    return max(env.columns[c].height for c in block.columns) + (
        fan.lanes * o.wiring_grid * 2 if fan else 0
    )
