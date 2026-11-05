"""Stage 5, y: a fan's trunk constraints, the trunks the stacks hold tangled, and their columns."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from .arrow_reserve import leg_depth, leg_fit, leg_rows
from .band import arrow_hang, level_offset, trunk_room
from .clearance import reach
from .cut_costs import ref_name
from .cut_end_rooms import arrow_room
from .geometry import pin_of, pin_xy
from .hangings import hanging_keep
from .node_names import LOW, box_node, box_y_node, pin_node
from .pack import cell_node

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .constraints import Graph
    from .flow_values import Attach, Cell, Fan
    from .pack import PlacedColumn
    from .place_env import PageEnv
    from .place_levels import Span
    from .place_room import CrossedRooms
    from .sym_values import Sym

TRUNK = "trunk:"


def trunk_node(fan: str, row: int) -> str:
    """The graph node of one fan's trunk in one row."""
    return f"{TRUNK}{fan}:{row}"


def box_pin_x(env: PageEnv, x: Mapping[str, int], box: str, pin: str) -> int:
    """The solved x of a box pin: its own node when the row solved one, else its offset."""
    sym = env.syms[box]
    default = x[box_node(box, LOW)] - sym.body.x + next(p.dx for p in sym.pins if p.id == pin)
    return x.get(pin_node(box, pin), default)


def box_at(env: PageEnv, sym: str) -> tuple[str, int] | None:
    """The y node of the card box `sym` and the row it stands in; None for any other symbol."""
    for r, row in enumerate(env.plan.rows):
        for b in row.blocks:
            if env.blocks[b].is_card and env.blocks[b].anchor == sym:
                return box_y_node(sym), r
    return None


def in_row(env: PageEnv, fan: Fan, a: Attach, row: int) -> bool:
    """The attachment stands on the fan's trunk in `row`: levelled and drawn by this one test.

    A column's lane stands in its column's row; a box pin on its box's row and on every row
    where the fan has a column, unless a row-wrap arrow of the fan lies between (layout-0511).
    """
    if a.column is not None:
        return a.column in env.pcs and env.pcs[a.column].row == row
    at = box_at(env, a.pin.sym)
    if at is not None and at[1] == row:
        return True
    here = at[1] if at is not None else row
    cut = any((here <= r0 and r1 <= row) or (row <= r0 and r1 <= here) for r0, r1 in env.wraps.get(ref_name(fan), ()))
    return not cut and any(b.column is not None and in_row(env, fan, b, row) for b in (*fan.drivers, *fan.legs))


def _cell_of(pc: PlacedColumn, a: Attach) -> tuple[Cell, int]:
    """The attached cell after a flip: cells reversed, so the index counts from the other end."""
    cells = pc.lanes[a.lane]
    index = len(cells) - 1 - a.cell if pc.flipped else a.cell
    return cells[index], index


def _clear(env: PageEnv, fan: Fan, a: Attach, crossed: CrossedRooms) -> int:
    """The y from the trunk to a crossed attachment's pin: grid * (lanes + levels), else 0."""
    levels = crossed.get((fan.id, a.pin.sym), 0)
    return level_offset(fan.lanes, levels, env.options.wiring_grid) if levels else 0


def anchors_under(env: PageEnv, x: Mapping[str, int], spans: Sequence[Span]) -> frozenset[tuple[str, str, str]]:
    """(fan, card, pin) of each hung pin on a card that the fan's trunk in the card's row runs over."""
    out: set[tuple[str, str, str]] = set()
    for sym, pin in {(sym, pin) for sym, pin, _ in env.hangings}:
        if (card := box_at(env, sym)) is not None:
            at = box_pin_x(env, x, sym, pin)
            out |= {(s.fan, sym, pin) for s in spans if s.row == card[1] and s.x0 <= at <= s.x1}
    return frozenset(out)


def _reach(env: PageEnv, fan: Fan, a: Attach, *, north: bool) -> int:
    """The G the anchors and leads (with their markers) on the card's pin row under this trunk reach towards it (R510)."""
    sym, side = env.syms[a.pin.sym], "N" if north else "S"
    dy = pin_of(sym, a.pin.pin).dy
    keeps = (
        hanging_keep(h, (0, 0), a.pin.sym, None)
        for (owner, pin, _), hs in env.hangings.items()
        if owner == a.pin.sym and (a.column is not None or (fan.id, owner, pin) in env.under) and pin_of(sym, pin).dy == dy
        for h in hs
        if h.side == side and h.kind in ("anchor", "lead")
    )
    return reach(0, keeps, "above" if north else "below", env.options.wiring_grid)


def _steps_out(sym: Sym, cell: Cell, pin: str) -> bool:
    """A cell whose pins all stand on the driver pin's line can step out only along the trunk's way (R472, KI-131)."""
    dx = pin_xy(sym, cell, pin)[0]
    return all(pin_xy(sym, cell, p.id)[0] == dx for p in sym.pins)


