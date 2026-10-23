"""Stage 4, before the DP: a column taller than the page is cut into pieces that fit it.

Each lane is cut on its own, at the first cell that passes the page height, again for each piece
(CUT-TALL). A cut is a tag pair by necessity and is excluded from P2 (design 4.4). The tags
returned here have page 0 at both ends; `cut_pages` fills the pages in once the DP has run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .cut_costs import with_wires
from .geometry import stack_lane
from .topology import build_column
from .values import Column, End, Lane, PinRef, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .sym_values import Sym
    from .values import Attach, Block, BlockList, Cell, Fan, FlowGraph, Options, PlacementProblem

Tag = tuple[str, PinRef, PinRef]


@dataclass(frozen=True, slots=True)
class Fold:
    """A column cut into `pieces`, top to bottom.

    bounds[lane]: each piece's first cell, the lane length last. lane_of[k]: each lane's index in
    piece k (None: no cell). tags[k]: per lane crossing the cut after piece k, (net, above, below).
    """

    pieces: tuple[Column, ...]
    bounds: tuple[tuple[int, ...], ...]
    lane_of: tuple[tuple[int | None, ...], ...]
    tags: tuple[tuple[tuple[Tag, ...], ...], ...]


@dataclass(frozen=True, slots=True)
class Tall:
    """What the cut reads: symbols, options, the height a piece may have, which net a pin is on."""

    syms: Mapping[str, Sym]
    options: Options
    page_h: int
    net_of: Mapping[PinRef, str]
    in_row: frozenset[str]
    pins_of: Mapping[str, Sequence[PinRef]]
    height: Mapping[str, int]
    extra: Mapping[str, int]


def _reserve(options: Options) -> int:
    """What a row adds to a piece: its wires margin and an open stub at each end."""
    return with_wires(0, options) + 2 * options.open_stub


def _extra(height: Mapping[str, int], blocks: tuple[BlockList, ...]) -> dict[str, int]:
    """For each column, what its block's row holds beyond the block's tallest column."""
    out: dict[str, int] = {}
    for b in (b for unit in blocks for b in unit.blocks if b.columns):
        extra = max(0, b.height_est - max(height[c] for c in b.columns))
        out.update(dict.fromkeys(b.columns, extra))
    return out


def split_tall(
    flow: FlowGraph, blocks: tuple[BlockList, ...], problem: PlacementProblem, options: Options
) -> tuple[FlowGraph, tuple[BlockList, ...], tuple[Ref, ...]]:
    """The flow and blocks with every tall column cut into pieces, and one planned tag per wire."""
    env = Tall(
        {s.id: s for s in problem.symbols},
        options,
        problem.area.h - options.page_headroom - _reserve(options),
        {ref: n.id for n in problem.nets for ref in n.pins},
        frozenset(s.id for s in problem.symbols if s.row_group),
        {n.id: n.pins for n in problem.nets},
        heights := {c.id: c.height for c in flow.columns},
        _extra(heights, blocks),
    )
    folds = {c.id: f for c in flow.columns if (f := _fold(c, env)) is not None}
    if not folds:
        return flow, blocks, ()
    columns = tuple(p for c in flow.columns for p in _pieces(c, folds))
    fans = tuple(_rewrite_fan(f, folds) for f in flow.fans)
    links = tuple(replace(x, ends=_moved(x.ends, folds)) for x in flow.cross_links)
    new_blocks = tuple(
        replace(bl, blocks=tuple(_rewrite_block(b, folds, env) for b in bl.blocks)) for bl in blocks
    )
    refs = tuple(r for f in folds.values() for r in _tags(f))
    return replace(flow, columns=columns, fans=fans, cross_links=links), new_blocks, refs


def _pieces(c: Column, folds: Mapping[str, Fold]) -> tuple[Column, ...]:
    return folds[c.id].pieces if c.id in folds else (c,)


def _tags(f: Fold) -> tuple[Ref, ...]:
    """One tag pair per wire across each cut, foot to head (LC1)."""
    return tuple(
        Ref(net, RefKind.TAG, (RefEnd(0, f.pieces[k].id, a), RefEnd(0, f.pieces[k + 1].id, b)))
        for k, lanes in enumerate(f.tags)
        for wires in lanes
        for net, a, b in wires
    )


def _fold(c: Column, env: Tall) -> Fold | None:
    """The fold of a column taller than the page, else None."""
    room = env.page_h - env.extra.get(c.id, 0)
    if c.height <= room:
        return None
    cuts = [_cuts(ln.cells, env, room) for ln in c.lanes]
    count = max(len(b) for b in cuts) - 1
    if count <= 1:
        return None
    return _split(c, [(*b, *([b[-1]] * (count + 1 - len(b)))) for b in cuts], env)


def _cuts(cells: Sequence[Cell], env: Tall, room: int) -> tuple[int, ...]:
    """Where each piece of a lane starts, and its length last; a piece stands in the page."""
    ys, _ = stack_lane(env.syms, tuple(cells), env.options, env.in_row)
    starts, top = [0], 0
    for i, (cell, y) in enumerate(zip(cells, ys, strict=True)):
        fp = env.syms[cell.sym].footprint
        if i > starts[-1] and y + fp.y + fp.h - top > room:
            starts.append(i)
            top = y + fp.y
        elif i == 0:
            top = y + fp.y
    return (*starts, len(cells))


def _wires(c: Column, lane: int, cut: int, env: Tall) -> tuple[Tag, ...]:
    """The wires across a cut of `lane` at cell `cut`: a chain hop's nets, else the two-pin net."""
    above, below = c.lanes[lane].cells[cut - 1], c.lanes[lane].cells[cut]
    if c.is_chain:
        return tuple(
            (n, _pin_on(env, n, above.sym), _pin_on(env, n, below.sym)) for n in c.hops[cut - 1]
        )
    pin_a, pin_b = PinRef(above.sym, above.bottom_pin or ""), PinRef(below.sym, below.top_pin or "")
    return ((env.net_of.get(pin_a, ""), pin_a, pin_b),)


