"""FLOW-DOWN: a column hung under a card box stands lower when a foreign trunk passes over it."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.geometry import cell_anchor
from fransys_layout.core.node_names import box_y_node, col_node
from fransys_layout.core.pack import cell_node
from fransys_layout.core.pack_sep import hard_soft
from fransys_layout.core.place_trunk import trunk_node
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import _spans, place_y

from .cut_fixtures import AREA, box_sym, elem
from .flow_builders import net
from .test_place_x import env_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_layout.core.place_env import PageEnv


def _trunk_over_a_hung_column() -> PlacementProblem:
    """Box pin p1 fans to k1 and k3, and s2 hangs on pin p4: a foreign cell near the trunk."""
    syms = (box_sym(4), *(elem(s, 40) for s in ("k1", "s2", "k3")))
    nets = [net("v", "A1.p1", "k1.n", "k3.n"), net("sig", "A1.p4", "s2.n")]
    return PlacementProblem(AREA, syms, tuple(nets), Facts())


def test_a_trunk_over_a_hung_column_lifts_the_column_not_a_y_cycle() -> None:
    env = env_of(_trunk_over_a_hung_column())
    x, _ = place_x(env)
    y, findings = place_y(env, x)
    assert findings == ()
    box = env.syms["A1"].body
    assert y[cell_node("c:s2", 0, 0)] > y[box_y_node("A1")] + box.y + box.h


def _held_crossing() -> PlacementProblem:
    """s1 hangs on box pin p2 and drives its own fan; p1's fan runs right, over s1's x."""
    syms = (box_sym(4), *(elem(s) for s in ("s1", "k2", "k3", "k4", "k5")))
    nets = [
        net("a", "A1.p2", "s1.n"),
        net("b", "s1.s", "k2.n", "k3.n"),
        net("c", "A1.p1", "k4.n", "k5.n"),
    ]
    return PlacementProblem(AREA, syms, tuple(nets), Facts())


def _lines_in_bodies(env: PageEnv, x: Mapping[str, int], y: Mapping[str, int]) -> list[str]:
    """Each (trunk, cell) where a trunk line lies in the hard box of a cell its fan skips."""
    out = []
    for span in _spans(env, x):
        fan = next(f for f in env.flow.fans if f.id == span.fan)
        own = {a.pin.sym for a in (*fan.drivers, *fan.legs)}
        line = y[trunk_node(span.fan, span.row)]
        for col in env.plan.rows[span.row].columns:
            pc = env.pcs[col]
            for lane, cells in enumerate(pc.lanes):
                for i, cell in enumerate(cells):
                    sym = env.syms[cell.sym]
                    hard, _ = hard_soft(sym, cell, in_row=cell.sym in env.in_row, tag_stagger=True)
                    left = x[col_node(col)] + pc.offsets[lane] - cell_anchor(sym, cell)[0] + hard.x
                    top = y[cell_node(pc.id, lane, i)] + hard.y
                    meets = left < span.x1 and span.x0 < left + hard.w
                    if cell.sym not in own and meets and top <= line <= top + hard.h:
                        out.append(f"{span.fan} in {cell.sym}")
    return out


@pytest.mark.rule("FLOW-DOWN")
@pytest.mark.parametrize("make", [_trunk_over_a_hung_column, _held_crossing])
def test_no_trunk_line_runs_in_a_body_its_fan_does_not_attach_to(
    make: Callable[[], PlacementProblem],
) -> None:
    """Whole class: a cell another fan holds is still foreign to this fan's trunk."""
    env = env_of(make())
    x, _ = place_x(env)
    y, _ = place_y(env, x)
    assert _spans(env, x)
    assert _lines_in_bodies(env, x, y) == []
