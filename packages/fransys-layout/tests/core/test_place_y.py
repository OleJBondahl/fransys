"""Stage 5, y: stacks, legs at depth, no overlaps, row groups level or dropped."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations, pairwise
from typing import TYPE_CHECKING

from fransys_layout.core import Box, Options, PlacementProblem
from fransys_layout.core.geometry import (
    cell_anchor,
    cell_footprint,
    overlaps,
    pin_xy,
    shift,
)
from fransys_layout.core.pack import cell_node
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import grid_up, place_y

from .cut_fixtures import AREA, box_sym, elem
from .flow_builders import net
from .place_fixtures import bundle_fan, card_with_coils, row_group_three
from .test_place_x import env_of

if TYPE_CHECKING:
    from fransys_layout.core.place_env import PageEnv
    from fransys_layout.core.values import Finding


def solved(
    prob: PlacementProblem, options: Options | None = None
) -> tuple[PageEnv, dict[str, int], tuple[Finding, ...]]:
    """The env, y and findings of the first page of a problem."""
    env = env_of(prob, options)
    x, _ = place_x(env)
    y, findings = place_y(env, x)
    return env, y, findings


def _footprints(env: PageEnv, y: dict[str, int]) -> list[tuple[str, int, int, Box]]:
    """(symbol, lane, index, absolute footprint) of every placed cell of the page."""
    x, _ = place_x(env)
    out = []
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                sym = env.syms[cell.sym]
                ax, _ = cell_anchor(sym, cell)
                fp = cell_footprint(sym, cell, in_row=cell.sym in env.in_row)
                ox = x[f"col:{pc.id}"] + pc.offsets[li] - ax
                out.append((pc.id, li, i, shift(fp, ox, y[cell_node(pc.id, li, i)])))
    return out


def test_a_bundle_trunks_legs_hang_at_eight_times_lanes_under_it() -> None:
    """Every leg pin lies grid * lanes under the trunk, exactly: legs are equal at that depth."""
    env, y, findings = solved(bundle_fan())
    (fan,) = env.flow.fans
    assert fan.lanes == 3
    assert findings == ()
    for a in fan.legs:
        assert a.column is not None
        pc = env.pcs[a.column]
        cell = pc.lanes[a.lane][a.cell]
        dy = pin_xy(env.syms[cell.sym], cell, a.pin.pin)[1]
        trunk = y[f"trunk:{fan.id}:{pc.row}"]
        assert y[cell_node(pc.id, a.lane, a.cell)] + dy == trunk + env.options.wiring_grid * 3


def test_no_two_footprints_of_one_row_overlap_in_y_and_x() -> None:
    """No two cells overlap, and the cells of one lane keep wire_min between footprints."""
    for prob in (card_with_coils(), row_group_three("X1")):
        env, y, _ = solved(prob)
        feet = _footprints(env, y)
        for (_, _, _, a), (_, _, _, b) in combinations(feet, 2):
            assert not overlaps(a, b)
        lanes = {}
        for col, li, _, fp in feet:
            lanes.setdefault((col, li), []).append(fp)
        for fps in lanes.values():
            assert all(b.y - (a.y + a.h) >= env.options.wire_min for a, b in pairwise(fps))


def _head_ys(env: PageEnv, y: dict[str, int]) -> list[int]:
    return [y[cell_node(pc.id, 0, 0)] for pc in env.pcs.values()]


def test_row_group_members_at_the_same_end_share_one_y() -> None:
    """The three hubs of group X1 stand level; the same hubs outside a group do not."""
    env, y, findings = solved(row_group_three("X1"))
    assert findings == ()
    assert len(set(_head_ys(env, y))) == 1
    env, y, _ = solved(row_group_three(None))
    assert len(set(_head_ys(env, y))) > 1


def _two_heights() -> PlacementProblem:
    """Two coils of different heights hang on one box, both in row group G."""
    coils = [replace(elem("k1", 84, 32), row_group="G"), replace(elem("k2", 84, 48), row_group="G")]
    nets = [net(f"c{i}", f"A1.p{i}", f"k{i}.n") for i in (1, 2)]
    return PlacementProblem(AREA, (box_sym(2), *coils), tuple(nets))


def test_a_row_group_that_contradicts_a_stack_is_dropped_with_the_finding() -> None:
    """Both coils hang wire_min under the box, so their origins differ; level would break that."""
    env, y, findings = solved(_two_heights())
    assert [(f.code, f.subject, f.page) for f in findings] == [
        ("ALIGN_DROPPED", "G", env.plan.page)
    ]
    assert "row group G" in findings[0].text
    box = env.syms["A1"].body
    for col in ("c:k1", "c:k2"):
        pc = env.pcs[col]
        cell = pc.lanes[0][0]
        dy = pin_xy(env.syms[cell.sym], cell, "n")[1]
        wire = env.options.wire_min
        assert y[cell_node(col, 0, 0)] + dy == y["box:A1"] + box.y + box.h + wire
    assert y[cell_node("c:k1", 0, 0)] != y[cell_node("c:k2", 0, 0)]


def test_place_y_is_deterministic() -> None:
    """Two runs give the same y, in the same key order."""
    for prob in (bundle_fan(), card_with_coils(), row_group_three("X1"), _two_heights()):
        _, y1, f1 = solved(prob)
        _, y2, f2 = solved(prob)
        assert list(y1.items()) == list(y2.items())
        assert f1 == f2


def test_grid_up_rounds_to_the_next_step() -> None:
    assert [grid_up(v, 8) for v in (-9, -8, -1, 0, 1, 8, 9)] == [-8, -8, 0, 0, 8, 8, 16]
