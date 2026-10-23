"""Stage 1: lanes of one column are offset through every symbol they share (layout-0370, R347)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core.topology import build_flow

from .flow_builders import elem, net, poles, problem

if TYPE_CHECKING:
    from fransys_layout.core.values import FlowGraph, Net


def flow_of(syms: list, nets: list[Net]) -> FlowGraph:
    return build_flow(
        problem(syms, nets),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def offsets(flow: FlowGraph, *syms: str) -> list[int]:
    """The offsets of the lanes that hold one of `syms`, in lane order."""
    return [
        lane.offset
        for column in flow.columns
        for lane in column.lanes
        if any(c.sym in syms for c in lane.cells)
    ]


def two_shared_symbols() -> FlowGraph:
    """Poles a and b; lane a0-u0 holds only a, lanes b0-b2 only b, a bridge holds both at pole 3."""
    syms = [
        poles("a", 4),
        poles("b", 4),
        *(elem(n) for n in ("u0", "m", "t0", "t1", "t2")),
    ]
    nets = [
        net("na", "a.s0", "u0.n"),
        net("nb", "a.s3", "m.n"),
        net("nc", "m.s", "b.n3"),
        *(net(f"nt{k}", f"b.s{k}", f"t{k}.n") for k in range(3)),
    ]
    return flow_of(syms, nets)


def test_lanes_that_share_only_the_second_symbol_keep_their_pole_spacing() -> None:
    """The first-binder rule gave the three b lanes one offset; their feet stood on each other."""
    feet = offsets(two_shared_symbols(), "t0", "t1", "t2")
    assert [o - feet[0] for o in feet] == [0, 24, 48]


def test_a_second_path_that_disagrees_keeps_the_first_path_and_says_nothing() -> None:
    syms = [poles("a", 3), poles("b", 3), elem("m1"), elem("m2")]
    nets = [
        net("n1", "a.s0", "m1.n"),
        net("n2", "m1.s", "b.n0"),
        net("n3", "a.s1", "m2.n"),
        net("n4", "m2.s", "b.n2"),
    ]
    flow = flow_of(syms, nets)
    assert not flow.findings
    assert offsets(flow, "m1", "m2") == [0, 24]
