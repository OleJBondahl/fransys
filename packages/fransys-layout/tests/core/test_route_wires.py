"""Stage 6 column wires: lane wires, box wires, hops, joins and jogs nested by E6."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Column, End, PinRef
from fransys_layout.core.route_counts import counts
from fransys_layout.core.route_env import Jog, RouteEnv, z_wire
from fransys_layout.core.route_wires import join_wires, lane_wires, nest_jogs

from .chain_fixtures import facing_chain
from .place_fixtures import card_with_coils
from .route_fixtures import envs_of, link_across_box


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
    assert box_wire.points == ((58, 136), (58, 144))
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
    ("foot", "home_pin", "member_pin", "x"),
    [(False, "s", "n", 269), (True, "n", "s", 438)],
    ids=["head-one-third", "foot-two-thirds"],
)
def test_a_join_z_steps_a_third_and_two_thirds_across_the_gap(
    *, foot: bool, home_pin: str, member_pin: str, x: int
) -> None:
    env = card_env()
    col = join_column(env, home_pin, member_pin, foot=foot)
    (wire,) = join_wires(env, col).wires
    a = (58, 176) if home_pin == "s" else (58, 144)
    m = (650, 144) if member_pin == "n" else (650, 176)
    assert wire.kind == "join"
    assert wire.points == (a, (x, a[1]), (x, m[1]), m)


def test_level_join_pins_are_one_run() -> None:
    env = card_env()
    col = join_column(env, "n", "n", foot=False)
    (wire,) = join_wires(env, col).wires
    assert wire.points == ((58, 144), (650, 144))


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


def test_a_cell_pin_with_no_net_is_reached_by_a_trunk_and_draws_no_lane_wire() -> None:
    env, col = ring_env()
    b = col.lanes[0].cells[1]
    bare = {k: v for k, v in env.net_of.items() if k != PinRef(b.sym, b.top_pin or "")}
    whole = lane_wires(env, col)
    drawn = lane_wires(replace(env, net_of=bare), col)
    assert drawn.findings == ()
    assert len(drawn.wires) == len(whole.wires) - 1
