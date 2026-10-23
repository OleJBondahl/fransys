"""Stage 5, x: each planned row solved by the row graph; a row wider than the page is named."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .arrow_reserve import arrow_ends, reserve
from .marker_room import column_rooms
from .pack_row import extent, solve_row
from .rowspec import one_row
from .values import Finding

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .pack_row import RowSpec
    from .place_env import PageEnv
    from .room import Room


def row_specs(env: PageEnv) -> tuple[RowSpec, ...]:
    """One RowSpec per planned row, built by the one home of "a row"."""
    out: list[RowSpec] = []
    rooms = column_rooms(env)
    for index, row in enumerate(env.plan.rows):
        spec = one_row(
            row.columns, [env.blocks[b] for b in row.blocks], env.flow, env.problem, env.options
        )
        left, right = arrow_ends(env.refs, env.plan.page, index)
        floors, tail = _fitted_floors(spec, rooms)
        out.append(
            replace(
                spec,
                floors=floors,
                reserves=dict(env.reserves),
                lead_extra=reserve(left, env.options),
                tail_extra=max(reserve(right, env.options), tail),
            )
        )
    return tuple(out)


def _fitted_floors(
    spec: RowSpec, rooms: Mapping[str, list[tuple[int, Room]]]
) -> tuple[dict[str, int], int]:
    """The least x of each column with a fitted box, and the tail its widest right reach needs."""
    floors: dict[str, int] = {}
    tail = 0
    for col in spec.cols:
        for off, room in rooms.get(col, ()):
            floors[col] = max(floors.get(col, 0), room.left - off)
            if col == spec.cols[-1]:
                tail = max(tail, room.right + off - extent(spec, col)[1])
    return floors, tail


def _wider(env: PageEnv, index: int, overflow: int) -> Finding:
    first = env.plan.rows[index].blocks[0]
    text = (
        f"page {env.plan.page}, row {index}: {overflow} G wider than the page; shorten the row, "
        "lower the column count of the block, raise the page width or set Options.short_height"
    )
    return Finding("WIDER_THAN_PAGE", text, env.plan.page, first)


def place_x(env: PageEnv) -> tuple[dict[str, int], tuple[Finding, ...]]:
    """The x of every node of the page and a finding per row past the page; never raises."""
    x: dict[str, int] = {}
    findings: list[Finding] = []
    for index, spec in enumerate(row_specs(env)):
        row_x, overflow = solve_row(spec, env.problem.area.w)
        x.update(row_x)
        if overflow > 0:
            findings.append(_wider(env, index, overflow))
    return x, tuple(findings)
