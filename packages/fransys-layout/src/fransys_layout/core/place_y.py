"""Stage 5, y: one constraint graph per page; stacks, trunks between, row groups level."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .arrow_reserve import reserve
from .clearance import Keep, reach
from .constraints import Graph
from .cut_end_rooms import arrow_ends
from .errors import CoreError
from .geometry import cell_footprint, pin_xy, union, view_of
from .keys import natural_key
from .marker_flags import pair_steps
from .node_names import box_y_node, col_node
from .pack import box_edge, cell_node
from .place_accept import accept
from .place_align import page_aligns, unmet_mates
from .place_foreign import clear_foreign
from .place_levels import Span, trunk_levels
from .place_ring import ring_symbols
from .place_room import Step, crossed_levels, step_rooms
from .place_trunk import (
    anchors_under,
    box_at,
    box_pin_x,
    fan_roles,
    fan_side,
    in_row,
    loose_columns,
    tangled_trunks,
    trunk_constraints,
)
from .row_extent import grid_up, held
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .flow_values import Attach, Cell, Fan
    from .pack import PlacedColumn
    from .place_align import Align
    from .place_env import PageEnv
    from .place_room import CrossedRooms
    from .values import Box


class YCycleError(CoreError):
    """The y constraints of a page are cyclic: a ring left in stage 1, or a stage 5 foreign clearance against the hard order."""


def _footprint(env: PageEnv, cell: Cell) -> Box:
    return cell_footprint(env.syms[cell.sym], cell, in_row=cell.sym in env.in_row)


def _pin_y(env: PageEnv, cell: Cell, pin: str | None) -> int:
    return 0 if pin is None else pin_xy(env.syms[cell.sym], cell, pin)[1]


def _gap(env: PageEnv, above: Cell, below: Cell, room: int = 0) -> int:
    fa, fb = _footprint(env, above), _footprint(env, below)
    wire = env.options.wire_min
    pins = max(wire, room)
    by_box = fa.y + fa.h + wire - fb.y
    pa = pin_xy(env.syms[above.sym], above, above.bottom_pin)[1] if above.bottom_pin else fa.y + fa.h
    pb = _pin_y(env, below, below.top_pin) if below.top_pin else fb.y
    return grid_up(max(by_box, pa + pins - pb) + below.hold, env.options.wiring_grid)


def _same_symbol(g: Graph, pc: PlacedColumn, lane: int, index: int, cell: Cell) -> None:
    """A symbol that spans lanes (a three-pair device) is one node in y."""
    for lj in range(lane):
        for j, other in enumerate(pc.lanes[lj]):
            if other.sym == cell.sym:
                g.equal(cell_node(pc.id, lj, j), cell_node(pc.id, lane, index), 0)
                return


def stack_constraints(g: Graph, pc: PlacedColumn, env: PageEnv, rooms: Mapping[Step, int], *, rigid: bool) -> None:
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
    """A folded parallel member stands with its head pin level with the pin its head join names.

    A join with no net or no head pin only stands the member level with the cell (cell tops equal).
    """
    for column in env.flow.columns:
        pc = env.pcs.get(column.id)
        if pc is None:
            continue
        where = {c.sym: (li, i) for li, cells in enumerate(pc.lanes) for i, c in enumerate(cells)}
        for li, end in enumerate(column.heads):
            if end.is_join and end.pin is not None:
                lane, index = where[end.pin.sym]
                member, target = pc.lanes[li][0], pc.lanes[lane][index]
                level = end.net is not None and member.top_pin is not None
                shift = _pin_y(env, target, end.pin.pin) - _pin_y(env, member, member.top_pin) if level else 0
                g.equal(cell_node(pc.id, lane, index), cell_node(pc.id, li, 0), shift)


def _held(g: Graph, r: int, env: PageEnv, node: str, extent_: tuple[int, int]) -> None:
    """A symbol's `extent` stays inside its row: below its top, above the next row's top."""
    g.after(f"row:{r}", node, extent_[0])
    g.after(node, f"row:{r + 1}", extent_[1] + env.options.row_gap)


def _row_constraints(g: Graph, r: int, env: PageEnv) -> None:
    """Every cell's extent, hangings included, stays inside the row; the top keeps the headroom."""
    for col in env.plan.rows[r].columns:
        pc = env.pcs[col]
        for li, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                extent = held(_footprint(env, cell), env.options)
                _held(g, r, env, cell_node(pc.id, li, i), extent)
    g.at_least(f"row:{r}", env.options.top_headroom)


def _attach_y(g: Graph, pc: PlacedColumn, env: PageEnv, *, above: bool, slack: bool = False) -> None:
    """An attached column hangs wire_min under the box's S edge, or stands over its N edge.

    A `slack` column hangs at least that far: a trunk of a foreign fan runs between it and the box.
    """
    box = env.attach[pc.id][0]
    body, cells = env.syms[box].body, pc.lanes[0]
    if above:
        dy = _pin_y(env, cells[-1], cells[-1].bottom_pin)
        wire = max(_box_gap(env, cells[-1], above=True, dy=dy), body.y - env.syms[box].footprint.y + env.options.wire_min)
        g.equal(box_y_node(box), cell_node(pc.id, 0, len(cells) - 1), body.y - wire - dy)
    else:
        dy = _pin_y(env, cells[0], cells[0].top_pin)
        wire = _box_gap(env, cells[0], above=False, dy=dy)
        at = box_y_node(box), cell_node(pc.id, 0, 0), body.y + body.h + wire - dy
        g.after(*at) if slack else g.equal(*at)