def _pin_on(env: Tall, net: str, sym: str) -> PinRef:
    return next(p for p in env.pins_of[net] if p.sym == sym)


def _split(c: Column, bounds: Sequence[tuple[int, ...]], env: Tall) -> Fold:
    """The pieces of a cut at `bounds`, each measured as stage 1 measures one."""
    n = len(bounds[0]) - 1
    tags = tuple(_cut_tags(c, bounds, k, env) for k in range(n - 1))
    out: list[Column] = []
    lane_of: list[tuple[int | None, ...]] = []
    for k in range(n):
        held = [i for i, b in enumerate(bounds) if b[k] < b[k + 1]]
        lane_of.append(tuple(held.index(i) if i in held else None for i in range(len(bounds))))
        lanes = tuple(
            Lane(c.lanes[i].cells[bounds[i][k] : bounds[i][k + 1]], c.lanes[i].offset) for i in held
        )
        heads = c.heads if k == 0 else _ends(tags[k - 1], below=True)
        feet = c.feet if k == n - 1 else _ends(tags[k], below=False)
        piece = build_column(f"{c.id}#{chr(97 + k)}", lanes, (heads, feet), env.syms, env.options)
        out.append(replace(piece, hops=c.hops[bounds[0][k] : bounds[0][k + 1] - 1]))
    return Fold(tuple(out), tuple(bounds), tuple(lane_of), tags)


def _cut_tags(
    c: Column, bounds: Sequence[tuple[int, ...]], k: int, env: Tall
) -> tuple[tuple[Tag, ...], ...]:
    """The wires of each lane that has cells on both sides of the cut after piece k."""
    return tuple(
        _wires(c, i, b[k + 1], env) for i, b in enumerate(bounds) if b[k] < b[k + 1] < b[k + 2]
    )


def _ends(lanes: tuple[tuple[Tag, ...], ...], *, below: bool) -> tuple[End, ...]:
    """One open end per crossing lane, on the pin below the cut, else above it."""
    return tuple(End("open", w[0][0], w[0][2] if below else w[0][1]) for w in lanes)


def _rewrite_fan(f: Fan, folds: Mapping[str, Fold]) -> Fan:
    return replace(f, drivers=_moved(f.drivers, folds), legs=_moved(f.legs, folds))


def _moved(attaches: Sequence[Attach], folds: Mapping[str, Fold]) -> tuple[Attach, ...]:
    return tuple(_move(a, folds) for a in attaches)


def _move(a: Attach, folds: Mapping[str, Fold]) -> Attach:
    """An attachment on a cut column follows its cell into the piece that holds it."""
    if a.column is None or a.column not in folds:
        return a
    fold = folds[a.column]
    starts = fold.bounds[a.lane]
    k = max(i for i in range(len(starts) - 1) if starts[i] <= a.cell)
    lane = fold.lane_of[k][a.lane]
    return replace(a, column=fold.pieces[k].id, lane=lane or 0, cell=a.cell - starts[k])


def _rewrite_block(b: Block, folds: Mapping[str, Fold], env: Tall) -> Block:
    """A block lists the pieces of a cut column in its place and is as tall as they are."""
    if not any(c in folds for c in b.columns):
        return b
    cols = tuple(
        i for c in b.columns for i in ((p.id for p in folds[c].pieces) if c in folds else (c,))
    )
    return replace(
        b, columns=cols, height_est=env.extra[b.columns[0]] + _tallest(b, folds, env.height)
    )


def _tallest(b: Block, folds: Mapping[str, Fold], height: Mapping[str, int]) -> int:
    """The tallest column of the block once its tall columns are cut."""
    heights = (
        [p.height for p in folds[c].pieces] if c in folds else [height[c]] for c in b.columns
    )
    return max(h for hs in heights for h in hs)
