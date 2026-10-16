"""Stage 5, y: a fan's trunk constraints, the trunks the stacks hold tangled, and their columns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import pin_of, pin_xy
from .pack import cell_node

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

    from .constraints import Graph
    from .pack import PlacedColumn
    from .place_env import PageEnv
    from .values import Attach, Cell, Fan

TRUNK = "trunk:"


def trunk_node(fan: str, row: int) -> str:
    """The graph node of one fan's trunk in one row."""
    return f"{TRUNK}{fan}:{row}"


def _box_at(env: PageEnv, sym: str) -> tuple[str, int] | None:
    """The y node of the card box `sym` and the row it stands in; None for any other symbol."""
    for r, row in enumerate(env.plan.rows):
        for b in row.blocks:
            if env.blocks[b].is_card and env.blocks[b].anchor == sym:
                return f"box:{sym}", r
    return None


def _cell_of(pc: PlacedColumn, a: Attach) -> tuple[Cell, int]:
    """The attached cell after a flip: cells reversed, so the index counts from the other end."""
    cells = pc.lanes[a.lane]
    index = len(cells) - 1 - a.cell if pc.flipped else a.cell
    return cells[index], index


def _driver(g: Graph, fan: Fan, a: Attach, env: PageEnv) -> None:
    """A driver's pin lies wire_min above the trunk at least."""
    rise = env.options.wire_min
    if a.column is None:
        at = _box_at(env, a.pin.sym)
        if at is not None:
            dy = pin_of(env.syms[a.pin.sym], a.pin.pin).dy
            g.after(at[0], trunk_node(fan.id, at[1]), dy + rise)
        return
    pc = env.pcs.get(a.column)
    if pc is not None:
        cell, index = _cell_of(pc, a)
        dy = pin_xy(env.syms[cell.sym], cell, a.pin.pin)[1]
        g.after(cell_node(pc.id, a.lane, index), trunk_node(fan.id, pc.row), dy + rise)


def _leg(g: Graph, fan: Fan, a: Attach, env: PageEnv, tangled: AbstractSet[str]) -> str | None:
    """Hang the leg `depth` under the trunk; the trunk when the stacks hold the cell elsewhere."""
    depth = env.options.wiring_grid * fan.lanes
    if a.column is None:
        at = _box_at(env, a.pin.sym)
        if at is not None:
            g.after(
                trunk_node(fan.id, at[1]), at[0], depth - pin_of(env.syms[a.pin.sym], a.pin.pin).dy
            )
        return None
    pc = env.pcs.get(a.column)
    if pc is None:
        return None
    cell, index = _cell_of(pc, a)
    trunk, node = trunk_node(fan.id, pc.row), cell_node(pc.id, a.lane, index)
    distance = depth - pin_xy(env.syms[cell.sym], cell, a.pin.pin)[1]
    if trunk in tangled:
        g.after(trunk, node, distance)
    elif not g.equal(trunk, node, distance):
        return trunk
    return None


def trunk_constraints(
    g: Graph, fan: Fan, env: PageEnv, tangled: AbstractSet[str]
) -> frozenset[str]:
    """One trunk per fan and row: drivers drop to it from above, legs hang `depth` under it.

    A trunk in `tangled` has its legs hang at least that far, not exactly. Returns the trunks
    with a leg the stacks would not let hang exactly: they belong in `tangled`.
    """
    opts = env.options
    for a in fan.drivers:
        _driver(g, fan, a, env)
    refused = {t for a in fan.legs if (t := _leg(g, fan, a, env, tangled)) is not None}
    rows = {
        env.pcs[a.column].row
        for a in (*fan.drivers, *fan.legs)
        if a.column is not None and a.column in env.pcs
    }
    for row in rows:
        g.after(f"row:{row}", trunk_node(fan.id, row), opts.wiring_grid)
        g.after(
            trunk_node(fan.id, row), f"row:{row + 1}", opts.wiring_grid * fan.lanes + opts.row_gap
        )
    return frozenset(refused)


def tangled_trunks(g: Graph) -> frozenset[str]:
    """The trunks at an `after` edge whose ends the classes already hold closer than it asks.

    Graph.solve refuses such an edge: rigid stacks and equal legs have merged its two ends.
    """
    out: set[str] = set()
    for a, b, d in g.edges:
        (ra, oa), (rb, ob) = g.uf.find(a), g.uf.find(b)
        if ra == rb and ob - oa < d:
            out.update(n for n in (a, b) if n.startswith(TRUNK))
    return frozenset(out)


def loose_columns(env: PageEnv, tangled: AbstractSet[str]) -> frozenset[str]:
    """The columns a tangled trunk's drivers or legs sit in: they stack loose."""
    return frozenset(
        a.column
        for fan in env.flow.fans
        for a in (*fan.drivers, *fan.legs)
        if a.column is not None
        and a.column in env.pcs
        and trunk_node(fan.id, env.pcs[a.column].row) in tangled
    )
