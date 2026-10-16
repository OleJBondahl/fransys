"""Stage 5, y: one constraint graph per page; stacks, trunks between, row groups level."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constraints import Graph
from .geometry import cell_footprint, pin_xy
from .keys import natural_key
from .pack import cell_node
from .place_accept import accept
from .place_align import page_aligns, unmet_mates
from .place_levels import Span, trunk_levels
from .place_trunk import loose_columns, tangled_trunks, trunk_constraints
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .pack import PlacedColumn
    from .place_align import Align
    from .place_env import PageEnv
    from .values import Attach, Box, Cell, RowPlan


class YCycleError(ValueError):
    """The stacks and trunks of a page are cyclic: stage 1 left a ring in a column."""


def grid_up(value: int, step: int) -> int:
    """Round up to the wiring grid, so every pin lands on it."""
    return -(-value // step) * step


def _footprint(env: PageEnv, cell: Cell) -> Box:
    return cell_footprint(env.syms[cell.sym], cell, in_row=cell.sym in env.in_row)


def _pin_y(env: PageEnv, cell: Cell, pin: str | None) -> int:
    return 0 if pin is None else pin_xy(env.syms[cell.sym], cell, pin)[1]


def _gap(env: PageEnv, above: Cell, below: Cell) -> int:
    fa, fb = _footprint(env, above), _footprint(env, below)
    wire = env.options.wire_min
    by_box = fa.y + fa.h + wire - fb.y
    pa = (
        pin_xy(env.syms[above.sym], above, above.bottom_pin)[1] if above.bottom_pin else fa.y + fa.h
    )
    pb = _pin_y(env, below, below.top_pin) if below.top_pin else fb.y
    return grid_up(max(by_box, pa + wire - pb), env.options.wiring_grid)


def _same_symbol(g: Graph, pc: PlacedColumn, lane: int, index: int, cell: Cell) -> None:
    """A symbol that spans lanes (a three-pole device) is one node in y."""
    for lj in range(lane):
        for j, other in enumerate(pc.lanes[lj]):
            if other.sym == cell.sym:
                g.equal(cell_node(pc.id, lj, j), cell_node(pc.id, lane, index), 0)
                return


def stack_constraints(g: Graph, pc: PlacedColumn, env: PageEnv, *, rigid: bool) -> None:
    """Consecutive cells keep wire_min between footprints and between their pins."""
    for li, cells in enumerate(pc.lanes):
        for i in range(1, len(cells)):
            a, b = cell_node(pc.id, li, i - 1), cell_node(pc.id, li, i)
            gap = _gap(env, cells[i - 1], cells[i])
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


def _row_constraints(g: Graph, r: int, env: PageEnv) -> None:
    """Every footprint stays below its row top; the next row top clears every footprint."""
    step = env.options.wiring_grid
    for col in env.plan.rows[r].columns:
        pc = env.pcs[col]
        for li, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                fp, node = _footprint(env, cell), cell_node(pc.id, li, i)
                g.after(f"row:{r}", node, grid_up(-fp.y, step))
                g.after(node, f"row:{r + 1}", grid_up(fp.y + fp.h, step) + env.options.row_gap)
    g.at_least(f"row:{r}", env.options.margin.h)


def _edge(env: PageEnv, col: str, row: RowPlan) -> str:
    """The edge of the box the attached column's pin uses in this row."""
    box, pin, _ = env.attach[col]
    for b in row.blocks:
        if env.blocks[b].anchor == box:
            return dict(env.blocks[b].pin_edges).get(pin, "S")
    return "S"


def _attach_y(g: Graph, pc: PlacedColumn, env: PageEnv, *, above: bool) -> None:
    """An attached column hangs wire_min under the box's S edge, or stands over its N edge."""
    box = env.attach[pc.id][0]
    body, cells = env.syms[box].body, pc.lanes[0]
    if above:
        dy = _pin_y(env, cells[-1], cells[-1].bottom_pin)
        g.equal(
            f"box:{box}", cell_node(pc.id, 0, len(cells) - 1), body.y - env.options.wire_min - dy
        )
    else:
        dy = _pin_y(env, cells[0], cells[0].top_pin)
        g.equal(f"box:{box}", cell_node(pc.id, 0, 0), body.y + body.h + env.options.wire_min - dy)


