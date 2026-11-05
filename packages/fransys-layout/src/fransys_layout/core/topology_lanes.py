"""Stage 1, part 4: chains that share a symbol become lanes of one column, offset by pin dx."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import pairwise
from typing import TYPE_CHECKING

from .flow_values import Cell
from .geometry import lane_extent, pin_xy
from .keys import natural_key
from .topology_chains import Node, cells_of, group_columns
from .topology_fans import LaneDraft
from .values import PinRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .sym_values import Sym
    from .topology_elements import Elem
    from .topology_fans import Slot
    from .values import Options

Lane = tuple["Cell", ...]


def lanes_of(
    paths: tuple[tuple[Node, ...], ...],
    elems: Mapping[str, Elem],
    syms: Mapping[str, Sym],
    options: Options,
    hubs: Mapping[PinRef, set[str]],
) -> tuple[list[LaneDraft], Slot, list[tuple[PinRef, PinRef]]]:
    """Chains sharing a symbol become lanes of one column, offset through the symbols they share.

    Also the joins whose cells have no pin facing each other, as the chain's own pins: a router's nets (layout-0482).
    `hubs` map a lane's end pin to the elements a fan deals beside it: their body reach keeps the lanes apart (R1208).
    """
    lanes: list[LaneDraft] = []
    slot: Slot = {}
    made: list[tuple[Cell, ...]] = []
    for path in paths:
        made.append(cells_of(path, elems, syms, options.flip_turn, {c.sym: c.orient for cells in made for c in cells}))
    joins = [
        (PinRef(elems[a.elem].sym, a.bottom or ""), PinRef(elems[b.elem].sym, b.top or ""))
        for path, cells in zip(paths, made, strict=True)
        for (a, b), (ca, cb) in zip(pairwise(path), pairwise(cells), strict=False)
        if not (ca.bottom_pin and cb.top_pin)
    ]

    for group in group_columns(paths, elems):
        cells = [made[i] for i in group]
        offsets = _offsets(cells, syms)
        order = sorted(range(len(group)), key=lambda k: offsets[k])
        offsets = _clear(cells, offsets, syms, order, (_reach([_dealt(paths[i], elems, hubs) for i in group], elems, syms), options.column_gap_min))
        for index, k in enumerate(order):
            lane = LaneDraft(f"c:{cells[order[0]][0].sym}", index, list(cells[k]), offsets[k])
            lanes.append(lane)
            first, last = paths[group[k]][0], paths[group[k]][-1]
            slot[(first.elem, first.top or "")] = (lane, "head")
            slot[(last.elem, last.bottom or "")] = (lane, "foot")
    return lanes, slot, joins


def _dealt(path: tuple[Node, ...], elems: Mapping[str, Elem], hubs: Mapping[PinRef, set[str]]) -> set[str]:
    """The hubs a fan deals at the head and the foot of a lane's path."""
    head, foot = path[0], path[-1]
    return hubs.get(PinRef(elems[head.elem].sym, head.top or ""), set()) | hubs.get(PinRef(elems[foot.elem].sym, foot.bottom or ""), set())


def _reach(dealt: Sequence[set[str]], elems: Mapping[str, Elem], syms: Mapping[str, Sym]) -> list[tuple[int, int]]:
    """Per lane, the body extent of the hubs it alone is dealt: a symbol two lanes are dealt (a pole box) stands once."""
    held = Counter(sym for lane in dealt for sym in {elems[e].sym for e in lane})
    return [
        lane_extent(
            syms, tuple(Cell(elems[e].sym, "R0", elems[e].n_pin, elems[e].s_pin) for e in lane if held[elems[e].sym] == 1), frozenset(), body=True
        )
        for lane in dealt
    ]


def _pin_dx(cells: Lane, sym: str, syms: Mapping[str, Sym]) -> int:
    """The lane's wire x against the origin of `sym`: the pin dx of the lane's first cell of it."""
    c = next(c for c in cells if c.sym == sym)
    return pin_xy(syms[c.sym], c, c.top_pin or c.bottom_pin or "")[0]


def _poled(sym: Sym) -> bool:
    """A pole box: some node joins two pins or more."""
    return any(len(n) > 1 for n in sym.nodes)


