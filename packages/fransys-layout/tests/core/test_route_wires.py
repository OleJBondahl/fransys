"""Stage 6 column wires: lane wires, box wires, hops, joins and jogs nested by E6."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise

import pytest

from fransys_layout.core import PinRef
from fransys_layout.core.route_counts import collinear, counts
from fransys_layout.core.route_env import Jog, RouteEnv, z_wire
from fransys_layout.core.route_wires import join_wires, lane_wires, nest_jogs
from fransys_layout.core.values import Column, End

from .chain_fixtures import facing_chain
from .place_fixtures import card_with_coils
from .route_fixtures import envs_of, link_across_box, open_end_env, stub_of


def card_env() -> RouteEnv:
    return envs_of(card_with_coils(3))[0]


def stair(shift: int) -> list[Jog]:
    """Three jogs from y 100 to y 200, each shifted by `shift` in x, sources 100 G apart-ish."""
    return [
        Jog(name, (x, 100), (x + shift, 200)) for name, x in (("c", 180), ("a", 100), ("b", 140))
    ]


def turns(env: RouteEnv, jogs: list[Jog]) -> dict[str, int]:
    return {w.net: w.points[1][1] for w in nest_jogs(env, jogs).wires}


def test_a_left_shifting_stair_nests_by_source_x_with_no_crossing() -> None:
    env = card_env()
    drawn = nest_jogs(env, stair(-90))
    turn = turns(env, stair(-90))
    assert turn["a"] < turn["b"] < turn["c"]
    assert counts(drawn.wires).crossings == 0
    assert drawn.findings == ()


def test_a_right_shifting_stair_nests_the_other_way_with_no_crossing() -> None:
    env = card_env()
    drawn = nest_jogs(env, stair(90))
    turn = turns(env, stair(90))
    assert turn["c"] < turn["b"] < turn["a"]
    assert counts(drawn.wires).crossings == 0


def test_the_stair_with_e6_reversed_crosses_six_times() -> None:
    """The same jogs turned in the opposite order cross twice per pair: the counter sees it."""
    env = card_env()
    grid = env.options.wiring_grid
    jogs = sorted(stair(-90), key=lambda j: -j.top[0])
    wires = [z_wire(j.net, 1, (j.top, j.bottom), 100 + grid * (k + 1)) for k, j in enumerate(jogs)]
    assert counts(wires).crossings == 6


def test_jogs_with_disjoint_spans_share_one_level_and_overlapping_spans_take_three() -> None:
    env = card_env()
    disjoint = [Jog(f"j{k}", (100 + 200 * k, 100), (40 + 200 * k, 200)) for k in range(3)]
    assert len(set(turns(env, disjoint).values())) == 1
    overlapping = [Jog(f"j{k}", (100 + 20 * k, 100), (20 + 20 * k, 200)) for k in range(3)]
    assert len(set(turns(env, overlapping).values())) == 3


def test_more_jogs_than_levels_is_a_finding_that_names_the_nets_and_the_fix() -> None:
    env = card_env()
    jogs = [Jog(f"j{k}", (100 + 40 * k, 100), (20 + 40 * k, 116)) for k in range(3)]
    drawn = nest_jogs(env, jogs)
    (finding,) = drawn.findings
    assert finding.code == "ROUTE_FAILED"
    assert all(f"j{k}" in finding.text for k in range(3))
    assert "wire_min" in finding.text
    assert str(env.options.wiring_grid * 4) in finding.text
    assert len(drawn.wires) == 3


def test_a_lane_wire_between_cells_and_a_box_wire_are_drawn() -> None:
    env = card_env()
    drawn = lane_wires(env, env.columns[0])
    (box_wire,) = drawn.wires
    assert box_wire.net == "c1"
    assert box_wire.points == ((58, 144), (58, 152))
    assert drawn.findings == ()


def test_a_lane_with_an_unplaced_cell_is_a_finding_naming_lane_and_column() -> None:
    env = card_env()
    col = env.columns[0]
    cut_down = replace(env, placed={s: p for s, p in env.placed.items() if s != "k1"})
    drawn = lane_wires(cut_down, col)
    (finding,) = drawn.findings
    assert (finding.code, finding.subject) == ("ROUTE_FAILED", col.id)
    assert "lane 0" in finding.text
    assert "k1" in finding.text


def test_a_box_pin_with_no_matching_cell_pin_is_a_finding_naming_box_and_pin() -> None:
    env = card_env()
    col = env.columns[0]
    wrong = replace(col.heads[0], pin=PinRef("A1", "p2"), net="c2")
    drawn = lane_wires(env, replace(col, heads=(wrong,)))
    (finding,) = drawn.findings
    assert (finding.code, finding.subject) == ("ROUTE_FAILED", "A1")
    assert "p2" in finding.text
    assert "wire it" in finding.text


def test_an_end_that_names_a_lane_the_column_lacks_is_a_finding_not_a_wrap() -> None:
    env = card_env()
    col = env.columns[0]
    drawn = lane_wires(env, replace(col, heads=(replace(col.heads[0], lane=5),)))
    assert len(drawn.findings) == 1
    assert drawn.wires == ()


def test_a_chain_draws_every_net_of_a_hop() -> None:
    prob = facing_chain(2, wires=2)
    env = envs_of(prob)[0]
    (col,) = [c for c in env.columns if c.is_chain]
    drawn = lane_wires(env, col)
    assert drawn.findings == ()
    nets = sorted(w.net for w in drawn.wires) + sorted(j.net for j in drawn.jogs)
    assert nets == sorted(n for hop in col.hops for n in hop)


def join_column(env: RouteEnv, home_pin: str, member_pin: str, *, foot: bool):
    """Two single-cell lanes (k1 home, k2 member) where k2's lane joins to k1's pin."""
    c1, c2 = env.columns[0], env.columns[1]
    cell = c2.lanes[0].cells[0]
    cell = (
        replace(cell, top_pin=None, bottom_pin=member_pin)
        if foot
        else replace(cell, top_pin=member_pin)
    )
    join = End("join", "c1", PinRef("k1", home_pin))
    open_ = End("open")
    heads = (open_, open_) if foot else (open_, join)
    feet = (open_, join) if foot else (open_, open_)
    lanes = (c1.lanes[0], replace(c2.lanes[0], cells=(cell,)))
    return replace(c1, lanes=lanes, heads=heads, feet=feet)


@pytest.mark.parametrize(
    ("foot", "home_pin", "member_pin", "source_top"),
    [(False, "s", "n", True), (True, "n", "s", False)],
    ids=["head", "foot"],
)
def test_a_join_is_a_z_wire_nested_with_the_jogs_and_its_source_is_the_joined_lane(
    *, foot: bool, home_pin: str, member_pin: str, source_top: bool
) -> None:
    env = card_env()
    col = join_column(env, home_pin, member_pin, foot=foot)
    drawn = join_wires(env, col)
    (jog,) = drawn.jogs
    assert (drawn.wires, jog.drawn_as, jog.source_top) == ((), "join", source_top)
    assert jog.source_x == 650
    (wire,) = nest_jogs(env, drawn.jogs).wires
    a = (58, 184) if home_pin == "s" else (58, 152)
    m = (650, 152) if member_pin == "n" else (650, 184)
    assert wire.kind == "join"
    assert {wire.points[0], wire.points[-1]} == {a, m}
    assert 152 < wire.points[1][1] < 184


def lanes_joining_lane_zero(order: tuple[int, ...] = (0, 1, 2)) -> list[Jog]:
    """Three member lanes at x 300, 400, 500 join three pins of lane 0 at x 20, 28, 36."""
    return [Jog(f"j{k}", (300 + 100 * k, 100), (20 + 8 * k, 200), "join") for k in order]


def test_three_parallel_lanes_joining_lane_zero_nest_with_no_crossing_and_no_collinear() -> None:
    env = card_env()
    drawn = nest_jogs(env, lanes_joining_lane_zero())
    turn = {w.net: w.points[1][1] for w in drawn.wires}
    assert turn["j0"] < turn["j1"] < turn["j2"]
    assert counts(drawn.wires).crossings == 0
    assert collinear(drawn.wires) == 0
    assert drawn.findings == ()


def test_three_lanes_joining_lane_zero_in_the_reverse_order_cross() -> None:
    """E6 reversed: the same joins turned the other way round cross (the part C probe)."""
    env = card_env()
    grid = env.options.wiring_grid
    jogs = lanes_joining_lane_zero((2, 1, 0))
    wires = [z_wire(j.net, 1, (j.top, j.bottom), 100 + grid * (k + 1)) for k, j in enumerate(jogs)]
    assert counts(wires).crossings > 0


def test_a_tie_in_source_x_is_broken_by_destination_x() -> None:
    env = card_env()
    jogs = [Jog("a", (100, 100), (40, 200)), Jog("b", (100, 100), (20, 200))]
    turn = turns(env, jogs)
    assert turn["b"] < turn["a"]


def test_level_join_pins_are_one_run() -> None:
    env = card_env()
    col = join_column(env, "n", "n", foot=False)
    (wire,) = join_wires(env, col).wires
    assert wire.points == ((58, 152), (650, 152))


def ring_env() -> tuple[RouteEnv, Column]:
    env = envs_of(link_across_box())[0]
    return env, next(c for c in env.columns if len(c.lanes[0].cells) > 1)


def test_two_cells_of_a_lane_on_different_nets_are_a_finding() -> None:
    env, col = ring_env()
    a, b = col.lanes[0].cells[:2]
    bent = {**env.net_of, PinRef(b.sym, b.top_pin or ""): "other"}
    drawn = lane_wires(replace(env, net_of=bent), col)
    (finding,) = drawn.findings
    assert (finding.code, finding.subject) == ("ROUTE_FAILED", col.id)
    assert a.sym in finding.text
    assert b.sym in finding.text
    assert "different nets" in finding.text


def test_a_cell_pin_with_no_net_draws_no_lane_wire_and_is_a_finding() -> None:
    env, col = ring_env()
    b = col.lanes[0].cells[1]
    bare = {k: v for k, v in env.net_of.items() if k != PinRef(b.sym, b.top_pin or "")}
    whole = lane_wires(env, col)
    drawn = lane_wires(replace(env, net_of=bare), col)
    assert [f.code for f in drawn.findings] == ["LANE_WIRE_DROPPED"]
    assert len(drawn.wires) == len(whole.wires) - 1


def stub_points(orient: str = "R0", open_stub: int = 8) -> list[tuple[tuple[int, int], ...]]:
    env, col = open_end_env(orient, open_stub)
    return [w.points for w in stub_of(lane_wires(env, col))]


def test_an_open_end_draws_a_stub_of_open_stub_out_along_its_side() -> None:
    assert stub_points() == [((650, 184), (650, 192))]


def test_a_turned_symbol_draws_its_stub_along_the_turned_side() -> None:
    assert stub_points("R180") == [((650, 184), (650, 176))]


def test_open_stub_zero_draws_no_stub() -> None:
    assert stub_points(open_stub=0) == []


def test_an_open_end_with_no_pin_draws_nothing() -> None:
    env, col = open_end_env(has_pin=False)
    assert stub_of(lane_wires(env, col)) == ()


@pytest.mark.parametrize(("sym", "pin"), [("k2", "nope"), ("ghost", "s")])
def test_an_open_end_naming_a_pin_not_on_the_page_is_a_finding_not_an_empty_stub(
    sym: str, pin: str
) -> None:
    env, col = open_end_env()
    col = replace(col, feet=(End("open", "dangling", PinRef(sym, pin)),))
    drawn = lane_wires(env, col)
    assert stub_of(drawn) == ()
    assert [f for f in drawn.findings if f"{sym}.{pin}" in f.text]


def far_box_env(*, foot: bool = False) -> RouteEnv:
    """The card's box pin moved right of its lane and well above it; `foot`: it ends the lane."""
    env = card_env()
    box = env.placed["A1"]
    pins = tuple(replace(q, x=100, y=40) if q.pin == "p1" else q for q in box.pin_xy)
    env = replace(env, placed={**env.placed, "A1": replace(box, pin_xy=pins)})
    if not foot:
        return env
    col = env.columns[0]
    gone = End("open", None, None, None, None)
    ends = {"heads": (gone,), "feet": col.heads}
    nets = {**env.net_of, PinRef("k1", "s"): "c1"}
    lane = replace(col.lanes[0], cells=(replace(col.lanes[0].cells[0], bottom_pin="s"),))
    col = replace(col, lanes=(lane, *col.lanes[1:]), **ends)
    return replace(env, net_of=nets, columns=(col, *env.columns[1:]))


