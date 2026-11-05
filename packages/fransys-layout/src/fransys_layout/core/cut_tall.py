"""Stage 4, before the DP: a column that does not fit the page is cut into pieces that do.

The one Column splitter, on two axes. A column taller than the page: each lane is cut on its own,
at the first cell that passes the page height, again for each piece (CUT-TALL). A column wider
than the page: whole lanes go to a piece while it stays within the page width, and each join end
across a cut becomes a reference (ROW-WRAP, layout-0464). The references returned here have page 0
at both ends; `cut_pages` fills the pages in once the DP has run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .cut_costs import with_wires
from .cut_dp import wide_room
from .flow_values import Attach, Block, Column, End, Lane
from .geometry import lane_extent, marker_drawn_box_at, stack_lane
from .row_extent import grid_up
from .topology import build_column
from .values import PinRef, Ref, RefEnd, RefKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .flow_values import BlockList, Cell, Fan, FlowGraph
    from .sym_values import Sym
    from .values import Options, PlacementProblem

Tag = tuple[str, PinRef, PinRef]


@dataclass(frozen=True, slots=True)
class Fold:
    """A column cut into `pieces`, top to bottom or by lane.

    bounds[lane]: each piece's first cell, the lane length last. lane_of[k]: each lane's index in piece k.
    tags[k]: per lane crossing cut k, (net, above, below). taps: per parted join end, (root attach, new attach).
    """

    pieces: tuple[Column, ...]
    bounds: tuple[tuple[int, ...], ...]
    lane_of: tuple[tuple[int | None, ...], ...]
    tags: tuple[tuple[tuple[Tag, ...], ...], ...]
    taps: tuple[tuple[Attach, Attach], ...] = ()


@dataclass(frozen=True, slots=True)
class Tall:
    """What the cut reads: symbols, options, the height a piece may have, which net a pin is on."""

    syms: Mapping[str, Sym]
    options: Options
    page_h: int
    page_w: int
    net_of: Mapping[PinRef, str]
    in_row: frozenset[str]
    pins_of: Mapping[str, Sequence[PinRef]]
    height: Mapping[str, int]
    extra: Mapping[str, int]
    fans: Sequence[Fan]


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
    """The flow and blocks with every tall or wide column cut into pieces, and the planned references."""
    env = Tall(
        {s.id: s for s in problem.symbols},
        options,
        problem.area.h - options.page_headroom - _reserve(options),
        problem.area.w - 2 * options.margin.w,
        {ref: n.id for n in problem.nets for ref in n.pins},
        frozenset(s.id for s in problem.symbols if s.row_group),
        {n.id: n.pins for n in problem.nets},
        heights := {c.id: c.height for c in flow.columns},
        _extra(heights, blocks),
        flow.fans,
    )
    folds = {c.id: f for c in flow.columns if (f := _fold(c, env)) is not None}
    if not folds:
        return flow, blocks, ()
    columns = tuple(p for c in flow.columns for p in (folds[c.id].pieces if c.id in folds else (c,)))
    fans = tuple(_rewrite_fan(f, folds) for f in flow.fans)
    links = tuple(replace(x, ends=_moved(x.ends, folds)) for x in flow.cross_links)
    new_blocks = tuple(_rewrite_blocks(bl, folds, env) for bl in blocks)
    refs = tuple(r for f in folds.values() for r in _tags(f))
    return replace(flow, columns=columns, fans=fans, cross_links=links), new_blocks, refs


def _tags(f: Fold) -> tuple[Ref, ...]:
    """One tag pair per wire across each height cut, foot to head (LC1)."""
    return tuple(
        Ref(net, RefKind.TAG, (RefEnd(0, f.pieces[k].id, a), RefEnd(0, f.pieces[k + 1].id, b)))
        for k, lanes in enumerate(f.tags)
        for wires in lanes
        for net, a, b in wires
    )


def _fold(c: Column, env: Tall) -> Fold | None:
    """The fold of a column taller or wider than the page, else None."""
    room = env.page_h - env.extra.get(c.id, 0)
    if c.height <= room:
        return _fold_wide(c, env)
    tag = _tag_room(env.options)
    cuts = [_cuts(ln.cells, env, room, tag) for ln in c.lanes]
    count = max(len(b) for b in cuts) - 1
    if count <= 1:
        return None
    return _split(c, [(*b, *([b[-1]] * (count + 1 - len(b)))) for b in cuts], env)


def _fold_wide(c: Column, env: Tall) -> Fold | None:
    """The fold of a column wider than the page: whole lanes to a piece, the first lane of each listed."""
    if len(c.lanes) == 1:
        return None
    room = wide_room(env.page_w, env.options)
    firsts = [0]
    lo, hi = 0, 0
    for i, ln in enumerate(c.lanes):
        a, b = lane_extent(env.syms, ln.cells, env.in_row)
        if i > firsts[-1] and max(hi, ln.offset + b) - min(lo, ln.offset + a) > room:
            firsts.append(i)
            lo, hi = ln.offset + a, ln.offset + b
        else:
            lo, hi = min(lo, ln.offset + a), max(hi, ln.offset + b)
    if len(firsts) == 1:
        return None
    n = len(firsts)
    piece_of = [sum(i >= f for f in firsts) - 1 for i in range(len(c.lanes))]
    bounds = [(0,) * (p + 1) + (len(ln.cells),) * (n - p) for ln, p in zip(c.lanes, piece_of, strict=True)]
    return _split(c, bounds, env, piece_of)


def _tag_room(options: Options) -> int:
    """The G a tag the fold places at a piece end holds: its drawn box on the wiring grid (R1430)."""
    drawn = marker_drawn_box_at(0, 0, options, options.marker_facing["S"], (PinRef("", ""), str(RefKind.TAG))).h
    return grid_up(drawn, options.wiring_grid)


def _cuts(cells: Sequence[Cell], env: Tall, room: int, tag: int) -> tuple[int, ...]:
    """Where each piece of a lane starts, and its length last; a piece and the tags at its ends stand in the page."""
    ys, _ = stack_lane(env.syms, tuple(cells), env.options, env.in_row)
    starts, top = [0], 0
    for i, (cell, y) in enumerate(zip(cells, ys, strict=True)):
        fp = env.syms[cell.sym].footprint
        avail = room - (tag if len(starts) > 1 else 0) - (0 if i == len(cells) - 1 else tag)
        if i > starts[-1] and y + fp.y + fp.h - top > avail:
            starts.append(i)
            top = y + fp.y
        elif i == 0:
            top = y + fp.y
    return (*starts, len(cells))


def _wires(c: Column, lane: int, cut: int, env: Tall) -> tuple[Tag, ...]:
    """The wires across a cut of `lane` at cell `cut`: a chain hop's nets, else the two-pin net."""
    above, below = c.lanes[lane].cells[cut - 1], c.lanes[lane].cells[cut]
    if c.is_chain:
        return tuple((n, _pin_on(env, n, above.sym), _pin_on(env, n, below.sym)) for n in c.hops[cut - 1])
    pin_a, pin_b = PinRef(above.sym, above.bottom_pin or ""), PinRef(below.sym, below.top_pin or "")
    return ((env.net_of.get(pin_a, ""), pin_a, pin_b),)


