"""Stage 1: lanes of one column are offset through every symbol they share (layout-0370, R347)."""

from __future__ import annotations

import itertools
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from .flow_builders import OPTIONS, elem, flow_of, free, net, poles

if TYPE_CHECKING:
    from fransys_layout.core.flow_values import FlowGraph


def offsets(flow: FlowGraph, *syms: str) -> list[int]:
    """The offsets of the lanes that hold one of `syms`, in lane order."""
    return [lane.offset for column in flow.columns for lane in column.lanes if any(c.sym in syms for c in lane.cells)]


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


@pytest.mark.rule("KEEP-OUT")
def test_lanes_whose_own_cells_would_overlap_stand_a_footprint_apart() -> None:
    """Two 40 wide bodies under poles 24 apart overlapped; the shared box may, the bodies may not."""
    syms = [poles("a", 2), elem("t0", 40), elem("t1", 40), elem("u0"), elem("u1")]
    nets = [
        net("n0", "u0.s", "a.n0"),
        net("n1", "u1.s", "a.n1"),
        net("m0", "a.s0", "t0.n"),
        net("m1", "a.s1", "t1.n"),
    ]
    o0, o1 = offsets(flow_of(syms, nets), "t0"), offsets(flow_of(syms, nets), "t1")
    assert abs(o1[0] - o0[0]) >= 40


@pytest.mark.rule("KEEP-OUT")
def test_lanes_the_pole_boxes_leave_at_one_offset_stand_a_hub_apart() -> None:
    """R1208: pole box a puts lane 1 where q puts lane 2; every lane head takes a hub, so no two stand under one another."""
    syms = [poles("a", 2), poles("q", 4), elem("t2"), elem("t3"), *(free(f"h{k}") for k in range(4))]
    heads = ("a.n0", "a.n1", "t2.n", "t3.n")
    nets = [
        net("n0", "a.s0", "q.n0"),
        net("n1", "a.s1", "q.n2"),
        net("n2", "t2.s", "q.n1"),
        net("n3", "t3.s", "q.n3"),
        *(net(f"f{k}", f"h{k}.n", head) for k, head in enumerate(heads)),
    ]
    at = sorted(o for k in range(4) for o in offsets(flow_of(syms, nets), f"h{k}"))
    assert min(b - a for a, b in itertools.pairwise(at)) >= 16


@pytest.mark.rule("KEEP-OUT")
def test_no_lanes_wire_stands_on_the_body_of_another_lane() -> None:
    """R1210: a narrow lane beside a wide body, poles 24 apart: the wide body's edge stood on the narrow lane's wire."""
    syms = [poles("a", 2), elem("t0", 0), elem("t1", 48), elem("u0"), elem("u1")]
    nets = [net("n0", "u0.s", "a.n0"), net("n1", "u1.s", "a.n1"), net("m0", "a.s0", "t0.n"), net("m1", "a.s1", "t1.n")]
    flow = flow_of(syms, nets)
    (o0,), (o1,) = offsets(flow, "t0"), offsets(flow, "t1")
    assert abs(o0 - o1) > 24


@pytest.mark.rule("LANE-CLEAR")
def test_two_interleaved_pole_blocks_beside_one_hub_move_as_one_and_stand_a_gap_apart() -> None:
    """R1482: a and b are 3-pole blocks on the even and the odd poles of hub h; each keeps its pole pitch, and b clears a's body."""
    hub = replace(poles("h", 6), nodes=tuple((f"n{k}", f"s{k}") for k in range(6)))  # a pole box: each pole joins its two pins
    syms = [hub, poles("a", 3), poles("b", 3), *(elem(f"{c}{k}") for c in "sl" for k in range(6))]
    nets = [
        *(net(f"h{k}", f"h.s{k}", f"l{k}.n") for k in range(6)),
        *(net(f"a{k}", f"a.s{k}", f"h.n{2 * k}") for k in range(3)),
        *(net(f"b{k}", f"b.s{k}", f"h.n{2 * k + 1}") for k in range(3)),
        *(net(f"sa{k}", f"s{2 * k}.s", f"a.n{k}") for k in range(3)),
        *(net(f"sb{k}", f"s{2 * k + 1}.s", f"b.n{k}") for k in range(3)),
    ]
    flow = flow_of(syms, nets)
    a, b = offsets(flow, "a"), offsets(flow, "b")
    assert [y - x for x, y in itertools.pairwise(a)] == [48, 48]
    assert [y - x for x, y in itertools.pairwise(b)] == [48, 48]
    assert abs(b[0] - a[0]) >= 72 + OPTIONS.column_gap_min