def _held(lanes: Sequence[Lane], syms: Mapping[str, Sym]) -> list[list[tuple[str, list[int]]]]:
    """Per lane, its symbols (pole boxes first, then natural order), each with every lane that holds it."""
    holders: dict[str, list[int]] = defaultdict(list)
    for i, lane in enumerate(lanes):
        for sym in {c.sym for c in lane}:
            holders[sym].append(i)
    return [[(s, holders[s]) for s in sorted({c.sym for c in lane}, key=lambda s: (not _poled(syms[s]), natural_key(s)))] for lane in lanes]


def _kinds(held: Sequence[Sequence[tuple[str, list[int]]]]) -> tuple[frozenset[str], dict[str, list[int]]]:
    """The hubs and the blocks among the symbols held by several lanes: a block's lanes are all held by a larger set (a pole box beside a hub)."""
    sets = {sym: others for lane in held for sym, others in lane if len(others) > 1}
    blocks = {sym: lanes for sym, lanes in sets.items() if any(len(other) > len(lanes) and set(lanes) <= set(other) for other in sets.values())}
    return frozenset(sets) - blocks.keys(), blocks


def _runs(lanes: Sequence[Lane], order: Sequence[int], hubs: frozenset[str]) -> dict[tuple[str, bool], list[tuple[int, Lane]]]:
    """The cells of each lane that are not a hub's, on one side of a hub, lanes in `order`: key (symbol, below), (lane, cells)."""
    runs: dict[tuple[str, bool], list[tuple[int, Lane]]] = defaultdict(list)
    for k in order:
        lane = lanes[k]
        key, run = (next((c.sym for c in lane if c.sym in hubs), ""), False), []
        for c in (*lane, None):
            if c is None or c.sym in hubs:
                if run:
                    runs[key].append((k, tuple(run)))
                key, run = (c.sym if c else "", True), []
            else:
                run.append(c)
    return runs


def _units(run: Sequence[tuple[int, Lane]], blocks: Mapping[str, list[int]]) -> list[tuple[list[int], int, Lane]]:
    """A run's pieces in lane order, each (lanes it moves, first lane, its cells): a block is one piece across its lanes, any other lane its own."""
    units: dict[str | int, tuple[list[int], int, Lane]] = {}
    for k, cells in run:
        key = next((c.sym for c in cells if c.sym in blocks), k)
        units.setdefault(key, (blocks.get(key, [k]), k, cells))
    return list(units.values())


def _clear(
    lanes: Sequence[Lane],
    offsets: Sequence[int],
    syms: Mapping[str, Sym],
    order: Sequence[int],
    clear: tuple[Sequence[tuple[int, int]], int],
) -> list[int]:
    """Push lanes (`order` is by offset) right until their own cells beside one hub clear each other, body to body, a `gap` apart (0469).

    A block (one pole box's lanes) moves as one, by the push its first lane's cells need: the symbol stands where that lane puts it.
    Then until the hub a fan deals to a lane's end (`hub`, its body reach) clears the next lane's, in every lane's offset order (R1208).
    """
    at, (hub, gap) = list(offsets), clear
    hubs, blocks = _kinds(_held(lanes, syms))
    for run in _runs(lanes, order, hubs).values():
        edge: int | None = None
        for moved, k, cells in _units(run, blocks):
            left, right = lane_extent(syms, cells, frozenset(), body=True)
            push = 0 if edge is None else max(0, edge + gap - left - at[k])
            for m in moved:
                at[m] += push
            edge = at[k] + right if edge is None else max(edge, at[k] + right)
    edge = None
    for k in (k for k in order if any(hub[k])):
        at[k] = at[k] if edge is None else max(at[k], edge - hub[k][0])
        edge = at[k] + hub[k][1] if edge is None else max(edge, at[k] + hub[k][1])
    return at


def _offsets(lanes: Sequence[Lane], syms: Mapping[str, Sym]) -> list[int]:
    """Each lane's wire x in one frame, from lane to lane over the symbols lanes share.

    A symbol stands once, so lane j is at lane i's x plus j's pin dx minus i's, a pole box (the cable box) first. The first path
    in lane order wins; a second path with another answer is ignored (pins of another pitch).
    """
    held = _held(lanes, syms)
    at: dict[int, int] = {}
    for start in range(len(lanes)):
        queue = [] if start in at else [start]
        at.setdefault(start, 0)
        for i in queue:
            for sym, others in held[i]:
                for j in others:
                    want = at[i] + _pin_dx(lanes[j], sym, syms) - _pin_dx(lanes[i], sym, syms)
                    if j not in at:
                        at[j] = want
                        queue.append(j)
    low = min(at.values())
    return [at[k] - low for k in range(len(lanes))]