def _pin_on(env: Tall, net: str, sym: str) -> PinRef:
    return next(p for p in env.pins_of[net] if p.sym == sym)


def _split(c: Column, bounds: Sequence[tuple[int, ...]], env: Tall, piece_of: Sequence[int] | None = None) -> Fold:
    """The pieces of a cut at `bounds`, each measured as stage 1 measures one.

    piece_of: given for a width cut, the piece of each whole lane.
    """
    n = len(bounds[0]) - 1
    tags = tuple(tuple(_wires(c, i, b[k + 1], env) for i, b in enumerate(bounds) if b[k] < b[k + 1] < b[k + 2]) for k in range(n - 1))
    out: list[Column] = []
    lane_of: list[tuple[int | None, ...]] = []
    for k in range(n):
        held = [i for i, b in enumerate(bounds) if b[k] < b[k + 1]]
        lane_of.append(tuple(held.index(i) if i in held else None for i in range(len(bounds))))
        left = c.lanes[held[0]].offset if piece_of is not None else 0
        lanes = tuple(Lane(c.lanes[i].cells[bounds[i][k] : bounds[i][k + 1]], c.lanes[i].offset - left) for i in held)
        ends = _tall_ends(c, (k, n), tags) if piece_of is None else _wide_ends(c, held, piece_of)
        piece = build_column(f"{c.id}#{chr(97 + k)}", lanes, ends, env.syms, env.options)
        out.append(replace(piece, hops=c.hops[bounds[0][k] : bounds[0][k + 1] - 1] if piece_of is None else c.hops))
    return Fold(tuple(out), tuple(bounds), tuple(lane_of), tags, () if piece_of is None else _taps(c, piece_of, env))


def _tall_ends(c: Column, at: tuple[int, int], tags: Sequence[tuple[tuple[Tag, ...], ...]]) -> tuple[tuple[End, ...], tuple[End, ...]]:
    """A height cut's piece k of n: the column's own ends at its top and foot, open ends at the cuts."""
    k, n = at
    return (c.heads if k == 0 else _ends(tags[k - 1], below=True), c.feet if k == n - 1 else _ends(tags[k], below=False))


def _owner(c: Column) -> dict[str, int]:
    return {x.sym: i for i, ln in enumerate(c.lanes) for x in ln.cells}


def _root(c: Column, ends: Sequence[End], lane: int) -> int:
    """The lane whose end is the net's own: the join partners of `lane` are followed to it."""
    owner = _owner(c)
    while (pin := ends[lane].pin) is not None and ends[lane].is_join and pin.sym in owner:
        lane = owner[pin.sym]
    return lane


def _parted(c: Column, piece_of: Sequence[int]) -> list[tuple[int, int]]:
    """(side, lane) of each join end whose partner lane stands in another piece."""
    owner = _owner(c)
    return [
        (side, i)
        for side, ends in enumerate((c.heads, c.feet))
        for i, e in enumerate(ends)
        if e.is_join and e.pin is not None and e.pin.sym in owner and piece_of[owner[e.pin.sym]] != piece_of[i]
    ]