def box_wire(env: RouteEnv) -> tuple[tuple[int, int], ...]:
    drawn = lane_wires(env, env.columns[0])
    wires = (*drawn.wires, *nest_jogs(env, drawn.jogs).wires)
    (wire,) = (w for w in wires if w.net == "c1" and len(w.points) > 2)
    return wire.points


def test_a_box_wire_to_a_head_pin_runs_long_on_the_box_column_and_turns_above_the_cell() -> None:
    """SHORTS-ROUTE: the long vertical on the lane's pin column ran through the lane's cells."""
    assert box_wire(far_box_env()) == ((100, 40), (100, 144), (58, 144), (58, 152))


def test_a_box_wire_to_a_foot_pin_comes_in_from_below_the_cell() -> None:
    """The foot pin faces south: the wire passes the cell on the box column, never over its body."""
    assert box_wire(far_box_env(foot=True)) == ((100, 40), (100, 192), (58, 192), (58, 184))


def test_a_stair_with_no_turn_row_draws_nothing_and_says_so() -> None:
    """SHORTS-ROUTE: pin levels one grid apart left no row; the clamp bent on a pin row."""
    env = card_env()
    grid = env.options.wiring_grid
    drawn = nest_jogs(env, [Jog("j", (100, 100), (40, 100 + grid))])
    (finding,) = drawn.findings
    assert finding.code == "ROUTE_FAILED"
    assert "j" in finding.text
    assert "wire_min" in finding.text
    assert drawn.wires == ()


def _cells(points: tuple[tuple[int, int], ...]) -> set[tuple[int, int]]:
    """Every 2-unit step along a wire's segments."""
    out = set()
    for (x0, y0), (x1, y1) in pairwise(points):
        n = max(abs(x1 - x0), abs(y1 - y0)) // 2
        out |= {(x0 + (x1 - x0) * k // n, y0 + (y1 - y0) * k // n) for k in range(n + 1)}
    return out


def test_two_box_wires_beside_neighbouring_cells_share_no_point() -> None:
    """Two box wires on one side: the second comes in on the first one's box column."""
    env = card_env()
    box, cell = env.placed["A1"], env.placed["k2"]
    at = {"p1": 100, "p2": 116}
    pins = tuple(replace(q, x=at[q.pin], y=40) if q.pin in at else q for q in box.pin_xy)
    moved = tuple(replace(q, x=100) if q.pin == "n" else q for q in cell.pin_xy)
    placed = {**env.placed, "A1": replace(box, pin_xy=pins), "k2": replace(cell, pin_xy=moved)}
    env = replace(env, placed=placed)
    wires = [w for col in env.columns[:2] for w in lane_wires(env, col).wires]
    first, second = wires
    assert not _cells(first.points) & _cells(second.points)
