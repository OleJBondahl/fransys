"""Stage 5, y: one constraint graph per page; stacks, trunks between, row groups level."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .arrow_reserve import arrow_ends, reserve
from .constraints import Graph
from .errors import CoreError
from .geometry import cell_footprint, pin_xy
from .keys import natural_key
from .marker_flags import pair_steps
from .marker_room import row_rooms
from .node_names import box_y_node, col_node
from .pack import cell_node
from .place_accept import accept
from .place_align import page_aligns, unmet_mates
from .place_foreign import clear_foreign
from .place_join_room import join_rooms
from .place_levels import Span, trunk_levels
from .place_ring import ring_symbols
from .place_room import Step, crossed_levels, origins, step_rooms
from .place_trunk import (
    box_at,
    box_pin_x,
    fan_roles,
    fan_side,
    in_row,
    loose_columns,
    tangled_trunks,
    trunk_constraints,
)
from .room import Room
from .row_extent import extent, grid_up
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .pack import PlacedColumn
    from .place_align import Align
    from .place_env import PageEnv
    from .place_room import CrossedRooms
    from .values import Attach, Box, Cell, Fan, RowPlan


class YCycleError(CoreError):
    """The stacks and trunks of a page are cyclic: stage 1 left a ring in a column."""


def _footprint(env: PageEnv, cell: Cell) -> Box:
    return cell_footprint(env.syms[cell.sym], cell, in_row=cell.sym in env.in_row)


def _pin_y(env: PageEnv, cell: Cell, pin: str | None) -> int:
    return 0 if pin is None else pin_xy(env.syms[cell.sym], cell, pin)[1]


def _gap(env: PageEnv, above: Cell, below: Cell, room: int = 0) -> int:
    fa, fb = _footprint(env, above), _footprint(env, below)
    wire = env.options.wire_min
    pins = max(wire, room)
    by_box = fa.y + fa.h + wire - fb.y
    pa = (
        pin_xy(env.syms[above.sym], above, above.bottom_pin)[1] if above.bottom_pin else fa.y + fa.h
    )
    pb = _pin_y(env, below, below.top_pin) if below.top_pin else fb.y
    return grid_up(max(by_box, pa + pins - pb), env.options.wiring_grid)


def _same_symbol(g: Graph, pc: PlacedColumn, lane: int, index: int, cell: Cell) -> None:
    """A symbol that spans lanes (a three-pair device) is one node in y."""
    for lj in range(lane):
        for j, other in enumerate(pc.lanes[lj]):
            if other.sym == cell.sym:
                g.equal(cell_node(pc.id, lj, j), cell_node(pc.id, lane, index), 0)
                return


def stack_constraints(
    g: Graph, pc: PlacedColumn, env: PageEnv, rooms: Mapping[Step, int], *, rigid: bool
) -> None:
    """Consecutive cells keep wire_min between footprints, `rooms` (else wire_min) between pins."""
    for li, cells in enumerate(pc.lanes):
        for i in range(1, len(cells)):
            a, b = cell_node(pc.id, li, i - 1), cell_node(pc.id, li, i)
            gap = _gap(env, cells[i - 1], cells[i], rooms.get((pc.id, li, i - 1), 0))
            if rigid:
                g.equal(a, b, gap)
            else:
                g.after(a, b, gap)
        for i, cell in enumerate(cells):
            _same_symbol(g, pc, li, i, cell)


def join_constraints(g: Graph, env: PageEnv) -> None:
    """A folded parallel member stands level with the cell its head join names."""
    for column in env.flow.columns:
        pc = env.pcs.get(column.id)
        if pc is None:
            continue
        where = {c.sym: (li, i) for li, cells in enumerate(pc.lanes) for i, c in enumerate(cells)}
        for li, end in enumerate(column.heads):
            if end.is_join and end.pin is not None:
                lane, index = where[end.pin.sym]
                g.equal(cell_node(pc.id, lane, index), cell_node(pc.id, li, 0), 0)


def _held(g: Graph, r: int, env: PageEnv, node: str, extent_: tuple[int, int]) -> None:
    """A symbol's `extent` stays inside its row: below its top, above the next row's top."""
    g.after(f"row:{r}", node, extent_[0])
    g.after(node, f"row:{r + 1}", extent_[1] + env.options.row_gap)


def _row_constraints(g: Graph, r: int, env: PageEnv) -> None:
    """Every cell's extent with its room stays inside the row; the top keeps the row's headroom."""
    step = env.options.wiring_grid
    for col in env.plan.rows[r].columns:
        pc = env.pcs[col]
        for li, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                room = env.rooms.get(cell.sym, Room())
                held = extent(_footprint(env, cell), room, env.options)
                _held(g, r, env, cell_node(pc.id, li, i), held)
    g.at_least(
        f"row:{r}",
        max(env.options.top_headroom, grid_up(row_rooms(env).get(r, Room()).up + step, step)),
    )


def _edge(env: PageEnv, col: str, row: RowPlan) -> str:
    """The edge of the box the attached column's pin uses in this row."""
    box, pin, _ = env.attach[col]
    for b in row.blocks:
        if env.blocks[b].anchor == box:
            return dict(env.blocks[b].pin_edges).get(pin, "S")
    return "S"


