"""Stage 1, part 4: chains that share a symbol become lanes of one column, ordered by pin dx."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .geometry import pin_xy
from .keys import natural_key
from .topology_chains import Node, cells_of, group_columns
from .topology_fans import LaneDraft

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .topology_elements import Elem
    from .topology_fans import Slot
    from .values import Cell, Sym

SHARED = 2


def lanes_of(
    paths: tuple[tuple[Node, ...], ...], elems: Mapping[str, Elem], syms: Mapping[str, Sym]
) -> tuple[list[LaneDraft], Slot]:
    """Chains sharing a symbol become lanes of one column, ordered and offset by its pins."""
    lanes: list[LaneDraft] = []
    slot: Slot = {}
    for group in group_columns(paths, elems):
        cells = [cells_of(paths[i], elems, syms) for i in group]
        binder = _binder(cells)
        keyed = sorted(zip(group, cells, strict=True), key=lambda gc: _lane_dx(gc[1], binder, syms))
        base = _lane_dx(keyed[0][1], binder, syms)
        column = f"c:{keyed[0][1][0].sym}"
        for index, (i, lane_cells) in enumerate(keyed):
            offset = _lane_dx(lane_cells, binder, syms) - base
            lane = LaneDraft(column, index, list(lane_cells), offset)
            lanes.append(lane)
            slot[(paths[i][0].elem, paths[i][0].top or "")] = (lane, "head")
            slot[(paths[i][-1].elem, paths[i][-1].bottom or "")] = (lane, "foot")
    return lanes, slot


def _binder(cells: Sequence[tuple[Cell, ...]]) -> str | None:
    """The first symbol (by natural key) that two or more lanes of the column share."""
    counts: dict[str, int] = defaultdict(int)
    for lane in cells:
        for sym in {c.sym for c in lane}:
            counts[sym] += 1
    shared = sorted((s for s, n in counts.items() if n >= SHARED), key=natural_key)
    return shared[0] if shared else None


def _lane_dx(cells: tuple[Cell, ...], binder: str | None, syms: Mapping[str, Sym]) -> int:
    for c in cells:
        if c.sym == binder:
            return pin_xy(syms[c.sym], c, c.top_pin or c.bottom_pin or "")[0]
    return 0