def _box_gap(env: PageEnv, cell: Cell, *, above: bool, dy: int) -> int:
    """wire_min, or the reach of the cell's keep-out or its footprint, hangings included."""
    view = view_of(env.syms[cell.sym], cell.orient)
    side = "below" if above else "above"
    hard = reach(dy, [Keep("", union(view.body, view.keepout), "keepout", cell.sym)], side, 0)
    foot = reach(dy, [Keep("", _footprint(env, cell), "footprint", cell.sym)], side, 0)
    return max(env.options.wire_min, hard, foot)


def _row_graph(g: Graph, r: int, env: PageEnv, rooms: Mapping[Step, int], free: tuple[AbstractSet[str], ...]) -> None:
    """`free` holds the loose columns, then the attached columns that hang at least wire_min."""
    (loose, slack), row = free, env.plan.rows[r]
    _row_constraints(g, r, env)
    for col in row.columns:
        above = col in env.attach and box_edge(env.blocks, row, *env.attach[col][:2]) == "N"
        stack_constraints(g, env.pcs[col], env, rooms, rigid=above and col not in loose)
        if col in env.attach:
            _attach_y(g, env.pcs[col], env, above=above, slack=col in slack)
    for b in row.blocks:
        if env.blocks[b].is_card:
            box = env.blocks[b].anchor or ""
            _held(g, r, env, box_y_node(box), held(env.syms[box].footprint, env.options))


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
    refused = frozenset[str]().union(*(trunk_constraints(g, f, env, tangled, crossed) for f in _trunked(env)))
    return g, refused, trunk_levels(g, spans, env.options)


def _xs(env: PageEnv, x: Mapping[str, int], ends: tuple[Fan, Sequence[Attach]], r: int) -> tuple[int, ...]:
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
    for fan in _trunked(env):
        roles, side = fan_roles(env, fan), fan_side(env, fan)
        for r in range(len(env.plan.rows)):
            drivers, legs = _xs(env, x, (fan, roles[0]), r), _xs(env, x, (fan, roles[1]), r)
            if drivers or legs:
                xs = (*drivers, *legs)
                left, right = arrow_ends(env.refs, env.plan, (fan,), r)
                lo, hi = min(xs) - reserve(left, env.options), max(xs) + reserve(right, env.options)
                out.append(Span(fan.id, r, lo, hi, fan.lanes, side, drivers, legs))
    return out


def _settle(env: PageEnv, spans: Sequence[Span], rooms: Mapping[Step, int], crossed: CrossedRooms) -> tuple[frozenset[str], frozenset[str]]:
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
    text = "mate {}: its halves are not cells of one row of this page; dropped, put both symbols in cells of one row (a box pin cannot be mated)"
    pairs = [f"{a.sym}.{a.pin}/{b.sym}.{b.pin}" for a, b in unmet_mates(env)]
    return [Finding("ALIGN_DROPPED", text.format(p), env.plan.page, p) for p in pairs]


def _loosened(env: PageEnv, trunks: AbstractSet[str]) -> list[Finding]:
    text = "{}: leg alignment contradicts the stacks; dropped, the legs hang loose under the trunk"
    return [Finding("ALIGN_DROPPED", text.format(t), env.plan.page, t) for t in sorted(trunks, key=natural_key)]


def _cycle_text(env: PageEnv, base: Graph) -> str:
    """Name the page and the symbols of the ring (their problem keys), and the fix."""
    keys = ", ".join(sorted(ring_symbols(env, base), key=natural_key)) or "none found"
    return (
        f"page {env.plan.page}: cyclic y constraints through symbols {keys}: a column feeds its "
        "own head through a fan, or a card box ties fans into a ring (split it in stage 1), "
        "or a stage 5 foreign clearance contradicts the hard order (a place_foreign defect: report it)"
    )


def _larger(jogs: Mapping[Step, int], flags: Mapping[Step, int]) -> dict[Step, int]:
    """Each pair of cells keeps the larger y step of its jogs and of the flags between its pins."""
    return {k: max(jogs.get(k, 0), flags.get(k, 0)) for k in jogs.keys() | flags.keys()}


def _steps(env: PageEnv, x: Mapping[str, int], spans: Sequence[Span], crossed: CrossedRooms) -> dict[Step, int]:
    """The y steps: a foot join with no row of its own is levelled with the jogs of its step (R456), the page solved once without it."""
    flags = pair_steps(env)
    first = _larger(step_rooms(env, x), flags)
    g, _, _ = _y_graph(env, spans, (frozenset(), frozenset()), first, crossed)
    solved = accept(g, page_aligns(env))
    return _larger(step_rooms(env, x, solved.y), flags) if solved else first


def _with_spans(env: PageEnv, x: Mapping[str, int]) -> tuple[PageEnv, list[Span], CrossedRooms]:
    """The env that knows which anchored pins each trunk runs over, the spans and the levels."""
    spans = _spans(env, x)
    return replace(env, under=anchors_under(env, x, spans)), spans, crossed_levels(env, x)


def place_y(env: PageEnv, x: Mapping[str, int]) -> tuple[dict[str, int], tuple[Finding, ...]]:
    """The y of every cell, box, row and trunk node of the page, and the alignments dropped.

    Raises YCycleError (a CoreError) when the stacks, trunks and foreign clearances are cyclic.
    """
    env, spans, crossed = _with_spans(env, x)
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


def _trunked(env: PageEnv) -> list[Fan]:
    """The fans that get a trunk: a row-cut TAG fan is wrapped by routing instead (layout-0529)."""
    return [f for f in env.flow.fans if f.id not in env.row_tags]