def _attach_y(
    g: Graph, pc: PlacedColumn, env: PageEnv, *, above: bool, slack: bool = False
) -> None:
    """An attached column hangs wire_min under the box's S edge, or stands over its N edge.

    A `slack` column hangs at least that far: a trunk of a foreign fan runs between it and the box.
    """
    box = env.attach[pc.id][0]
    body, cells = env.syms[box].body, pc.lanes[0]
    if above:
        dy = _pin_y(env, cells[-1], cells[-1].bottom_pin)
        g.equal(
            box_y_node(box), cell_node(pc.id, 0, len(cells) - 1), body.y - env.options.wire_min - dy
        )
    else:
        dy = _pin_y(env, cells[0], cells[0].top_pin)
        at = box_y_node(box), cell_node(pc.id, 0, 0), body.y + body.h + env.options.wire_min - dy
        g.after(*at) if slack else g.equal(*at)


def _box_y(g: Graph, r: int, env: PageEnv, box: str) -> None:
    held = extent(env.syms[box].footprint, env.rooms.get(box, Room()), env.options)
    _held(g, r, env, box_y_node(box), held)


def _row_graph(
    g: Graph, r: int, env: PageEnv, rooms: Mapping[Step, int], free: tuple[AbstractSet[str], ...]
) -> None:
    """`free` holds the loose columns, then the attached columns that hang at least wire_min."""
    (loose, slack), row = free, env.plan.rows[r]
    _row_constraints(g, r, env)
    for col in row.columns:
        above = col in env.attach and _edge(env, col, row) == "N"
        stack_constraints(g, env.pcs[col], env, rooms, rigid=above and col not in loose)
        if col in env.attach:
            _attach_y(g, env.pcs[col], env, above=above, slack=col in slack)
    for b in row.blocks:
        if env.blocks[b].is_card:
            _box_y(g, r, env, env.blocks[b].anchor or "")


def _y_graph(
    env: PageEnv,
    spans: Sequence[Span],
    give: tuple[AbstractSet[str], ...],
    rooms: Mapping[Step, int],
    crossed: CrossedRooms,
) -> tuple[Graph, frozenset[str], frozenset[str]]:
    """The page graph, the trunks with a leg refused, and the trunks at a level edge.

    `give` holds the tangled trunks, then the attached columns that hang at least wire_min.
    """
    g, (tangled, slack) = Graph(), give
    free = (loose_columns(env, tangled), slack)
    for r in range(len(env.plan.rows)):
        _row_graph(g, r, env, rooms, free)
    join_constraints(g, env)
    refused = frozenset[str]().union(
        *(trunk_constraints(g, f, env, tangled, crossed) for f in env.flow.fans)
    )
    return g, refused, trunk_levels(g, spans, env.options)


def _xs(
    env: PageEnv, x: Mapping[str, int], ends: tuple[Fan, Sequence[Attach]], r: int
) -> tuple[int, ...]:
    """The x of each attachment of a fan on its row-r trunk (`in_row`): a lane or a card's pin.

    A box pin with no card has no x node yet; it is skipped, as before.
    """
    fan, atts = ends
    out = []
    for a in (a for a in atts if in_row(env, fan, a, r)):
        if a.column is None:
            if box_at(env, a.pin.sym) is not None:
                out.append(box_pin_x(env, x, a.pin.sym, a.pin.pin))
        else:
            out.append(x[col_node(a.column)] + env.pcs[a.column].offsets[a.lane])
    return tuple(out)


def _spans(env: PageEnv, x: Mapping[str, int]) -> list[Span]:
    """Each fan's x span per row, from its column attachments and its box pins."""
    out = []
    for fan in env.flow.fans:
        roles, side = fan_roles(env, fan), fan_side(env, fan)
        for r in range(len(env.plan.rows)):
            drivers, legs = _xs(env, x, (fan, roles[0]), r), _xs(env, x, (fan, roles[1]), r)
            if drivers or legs:
                xs = (*drivers, *legs)
                left, right = arrow_ends(env.refs, env.plan.page, r, fan.id)
                lo, hi = min(xs) - reserve(left, env.options), max(xs) + reserve(right, env.options)
                out.append(Span(fan.id, r, lo, hi, fan.lanes, side, drivers, legs))
    return out


