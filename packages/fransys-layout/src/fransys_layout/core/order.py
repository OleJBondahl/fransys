"""Stage 3, column order (L6), design 4.3: the order of a block's columns that cuts interleaving.

A card keeps the pin order of its box pins and a chain-fixed block keeps its columns. Any other
block is ordered by a cost over its spans (the columns one fan or one cross-link touches):
interleaving span pairs, foreign columns inside a span's reach, columns between a cross-link's
ends. A median sweep and swaps of any two columns give an order first. Up to
`options.exact_order_limit` columns, branch and bound (`order_search`) then looks for a better one
and stops after `options.exact_order_nodes` nodes, so the answer is never worse than the sweep's.
The columns stand in natural order and natural order wins every tie. A fan block puts its driver
first and a bundle's legs keep lane order. The stage reads no symbol kind and no id text beyond
`natural_key`.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
from typing import TYPE_CHECKING

from .keys import natural_key
from .order_bare import seat_bare_cards
from .order_search import exact_search

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .order_search import Before, Span
    from .values import Block, BlockList, Column, FlowGraph, Options

SWEEP_PASSES = 24
MIN_SPAN = 2  # a span of one column costs nothing


def order_blocks(
    blocks: tuple[BlockList, ...], flow: FlowGraph, options: Options
) -> tuple[BlockList, ...]:
    """Every block with its columns ordered, then each column-less card seated (layout-0288)."""
    return tuple(
        seat_bare_cards(
            replace(bl, blocks=tuple(order_columns(b, flow, options) for b in bl.blocks)), flow
        )
        for bl in blocks
    )


def order_columns(block: Block, flow: FlowGraph, options: Options) -> Block:
    """A card keeps its pin order and a chain-fixed block its columns; the rest is searched."""
    if block.kind == "card":
        cols = _pin_order(block, flow)
    elif block.fixed_order:
        cols = list(block.columns)
    else:
        cols = _search(block, flow, options)
    return replace(block, columns=tuple(cols))


def order_cost(order: Sequence[str], flow: FlowGraph) -> int:
    """The design's cost of one order of a block's columns, counting every span."""
    return _cost(order, _spans(order, flow))


def _search(block: Block, flow: FlowGraph, options: Options) -> list[str]:
    natural = sorted(block.columns, key=natural_key)
    before = _precedence(natural, block, flow, options)
    start = _extend(natural, before)
    # a span of every column costs every order alike
    spans = [s for s in _spans(start, flow) if len(s[0]) < len(start)]
    if not spans:
        return start
    sweep = _sweep(start, spans, before)
    if len(start) > options.exact_order_limit:
        return sweep
    seed = (sweep, _cost(sweep, spans))
    return exact_search(natural, spans, before, seed, options.exact_order_nodes)


def _spans(cols: Sequence[str], flow: FlowGraph) -> list[Span]:
    here = set(cols)
    ends = [(f.drivers + f.legs) for f in flow.fans]
    found = [(frozenset(a.column for a in e if a.column in here), False) for e in ends]
    found += [
        (frozenset(a.column for a in x.ends if a.column in here), True) for x in flow.cross_links
    ]
    return [s for s in found if len(s[0]) >= MIN_SPAN]


def _cost(order: Sequence[str], spans: Sequence[Span]) -> int:
    pos = {c: i for i, c in enumerate(order)}
    cost = 0
    reach = []
    for members, link in spans:
        at = [pos[c] for c in members]
        lo, hi = min(at), max(at)
        cost += hi - lo + 1 - len(members) + (hi - lo - 1 if link else 0)
        reach.append((lo, hi))
    for i, (a0, a1) in enumerate(reach):
        for b0, b1 in reach[i + 1 :]:
            cost += int(a0 < b0 <= a1 < b1 or b0 < a0 <= b1 < a1)
    return cost


def _sweep(start: Sequence[str], spans: Sequence[Span], before: Before) -> list[str]:
    """Median passes between spans and columns, the best order kept, then swaps of two columns."""
    order = start
    best, best_cost = start, _cost(start, spans)
    for _ in range(SWEEP_PASSES):
        nxt = _median_pass(order, spans, before)
        if nxt == order:
            break
        order = nxt
        cost = _cost(order, spans)
        if cost < best_cost:
            best, best_cost = order, cost
    return _swap_pairs(best, spans, before)


def _median2(values: Sequence[int]) -> int:
    """Twice the median, so that halves stay integers."""
    v = sorted(values)
    return v[len(v) // 2] + v[(len(v) - 1) // 2]


def _median_pass(order: Sequence[str], spans: Sequence[Span], before: Before) -> list[str]:
    """Spans take the median place of their columns, then the columns of a span the median rank."""
    pos = {c: i for i, c in enumerate(order)}
    at = [sorted(pos[c] for c in members) for members, _ in spans]
    ranked = sorted(range(len(spans)), key=lambda s: (_median2(at[s]), at[s], s))
    rank = {s: r for r, s in enumerate(ranked)}
    held: dict[str, list[int]] = {}
    for s, (members, _) in enumerate(spans):
        for c in members:
            held.setdefault(c, []).append(rank[s])
    held_cols = (c for c in order if c in held)
    moved = iter(sorted(held_cols, key=lambda c: (_median2(held[c]), pos[c])))
    return _extend([next(moved) if c in held else c for c in order], before)


def _swap_pairs(order: Sequence[str], spans: Sequence[Span], before: Before) -> list[str]:
    """Swap any two columns while the cost falls: scan i < j, keep a swap that lowers it."""
    order, best = list(order), _cost(order, spans)
    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                if not _swappable(order, i, j, before):
                    continue
                order[i], order[j] = order[j], order[i]
                cost = _cost(order, spans)
                if cost < best:
                    best, improved = cost, True
                else:
                    order[i], order[j] = order[j], order[i]
    return order


def _swappable(order: Sequence[str], i: int, j: int, before: Before) -> bool:
    """Columns i < j may trade places: j is not held by i or by one between, nor i by those."""
    a, b = order[i], order[j]
    return a not in before[b] and all(
        a not in before[c] and c not in before[b] for c in order[i + 1 : j]
    )


def _extend(order: Sequence[str], before: Before) -> list[str]:
    """The order with every column after its predecessors: each step takes the first free column."""
    out: list[str] = []
    placed: set[str] = set()
    rest = list(order)
    while rest:
        c = next((c for c in rest if before[c] <= placed), rest[0])
        rest.remove(c)
        out.append(c)
        placed.add(c)
    return out


def _precedence(cols: Sequence[str], block: Block, flow: FlowGraph, options: Options) -> Before:
    pairs = [*_driver_pairs(cols, block, flow, options), *_pole_pairs(cols, flow)]
    return {c: frozenset(a for a, b in pairs if b == c) for c in cols}


def _driver_pairs(
    cols: Sequence[str], block: Block, flow: FlowGraph, options: Options
) -> list[tuple[str, str]]:
    """With `driver_first`, a fan block's driver column stands first, unless it is also a leg."""
    if not options.driver_first:
        return []
    fan = next((f for f in flow.fans if f.id == block.fan), None)
    if fan is None:
        return []
    here = set(cols)
    drivers = [a.column for a in fan.drivers if a.column in here]
    if not drivers or drivers[0] in {a.column for a in fan.legs}:
        return []
    return [(drivers[0], c) for c in cols if c != drivers[0]]


def _pole_pairs(cols: Sequence[str], flow: FlowGraph) -> list[tuple[str, str]]:
    """A bundle's legs, one column each, keep the order the fan lists them in (lane order)."""
    here = set(cols)
    pairs: list[tuple[str, str]] = []
    for fan in flow.fans:
        legs = [a.column for a in fan.legs if a.column in here]
        if fan.lanes > 1 and len(set(legs)) == len(legs):
            pairs += list(pairwise(legs))
    return pairs


def _pin_order(block: Block, flow: FlowGraph) -> list[str]:
    rank = {pin: i for i, (pin, _) in enumerate(block.pin_edges)}
    columns = {c.id: c for c in flow.columns}
    return sorted(block.columns, key=lambda c: (_pin_rank(columns[c], rank), natural_key(c)))


def _pin_rank(column: Column, rank: Mapping[str, int]) -> int:
    end = next(e for e in (*column.heads, *column.feet) if e.kind == "boxpin")
    return rank.get(end.pin.pin if end.pin else "", len(rank))
