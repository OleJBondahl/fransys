"""Stage 1: parallel members are lanes of one column; a bundle's fan lists legs in pole order."""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core.topology import build_flow
from fransys_layout.core.values import (
    Bundle,
    FlowGraph,
    Net,
    Pin,
    PinRef,
    PlacementProblem,
)
lazy from fransys_layout.core.sym_values import Sym

from .flow_builders import elem, free, net, poles, problem


def flow_of(syms: list[Sym], nets: list[Net]) -> FlowGraph:
    return build_flow(
        problem(syms, nets),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def lanes_of(flow: FlowGraph) -> list[list[list[str]]]:
    """Per column, per lane, the symbols from head to foot."""
    return [[[c.sym for c in lane.cells] for lane in column.lanes] for column in flow.columns]


def seal_in() -> PlacementProblem:
    """S1 parallel to K's own contact between the same two nets."""
    return problem(
        [elem("s1"), elem("k1c")], [net("x", "s1.n", "k1c.n"), net("y", "s1.s", "k1c.s")]
    )


def mid_chain() -> PlacementProblem:
    """supply -> a || b -> coil."""
    syms = [elem("src", stand_n="SUPPLY"), elem("a"), elem("b"), elem("coil", stand_s="GROUND")]
    nets = [net("n1", "src.s", "a.n", "b.n"), net("n2", "a.s", "b.s", "coil.n")]
    return problem(syms, nets)


def test_seal_in_is_one_column_of_two_lanes() -> None:
    (column,) = build_flow(
        seal_in(),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    ).columns
    assert len(column.lanes) == 2


def test_three_parallel_members_make_three_lanes() -> None:
    prob = problem(
        [elem("a"), elem("b"), elem("c")],
        [net("x", "a.n", "b.n", "c.n"), net("y", "a.s", "b.s", "c.s")],
    )
    assert lanes_of(
        build_flow(
            prob,
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
    ) == [[["a"], ["b"], ["c"]]]


def test_pair_inside_a_chain_keeps_the_chain_in_lane_zero() -> None:
    assert lanes_of(
        build_flow(
            mid_chain(),
            core_options(
                flip_turn="R180",
                tag_stagger=True,
                label_gap=8,
                parallel_pitch=48,
                driver_first=True,
                arrow_sides=("E", "W"),
            ),
        )
    ) == [[["src", "a", "coil"], ["b"]]]


def test_a_member_with_its_pins_the_other_way_up_is_turned() -> None:
    prob = problem([elem("a"), elem("b")], [net("x", "a.n", "b.s"), net("y", "a.s", "b.n")])
    (column,) = build_flow(
        prob,
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    ).columns
    turned = [
        (lane.cells[0].sym, lane.cells[0].orient, lane.cells[0].top_pin) for lane in column.lanes
    ]
    assert turned == [("a", "R0", "n"), ("b", "R180", "s")]


def test_the_parent_is_no_child_item_then_shares_an_item_with_the_chain_then_sorts_first() -> None:
    nets = [net("x", "a.n", "b.n"), net("y", "a.s", "b.s")]
    assert lanes_of(flow_of([elem("a"), elem("b")], nets)) == [[["a"], ["b"]]]
    child = [replace(elem("a"), child_of="b"), elem("b")]
    assert lanes_of(flow_of(child, nets)) == [[["b"], ["a"]]]
    syms = [
        elem("src", stand_n="SUPPLY"),
        replace(elem("a"), item="S1"),
        replace(elem("k"), item="K1"),
        replace(elem("coil", stand_s="GROUND"), item="K1"),
    ]
    chain = [net("n1", "src.s", "a.n", "k.n"), net("n2", "a.s", "k.s", "coil.n")]
    assert lanes_of(flow_of(syms, chain)) == [[["src", "k", "coil"], ["a"]]]


def test_ids_named_like_a_terminal_or_a_contact_give_the_same_lanes() -> None:
    """Corpus ids put the kind after a dot, such as `X1:1.terminal`; hi sorts first in both sets."""
    plain = {"hi": "a", "lo": "b", "tail": "c"}
    named = {"hi": "-U1-K1.contact", "lo": "X1:1.terminal", "tail": "-U1-Y1.coil"}
    shapes = []
    for ids in (plain, named):
        hi, lo, tail = ids["hi"], ids["lo"], ids["tail"]
        syms = [elem(hi), elem(lo), elem(tail, stand_s="GROUND")]
        nets = [
            Net("x", (PinRef(hi, "n"), PinRef(lo, "n"))),
            Net("y", (PinRef(hi, "s"), PinRef(lo, "s"), PinRef(tail, "n"))),
        ]
        back = {v: k for k, v in ids.items()}
        flow = flow_of(syms, nets)
        shapes.append(
            [
                [(back[c.sym], c.orient, c.top_pin, c.bottom_pin) for c in lane.cells]
                + [lane.offset]
                for column in flow.columns
                for lane in column.lanes
            ]
        )
    assert shapes[0] == shapes[1]
    assert len(shapes[0]) == 2


def test_input_order_does_not_change_the_lanes() -> None:
    syms = [
        elem("src", stand_n="SUPPLY"),
        elem("a"),
        elem("b"),
        elem("c"),
        elem("coil", stand_s="GROUND"),
    ]
    nets = [net("n1", "src.s", "a.n", "b.n", "c.n"), net("n2", "a.s", "b.s", "c.s", "coil.n")]
    expected = [[["src", "a", "coil"], ["b"], ["c"]]]
    assert lanes_of(flow_of(syms, nets)) == lanes_of(flow_of(syms[::-1], nets[::-1])) == expected


def test_a_group_on_a_net_with_a_hub_stays_a_fan() -> None:
    """The fan draws a hub with its legs aligned; folding under the hub was longer (w04)."""
    syms = [free("h"), elem("a"), elem("b"), elem("tail", stand_s="GROUND")]
    flow = flow_of(syms, [net("x", "h.s", "a.n", "b.n"), net("y", "a.s", "b.s", "tail.n")])
    assert all(len(column.lanes) == 1 for column in flow.columns)
    assert flow.fans


@pytest.mark.parametrize(
    ("members", "driver_pins"),
    [
        ([("b0", 2, 2), ("b1", 1, 1), ("b2", 0, 0)], [0, 1, 2]),
        ([("b0", 1, 1), ("b1", 2, 2), ("b2", 0, 0)], [0, 1, 2]),
        ([("b10", 0, 0), ("b9", 0, 1), ("b2", 1, 2)], [1, 0, 2]),
    ],
    ids=["ids-against-poles", "ids-scrambled", "equal-poles-by-natural-id"],
)
def test_a_bundles_fan_lists_drivers_and_legs_in_pole_order(
    members: list[tuple[str, int, int]], driver_pins: list[int]
) -> None:
    """Members are (net id, pole, pin index); net ids against the poles do not set the order."""
    syms = [poles("src"), *(elem(f"{c}{k}") for c in "xy" for k in range(3))]
    nets = [
        net(nid, f"src.s{k}", f"x{k}.n", f"y{k}.n", bundle=Bundle("b", pole))
        for nid, pole, k in members
    ]
    (fan,) = flow_of(syms, nets).fans
    assert [int(a.pin.pin[1:]) for a in fan.drivers] == driver_pins
    assert [a.pin.sym for a in fan.legs] == [f"{c}{k}" for k in driver_pins for c in "xy"]
    assert fan.lanes == max(pole for _, pole, _ in members) + 1


def lamp_beside_coil() -> PlacementProblem:
    """A lamp (both pins on top) beside its coil, returning through the coil's contact."""
    lamp = replace(elem("lamp"), pins=(Pin("a", "N", 0, -16, 0), Pin("b", "N", 16, -16, 1)))
    syms = [
        elem("src", stand_n="SUPPLY"),
        replace(elem("coil", stand_s="GROUND"), item="K1"),
        lamp,
        replace(elem("kc", stand_s="GROUND"), item="K1"),
    ]
    return problem(syms, [net("n1", "src.s", "coil.n", "lamp.a"), net("n2", "lamp.b", "kc.n")])


def test_no_symbol_is_dealt_into_two_lanes_of_one_column() -> None:
    for column in build_flow(
        lamp_beside_coil(),
        core_options(
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    ).columns:
        seen = [c.sym for lane in column.lanes for c in lane.cells]
        assert len(seen) == len(set(seen))
