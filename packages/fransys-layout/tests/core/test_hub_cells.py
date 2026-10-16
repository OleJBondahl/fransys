"""P1-3B plant: a fan's hub terminals stand in a cell of the fan's columns (layout-0282).

The shape is the p02 gap: a box wired to a trunk by its pin alone (`Attach.column` None) and
three terminals on that trunk. Before the fix the first terminal was dealt as the hub of a lane
the trunk does not have, and dropped: it stood in no cell, so no block held it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core.topology_check import cell_findings
from fransys_layout.core.topology_elements import Elem

from .flow_builders import free, net, problem
from .pipeline_fixtures import blocks_of, flow_of
from .topology_fixtures import box

if TYPE_CHECKING:
    from fransys_layout.core.values import FlowGraph, PlacementProblem

TERMINALS = ("T1", "T2", "T3")


def hub_shape() -> PlacementProblem:
    """A box K, one trunk on its pin s alone, and a fan of three terminals on that trunk."""
    syms = [box("K"), *(free(t) for t in TERMINALS)]
    return problem(syms, [net("trunk", "K.s", *(f"{t}.e" for t in TERMINALS))])


def _cells_of(flow: FlowGraph, sym: str) -> list[str]:
    return [
        col.id
        for col in flow.columns
        for lane in col.lanes
        for cell in lane.cells
        if cell.sym == sym
    ]


def test_every_drawn_symbol_stands_in_one_cell_and_a_hub_in_its_fans_column() -> None:
    flow = flow_of(hub_shape())
    assert set(flow.drawn) == {"K", *TERMINALS}
    for sym in TERMINALS:
        assert len(_cells_of(flow, sym)) == 1, sym
    fan = flow.fans[0]
    fan_cols = {a.column for a in (*fan.drivers, *fan.legs) if a.column}
    assert {c for t in TERMINALS for c in _cells_of(flow, t)} <= fan_cols


def test_every_drawn_symbol_is_held_and_the_trunk_wired_box_is_a_card_with_no_column() -> None:
    """A terminal is held by its cell's block; the box K, in no cell, by a card of its own (C2)."""
    prob = hub_shape()
    flow = flow_of(prob)
    blocks = [b for bl in blocks_of(prob) for b in bl.blocks]
    held = {b.anchor for b in blocks if b.anchor}
    for b in blocks:
        for col_id in b.columns:
            held |= {
                c.sym
                for col in flow.columns
                if col.id == col_id
                for ln in col.lanes
                for c in ln.cells
            }
    assert set(flow.drawn) - held == set()
    assert [(b.kind, b.anchor, b.columns) for b in blocks if b.kind == "card"] == [
        ("card", "K", ())
    ]


def test_a_flow_with_every_symbol_in_its_cells_has_no_finding() -> None:
    assert flow_of(hub_shape()).findings == ()


def test_a_drawn_symbol_in_no_cell_or_two_gives_one_no_cell_finding_naming_it() -> None:
    flow = flow_of(hub_shape())
    syms = {s.id: s for s in hub_shape().symbols}
    elems = {t: Elem(t, t, "free", "n", "s") for t in TERMINALS}
    first = flow.columns[0]
    twice = replace(first, lanes=(first.lanes[0], first.lanes[0]))
    none = cell_findings(syms, elems, flow.columns[1:])
    two = cell_findings(syms, elems, [twice, *flow.columns[1:]])
    assert [(f.code, f.subject) for f in none] == [("NO_CELL", "T1")]
    assert [f.subject for f in two] == ["T1"]