def _box_y(g: Graph, r: int, env: PageEnv, box: str) -> None:
    fp, step = env.syms[box].footprint, env.options.wiring_grid
    g.after(f"row:{r}", f"box:{box}", grid_up(-fp.y, step))
    g.after(f"box:{box}", f"row:{r + 1}", grid_up(fp.y + fp.h, step) + env.options.row_gap)


def _row_graph(g: Graph, r: int, env: PageEnv, loose: AbstractSet[str]) -> None:
    row = env.plan.rows[r]
    _row_constraints(g, r, env)
    for col in row.columns:
        above = col in env.attach and _edge(env, col, row) == "N"
        stack_constraints(g, env.pcs[col], env, rigid=above and col not in loose)
        if col in env.attach:
            _attach_y(g, env.pcs[col], env, above=above)
    for b in row.blocks:
        if env.blocks[b].is_card:
            _box_y(g, r, env, env.blocks[b].anchor or "")


def _y_graph(
    env: PageEnv, spans: Sequence[Span], tangled: AbstractSet[str]
) -> tuple[Graph, frozenset[str]]:
    """The page graph and the trunks to loosen: a leg refused, or a trunk edge tangled."""
    g = Graph()
    loose = loose_columns(env, tangled)
    for r in range(len(env.plan.rows)):
        _row_graph(g, r, env, loose)
    join_constraints(g, env)
    refused = frozenset[str]().union(
        *(trunk_constraints(g, f, env, tangled) for f in env.flow.fans)
    )
    trunk_levels(g, spans, env.options)
    return g, refused


def _xs(env: PageEnv, x: Mapping[str, int], ends: Sequence[Attach], r: int) -> tuple[int, ...]:
    return tuple(
        x[f"col:{a.column}"] + env.pcs[a.column].offsets[a.lane]
        for a in ends
        if a.column is not None and a.column in env.pcs and env.pcs[a.column].row == r
    )


def _spans(env: PageEnv, x: Mapping[str, int]) -> list[Span]:
    """Each fan's x span per row, from its column attachments (box pins are not placed yet)."""
    out = []
    for fan in env.flow.fans:
        for r in range(len(env.plan.rows)):
            drivers, legs = _xs(env, x, fan.drivers, r), _xs(env, x, fan.legs, r)
            if drivers or legs:
                xs = (*drivers, *legs)
                out.append(Span(fan.id, r, min(xs), max(xs), fan.lanes, fan.side, drivers, legs))
    return out


def _settle(env: PageEnv, spans: Sequence[Span]) -> tuple[frozenset[str], frozenset[str]]:
    """Rebuild with each newly found tangled trunk until none is new; (tangled, refused)."""
    tangled: frozenset[str] = frozenset[str]()
    refused: frozenset[str] = frozenset[str]()
    while True:
        g, round_refused = _y_graph(env, spans, tangled)
        refused |= round_refused
        found = round_refused | tangled_trunks(g)
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


def _cycle_text(env: PageEnv) -> str:
    """Name the page and the columns a fan feeds back into (the ring), and the fix."""
    rings = {
        a.column
        for f in env.flow.fans
        for a in f.drivers
        if a.column is not None and a.column in env.pcs and a.column in {x.column for x in f.legs}
    }
    where = f"columns {', '.join(sorted(rings, key=natural_key))}" if rings else "no ring column"
    return (
        f"page {env.plan.page}: cyclic y constraints ({where}): a column feeds its own head "
        "through a fan; split the ring in stage 1 (cycle split) so no column loops back"
    )


def place_y(env: PageEnv, x: Mapping[str, int]) -> tuple[dict[str, int], tuple[Finding, ...]]:
    """The y of every cell, box, row and trunk node of the page, and the alignments dropped.

    Raises YCycleError (a ValueError) when the stacks and trunks alone are cyclic.
    """
    spans = _spans(env, x)
    tangled, refused = _settle(env, spans)
    base, _ = _y_graph(env, spans, tangled)
    result = accept(base, page_aligns(env))
    if result is None:
        raise YCycleError(_cycle_text(env))
    findings = [*_loosened(env, refused), *_unmet(env)]
    findings.extend(_dropped(env, a) for a in result.dropped)
    return result.y, tuple(findings)
