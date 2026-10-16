"""Stage 5, x: each planned row solved by the row graph; a row wider than the page is named."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .arrow_reserve import arrow_ends, reserve
from .pack_row import solve_row
from .rowspec import one_row
from .values import Finding

if TYPE_CHECKING:
    from .pack_row import RowSpec
    from .place_env import PageEnv


def row_specs(env: PageEnv) -> tuple[RowSpec, ...]:
    """One RowSpec per planned row, built by the one home of "a row"."""
    out = []
    for index, row in enumerate(env.plan.rows):
        spec = one_row(
            row.columns, [env.blocks[b] for b in row.blocks], env.flow, env.problem, env.options
        )
        left, right = arrow_ends(env.refs, env.plan.page, index)
        out.append(
            replace(
                spec,
                reserves=dict(env.reserves),
                lead_extra=reserve(left, env.options),
                tail_extra=reserve(right, env.options),
            )
        )
    return tuple(out)


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