def _own_pin(c: Column, side: int, lane: int) -> PinRef:
    """The pin of the lane's end cell on its head side (0) or foot side (1)."""
    cell = c.lanes[lane].cells[-side]
    return PinRef(cell.sym, (cell.bottom_pin if side else cell.top_pin) or "")


def _wide_ends(c: Column, held: Sequence[int], piece_of: Sequence[int]) -> tuple[tuple[End, ...], tuple[End, ...]]:
    """A width cut's piece: its lanes' own ends; a join to a lane in another piece is its net's own end."""
    parted = set(_parted(c, piece_of))
    heads, feet = (
        tuple(_lane_end(c, ends, parted=(side, i) in parted, at=(i, held.index(i), side)) for i in held)
        for side, ends in enumerate((c.heads, c.feet))
    )
    return heads, feet


def _lane_end(c: Column, ends: Sequence[End], *, parted: bool, at: tuple[int, int, int]) -> End:
    """A lane's end in its piece, its lane renumbered; one parted from its partner takes the root's kind."""
    i, lane, side = at
    root = ends[_root(c, ends, i)] if parted else ends[i]
    if root.lane is not None:  # only a boxpin end carries a lane
        return replace(root, lane=lane)
    if not parted:
        return root
    return End("fan", root.net, _own_pin(c, side, i), fan=root.fan) if root.kind == "fan" else End("open", root.net, _own_pin(c, side, i))


def _taps(c: Column, piece_of: Sequence[int], env: Tall) -> tuple[tuple[Attach, Attach], ...]:
    """For each parted join end rooted in a fan, the root's attach and the new one at the lane's own pin."""
    out: list[tuple[Attach, Attach]] = []
    for side, i in _parted(c, piece_of):
        ends = (c.heads, c.feet)[side]
        root, r = ends[_root(c, ends, i)], _root(c, ends, i)
        found = [a for f in env.fans for a in (*f.drivers, *f.legs) if a.column == c.id and a.lane == r and a.pin == root.pin]
        if root.kind == "fan" and found:
            cell = len(c.lanes[i].cells) - 1 if side else 0
            out.append((found[0], Attach(c.id, i, cell, _own_pin(c, side, i), found[0].pole, net=found[0].net)))
    return tuple(out)


def _ends(lanes: tuple[tuple[Tag, ...], ...], *, below: bool) -> tuple[End, ...]:
    """One open end per crossing lane, on the pin below the cut, else above it."""
    return tuple(End("open", w[0][0], w[0][2] if below else w[0][1]) for w in lanes)


def _rewrite_fan(f: Fan, folds: Mapping[str, Fold]) -> Fan:
    """A fan's attachments follow their cells; each tap of a width cut joins the side its root stands on."""
    taps = [t for fold in folds.values() for t in fold.taps]
    drivers = (*f.drivers, *(new for root, new in taps if root in f.drivers))
    legs = (*f.legs, *(new for root, new in taps if root in f.legs))
    return replace(f, drivers=_moved(drivers, folds), legs=_moved(legs, folds))


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


def _rewrite_blocks(bl: BlockList, folds: Mapping[str, Fold], env: Tall) -> BlockList:
    """The unit's blocks with each cut column's pieces in place; a card's later pieces stand free after the cards."""
    rewritten = [_rewrite_block(b, folds, env) for b in bl.blocks]
    free = [x for _, spilled in rewritten for x in spilled]
    return replace(bl, blocks=(*(b for b, _ in rewritten), *(replace(x, forced_break_before=i == 0) for i, x in enumerate(free))))


def _rewrite_block(b: Block, folds: Mapping[str, Fold], env: Tall) -> tuple[Block, list[Block]]:
    """A block lists the pieces of a cut column in its place and is as tall as they are.

    A card keeps the first piece of a width cut on its box pin; each later piece that meets a box pin is spilled (layout-0464).
    """
    if not any(c in folds for c in b.columns):
        return b, []
    later = [
        p
        for c in b.columns
        if c in folds and None in folds[c].lane_of[0]
        for p in folds[c].pieces[1:]
        if b.is_card and any(e.lane is not None for e in (*p.heads, *p.feet))
    ]
    gone = {p.id for p in later}
    cols = tuple(i for c in b.columns for i in ((p.id for p in folds[c].pieces) if c in folds else (c,)) if i not in gone)
    spilled = [
        Block(
            f"column:{p.id}",
            "column",
            b.unit,
            (p.id,),
            None,
            None,
            b.group,
            p.width,
            p.height,
            short=b.short,
            keep_whole=len(p.lanes) > 1,
            forced_break_before=False,
            seat="none",
        )
        for p in later
    ]
    heights = ([p.height for p in folds[c].pieces] if c in folds else [env.height[c]] for c in b.columns)
    return replace(b, columns=cols, height_est=env.extra[b.columns[0]] + max(h for hs in heights for h in hs)), spilled