def _driver(g: Graph, fan: Fan, a: Attach, env: PageEnv, crossed: CrossedRooms) -> None:
    """A driver's pin lies wire_min above the trunk at least; a crossed one, its levels more."""
    rise = max(env.options.wire_min, _clear(env, fan, a, crossed), _reach(env, fan, a, north=False))
    if a.column is None:
        at = box_at(env, a.pin.sym)
        if at is not None:
            dy = pin_of(env.syms[a.pin.sym], a.pin.pin).dy
            # R472: the trunk clears the step-out cell of the box's other pins (kept, KI-131)
            g.after(at[0], trunk_node(fan.id, at[1]), dy + rise + env.options.wiring_grid)
        return
    pc = env.pcs.get(a.column)
    if pc is not None:
        cell, index = _cell_of(pc, a)
        dy = pin_xy(env.syms[cell.sym], cell, a.pin.pin)[1]
        g.after(
            cell_node(pc.id, a.lane, index),
            trunk_node(fan.id, pc.row),
            dy + rise + (env.options.wiring_grid if _steps_out(env.syms[cell.sym], cell, a.pin.pin) else 0),
        )


class _Hang(NamedTuple):
    """What a fan's legs hang by: the fan, the trunks held loose, the crossed levels, the arrow room of each row."""

    fan: Fan
    tangled: AbstractSet[str]
    crossed: CrossedRooms
    arrow: Mapping[int, int]


def _leg(g: Graph, h: _Hang, a: Attach, env: PageEnv) -> str | None:
    """Hang the leg `depth` under the trunk; the trunk when the stacks hold the cell elsewhere."""
    pc = env.pcs.get(a.column) if a.column is not None else None
    at = box_at(env, a.pin.sym) if a.column is None else None
    row = pc.row if pc is not None else at[1] if at is not None else 0
    step = env.options.wiring_grid
    depth = max(
        trunk_room(h.fan.lanes, step, arrow_hang(h.fan.lanes, step, h.arrow.get(row, 0)))[1],
        _clear(env, h.fan, a, h.crossed),
        _reach(env, h.fan, a, north=True),
    )
    if a.column is None:
        if at is not None:
            g.after(trunk_node(h.fan.id, at[1]), at[0], depth - pin_of(env.syms[a.pin.sym], a.pin.pin).dy)
        return None
    if pc is None:
        return None
    cell, index = _cell_of(pc, a)
    trunk, node, distance = (
        trunk_node(h.fan.id, pc.row),
        cell_node(pc.id, a.lane, index),
        depth - pin_xy(env.syms[cell.sym], cell, a.pin.pin)[1],
    )
    if trunk in h.tangled:
        g.after(trunk, node, distance)
    elif not g.equal(trunk, node, distance):
        return trunk
    return None


def fan_roles(env: PageEnv, fan: Fan) -> tuple[tuple[Attach, ...], tuple[Attach, ...]]:
    """Drivers and legs as the page stands them: a fan wholly in flipped columns is upside down.

    A flip reverses the stacks, not the fan: stage 1 put drivers above legs in the natural
    order, so a fan whose every attachment is in a flipped column swaps its two sides.
    """
    ends = [a for a in (*fan.drivers, *fan.legs) if a.column is not None]
    pcs = [env.pcs.get(a.column or "") for a in ends]
    boxed = len(ends) < len(fan.drivers) + len(fan.legs)
    if boxed or not pcs or not all(pc is not None and pc.flipped for pc in pcs):
        return fan.drivers, fan.legs
    return fan.legs, fan.drivers


def fan_side(env: PageEnv, fan: Fan) -> str:
    """The trunk side as the page stands the fan: a swapped fan lies on the other side."""
    if fan_roles(env, fan)[0] is fan.drivers:
        return fan.side
    return "below" if fan.side == "above" else "above"


def held_room(fan: Fan, env: PageEnv, row: int) -> tuple[int, int]:
    """The G the solve holds above and below the fan's trunk in `row`: the value its edges, `Trunk.room` and the spans read."""
    stood = leg_rows(env.refs, env.plan.page)
    arrow = arrow_room(env.refs, env.plan, [fan], row, env.options)
    leg = leg_depth(fan, stood, row, leg_fit(env.options, env.refs, env.plan.page), arrow)
    return trunk_room(fan.lanes, env.options.wiring_grid, leg)


def trunk_constraints(
    g: Graph,
    fan: Fan,
    env: PageEnv,
    tangled: AbstractSet[str],
    crossed: CrossedRooms,
) -> frozenset[str]:
    """One trunk per fan and row: drivers drop to it from above, legs hang `depth` under it.

    A trunk in `tangled` has its legs hang at least that far, not exactly. Returns the trunks
    with a leg the stacks would not let hang exactly: they belong in `tangled`.
    """
    opts = env.options
    drivers, legs = fan_roles(env, fan)
    for a in drivers:
        _driver(g, fan, a, env, crossed)
    rows = {env.pcs[a.column].row for a in (*fan.drivers, *fan.legs) if a.column is not None and a.column in env.pcs} | {
        at[1] for a in (*fan.drivers, *fan.legs) if (at := box_at(env, a.pin.sym)) is not None
    }
    hang = _Hang(fan, tangled, crossed, {row: arrow_room(env.refs, env.plan, [fan], row, opts) for row in rows})
    refused = {t for a in legs if (t := _leg(g, hang, a, env)) is not None}
    for row in rows:
        above, below = held_room(fan, env, row)
        g.after(f"row:{row}", trunk_node(fan.id, row), above)
        g.after(trunk_node(fan.id, row), f"row:{row + 1}", below + opts.row_gap)
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
        if a.column is not None and a.column in env.pcs and trunk_node(fan.id, env.pcs[a.column].row) in tangled
    )
