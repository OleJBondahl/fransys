"""Stage 1, part 4: chains that share a symbol become lanes of one column, offset by pin dx."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .geometry import pin_xy
from .keys import natural_key
from .topology_chains import Node, cells_of, group_columns
from .topology_fans import LaneDraft

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .sym_values import Sym
    from .topology_elements import Elem
    from .topology_fans import Slot
    from .values import Cell, Orientation

Lane = tuple["Cell", ...]


def lanes_of(
    paths: tuple[tuple[Node, ...], ...],
    elems: Mapping[str, Elem],
    syms: Mapping[str, Sym],
    flip_turn: Orientation,
) -> tuple[list[LaneDraft], Slot]:
    """Chains sharing a symbol become lanes of one column, offset through the symbols they share."""
    lanes: list[LaneDraft] = []
    slot: Slot = {}
    for group in group_columns(paths, elems):
        cells = [cells_of(paths[i], elems, syms, flip_turn) for i in group]
        offsets = _offsets(cells, syms)
        order = sorted(range(len(group)), key=lambda k: offsets[k])
        for index, k in enumerate(order):
            lane = LaneDraft(f"c:{cells[order[0]][0].sym}", index, list(cells[k]), offsets[k])
            lanes.append(lane)
            first, last = paths[group[k]][0], paths[group[k]][-1]
            slot[(first.elem, first.top or "")] = (lane, "head")
            slot[(last.elem, last.bottom or "")] = (lane, "foot")
    return lanes, slot


def _pin_dx(cells: Lane, sym: str, syms: Mapping[str, Sym]) -> int:
    """The lane's wire x against the origin of `sym`: the pin dx of the lane's first cell of it."""
    c = next(c for c in cells if c.sym == sym)
    return pin_xy(syms[c.sym], c, c.top_pin or c.bottom_pin or "")[0]


def _held(lanes: Sequence[Lane]) -> list[list[tuple[str, list[int]]]]:
    """Per lane, its symbols in natural order, each with every lane that holds it."""
    holders: dict[str, list[int]] = defaultdict(list)
    for i, lane in enumerate(lanes):
        for sym in {c.sym for c in lane}:
            holders[sym].append(i)
    return [
        [(s, holders[s]) for s in sorted({c.sym for c in lane}, key=natural_key)] for lane in lanes
    ]


def _offsets(lanes: Sequence[Lane], syms: Mapping[str, Sym]) -> list[int]:
    """Each lane's wire x in one frame, from lane to lane over the symbols lanes share.

    A symbol stands once, so lane j is at lane i's x plus j's pin dx minus i's. The first path
    in lane order wins; a second path with another answer is ignored (pins of another pitch).
    """
    held = _held(lanes)
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