def _settle(
    env: PageEnv, spans: Sequence[Span], rooms: Mapping[Step, int], crossed: CrossedRooms
) -> tuple[frozenset[str], frozenset[str]]:
    """Rebuild with each newly found tangled trunk until none is new; (tangled, refused)."""
    tangled: frozenset[str] = frozenset[str]()
    refused: frozenset[str] = frozenset[str]()
    while True:
        g, round_refused, lowered = _y_graph(env, spans, (tangled, frozenset()), rooms, crossed)
        refused |= round_refused
        found = round_refused | lowered | tangled_trunks(g)
        if found <= tangled:
            return tangled, refused
        tangled |= found


def _dropped(env: PageEnv, align: Align) -> Finding:
    return Finding("ALIGN_DROPPED", align.note, env.plan.page, align.subject)


def _unmet(env: PageEnv) -> list[Finding]:
    text = (
        "mate {}: its halves are not cells of one row of this page; dropped, put both "
        "symbols in cells of one row (a box pin cannot be mated)"
    )
    pairs = [f"{a.sym}.{a.pin}/{b.sym}.{b.pin}" for a, b in unmet_mates(env)]
    return [Finding("ALIGN_DROPPED", text.format(p), env.plan.page, p) for p in pairs]


def _loosened(env: PageEnv, trunks: AbstractSet[str]) -> list[Finding]:
    text = "{}: leg alignment contradicts the stacks; dropped, the legs hang loose under the trunk"
    return [
        Finding("ALIGN_DROPPED", text.format(t), env.plan.page, t)
        for t in sorted(trunks, key=natural_key)
    ]


def _cycle_text(env: PageEnv, base: Graph) -> str:
    """Name the page and the symbols of the ring (their problem keys), and the fix."""
    keys = ", ".join(sorted(ring_symbols(env, base), key=natural_key)) or "none found"
    return (
        f"page {env.plan.page}: cyclic y constraints through symbols {keys}: a column feeds its "
        "own head through a fan, or a card box ties fans into a ring; split the ring in stage 1 "
        "(cycle split) so no column loops back"
    )


def _steps(
    env: PageEnv, x: Mapping[str, int], spans: Sequence[Span], crossed: CrossedRooms
) -> dict[Step, int]:
    """Each pair of cells keeps the larger y step of its jogs and of the flags between its pins.

    A foot join with no row of its own adds its step (R456): the page is solved once without it.
    """
    jogs, flags = step_rooms(env, x), pair_steps(env)
    first = {k: max(jogs.get(k, 0), flags.get(k, 0)) for k in jogs.keys() | flags.keys()}
    g, _, _ = _y_graph(env, spans, (frozenset(), frozenset()), first, crossed)
    solved = accept(g, page_aligns(env))
    joins = join_rooms(env, origins(env, x), solved.y) if solved else {}
    jogs |= {k: max(jogs.get(k, 0), v) for k, v in joins.items()}
    return {k: max(jogs.get(k, 0), flags.get(k, 0)) for k in jogs.keys() | flags.keys()}


def place_y(env: PageEnv, x: Mapping[str, int]) -> tuple[dict[str, int], tuple[Finding, ...]]:
    """The y of every cell, box, row and trunk node of the page, and the alignments dropped.

    Raises YCycleError (a CoreError) when the stacks and trunks alone are cyclic.
    """
    spans, crossed = _spans(env, x), crossed_levels(env, x)
    rooms = _steps(env, x, spans, crossed)
    tangled, refused = _settle(env, spans, rooms, crossed)
    base, _, _ = _y_graph(env, spans, (tangled, frozenset()), rooms, crossed)
    pushed = clear_foreign(base, env, x, spans)
    result = accept(base, page_aligns(env))
    slack = {c for c in env.attach if any(n.startswith(f"cell:{c}:") for n in pushed)}
    if result is None and slack:
        base, _, _ = _y_graph(env, spans, (tangled, slack), rooms, crossed)
        clear_foreign(base, env, x, spans)
        result = accept(base, page_aligns(env))
    if result is None:
        raise YCycleError(_cycle_text(env, base))
    findings = (*_loosened(env, refused), *_unmet(env), *(_dropped(env, a) for a in result.dropped))
    return result.y, findings
