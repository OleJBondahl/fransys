"""Stage 4, before the DP: a single-lane column taller than the page is cut at a two-pin net.

The fold is a tag pair by necessity and is excluded from P2 (design 4.4). The tag returned
here has page 0 at both ends; `cut_pages` fills the pages in once the DP has run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .geometry import stack_lane
from .topology import build_column
from .values import Column, End, Lane, PinRef, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .values import Attach, Block, BlockList, Fan, FlowGraph, Options, PlacementProblem, Sym


MIN_CELLS = 2  # a single cell cannot be cut


@dataclass(frozen=True, slots=True)
class Fold:
    """A column cut at cell `cut` into top and bottom, over `tags`: (net, pin above, pin below)."""

    top: Column
    bottom: Column
    cut: int
    tags: tuple[tuple[str, PinRef, PinRef], ...]


@dataclass(frozen=True, slots=True)
class Tall:
    """What the cut reads: symbols, options, the page height, which net a pin is on."""

    syms: Mapping[str, Sym]
    options: Options
    page_h: int
    net_of: Mapping[PinRef, str]
    in_row: frozenset[str]
    pins_of: Mapping[str, Sequence[PinRef]]


def split_tall(
    flow: FlowGraph, blocks: tuple[BlockList, ...], problem: PlacementProblem, options: Options
) -> tuple[FlowGraph, tuple[BlockList, ...], tuple[Ref, ...]]:
    """The flow and blocks with every tall column cut in two, and one planned tag per cut."""
    env = Tall(
        {s.id: s for s in problem.symbols},
        options,
        problem.area.h - 2 * options.margin.h,
        {ref: n.id for n in problem.nets for ref in n.pins},
        frozenset(s.id for s in problem.symbols if s.row_group),
        {n.id: n.pins for n in problem.nets},
    )
    folds = {c.id: f for c in flow.columns if (f := _fold(c, env)) is not None}
    if not folds:
        return flow, blocks, ()
    columns = tuple(p for c in flow.columns for p in _pieces(c, folds))
    fans = tuple(_rewrite_fan(f, folds) for f in flow.fans)
    links = tuple(replace(x, ends=_moved(x.ends, folds)) for x in flow.cross_links)
    new_blocks = tuple(
        replace(bl, blocks=tuple(_rewrite_block(b, folds) for b in bl.blocks)) for bl in blocks
    )
    refs = tuple(r for f in folds.values() for r in _tags(f))
    return replace(flow, columns=columns, fans=fans, cross_links=links), new_blocks, refs


def _pieces(c: Column, folds: Mapping[str, Fold]) -> tuple[Column, ...]:
    return (folds[c.id].top, folds[c.id].bottom) if c.id in folds else (c,)


def _tags(f: Fold) -> tuple[Ref, ...]:
    """One tag pair per wire across the fold, foot to head (LC1)."""
    return tuple(
        Ref(net, RefKind.TAG, (RefEnd(0, f.top.id, a), RefEnd(0, f.bottom.id, b)))
        for net, a, b in f.tags
    )


def _fold(c: Column, env: Tall) -> Fold | None:
    """The fold of a single-lane column of two or more cells taller than the page, else None."""
    if c.height <= env.page_h or len(c.lanes) != 1 or len(c.lanes[0].cells) < MIN_CELLS:
        return None
    cut = _cut_index(c, env)
    return _split(c, cut, env) if cut else None


def _cut_index(c: Column, env: Tall) -> int:
    """The first cell whose stacked footprint passes the page height, at least 1."""
    cells = c.lanes[0].cells
    ys, _ = stack_lane(env.syms, cells, env.options, env.in_row)
    for i, (cell, y) in enumerate(zip(cells, ys, strict=True)):
        fp = env.syms[cell.sym].footprint
        if y + fp.y + fp.h > env.page_h:
            return max(i, 1)
    return 0


def _wires(c: Column, cut: int, env: Tall) -> tuple[tuple[str, PinRef, PinRef], ...]:
    """The wires across a cut at `cut`: every net of a chain's hop, else the one two-pin net."""
    above, below = c.lanes[0].cells[cut - 1], c.lanes[0].cells[cut]
    if c.is_chain:
        return tuple(
            (n, _pin_on(env, n, above.sym), _pin_on(env, n, below.sym)) for n in c.hops[cut - 1]
        )
    pin_a, pin_b = PinRef(above.sym, above.bottom_pin or ""), PinRef(below.sym, below.top_pin or "")
    return ((env.net_of.get(pin_a, ""), pin_a, pin_b),)


def _pin_on(env: Tall, net: str, sym: str) -> PinRef:
    return next(p for p in env.pins_of[net] if p.sym == sym)


def _split(c: Column, cut: int, env: Tall) -> Fold:
    """The two columns of a cut at cell `cut`, each measured as stage 1 measures one."""
    cells, offset = c.lanes[0].cells, c.lanes[0].offset
    tags = _wires(c, cut, env)
    (net, pin_a, pin_b), *_ = tags
    top = build_column(
        f"{c.id}#a",
        (Lane(cells[:cut], offset),),
        (c.heads, (End("open", net, pin_a),)),
        env.syms,
        env.options,
    )
    bottom = build_column(
        f"{c.id}#b",
        (Lane(cells[cut:], offset),),
        ((End("open", net, pin_b),), c.feet),
        env.syms,
        env.options,
    )
    top = replace(top, hops=c.hops[: cut - 1])
    return Fold(top, replace(bottom, hops=c.hops[cut:]), cut, tags)


def _rewrite_fan(f: Fan, folds: Mapping[str, Fold]) -> Fan:
    return replace(f, drivers=_moved(f.drivers, folds), legs=_moved(f.legs, folds))


def _moved(attaches: Sequence[Attach], folds: Mapping[str, Fold]) -> tuple[Attach, ...]:
    return tuple(_move(a, folds) for a in attaches)


def _move(a: Attach, folds: Mapping[str, Fold]) -> Attach:
    """An attachment on a folded column follows its cell into the top or the bottom piece."""
    if a.column is None or a.column not in folds:
        return a
    fold = folds[a.column]
    if a.cell < fold.cut:
        return replace(a, column=fold.top.id)
    return replace(a, column=fold.bottom.id, cell=a.cell - fold.cut)


def _rewrite_block(b: Block, folds: Mapping[str, Fold]) -> Block:
    """A block lists the two pieces of a folded column where it listed the column."""
    cols = tuple(
        i
        for c in b.columns
        for i in ((folds[c].top.id, folds[c].bottom.id) if c in folds else (c,))
    )
    return replace(b, columns=cols)
