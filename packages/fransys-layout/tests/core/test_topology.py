"""Stage 1: what build_flow makes of tiny hand-built problems."""

from __future__ import annotations

from typing import TYPE_CHECKING

from turn_fixtures import refit

from fransys_layout.core.values import Bundle

from .flow_builders import elem, flow_of, free, net, poles

if TYPE_CHECKING:
    from fransys_layout.core.flow_values import FlowGraph


def test_series_chain_between_stands_is_one_column_of_one_lane() -> None:
    """k1 sits at the GROUND end and sorts first, so the walk starts there and turns head-first."""
    syms = [elem("k1", stand_s="GROUND"), elem("k2"), elem("k3", stand_n="SUPPLY")]
    nets = [
        net("x", "k1.n", "k2.s"),
        net("y", "k2.n", "k3.s"),
    ]
    (column,) = flow_of(syms, nets).columns
    (lane,) = column.lanes
    assert [(c.sym, c.orient) for c in lane.cells] == [("k3", "R0"), ("k2", "R0"), ("k1", "R0")]


def test_seal_in_pair_folds_into_two_lanes_of_one_column() -> None:
    """Two symbols on the same two wiring nets are two lanes of one column, not one chained lane."""
    nets = [net("x", "a.n", "b.n"), net("y", "a.s", "b.s")]
    (column,) = flow_of([elem("a"), elem("b")], nets).columns
    assert len(column.lanes) == 2


def test_free_sided_symbol_is_the_hub_of_a_fan() -> None:
    syms = [free("h"), elem("l1"), elem("l2"), elem("l3")]
    (fan,) = flow_of(syms, [net("bus", "h.s", "l1.n", "l2.n", "l3.n")]).fans
    assert fan.hub == "h"
    assert (len(fan.drivers), len(fan.legs)) == (1, 3)


def test_bundle_nets_make_one_fan_of_three_lanes_named_in_lane_order_not_in_id_order() -> None:
    syms = [poles("src"), poles("ld1"), poles("ld2")]
    for poles_of, names in (((0, 1, 2), ("b0", "b1", "b2")), ((2, 0, 1), ("b1", "b2", "b0"))):
        nets = [net(f"b{k}", f"src.s{p}", f"ld1.n{p}", f"ld2.n{p}", bundle=Bundle("b", p)) for k, p in enumerate(poles_of)]
        (fan,) = flow_of(syms, nets).fans
        assert (fan.lanes, fan.nets) == (3, names)


def test_two_end_net_between_s_pins_stays_a_link_and_flips_one_symbol() -> None:
    flow = flow_of([elem("a"), elem("b")], [net("x", "a.s", "b.s")])
    (column,) = flow.columns
    (lane,) = column.lanes
    assert sorted(c.orient for c in lane.cells) == ["R0", "R180"]
    assert flow.fans == flow.cross_links == ()


def test_a_symbol_with_the_terminal_structure_is_placed_the_same_whatever_it_is() -> None:
    """T4: the core reads pins, nodes, row group and footprint, never what the symbol is."""

    def build(hub_id: str, **kind: object) -> FlowGraph:
        hub = refit(free(hub_id, row_group="r"), pins=free(hub_id).pins[::2], **kind)
        syms = [hub, elem("l1"), elem("l2")]
        return flow_of(syms, [net("bus", f"{hub_id}.s", "l1.n", "l2.n")])

    terminal = build("t", item="terminal", unit="X1", group="terminals", child_of="strip")
    plain = build("p")
    assert terminal.fans
    assert _anon(terminal, "t") == _anon(plain, "p")


def _anon(flow: FlowGraph, hub_id: str) -> str:
    return repr(flow).replace(f"'{hub_id}'", "'H'").replace(f"c:{hub_id}", "c:H")


def test_bundle_poles_that_skip_an_index_make_one_lane_per_pole() -> None:
    syms = [poles("src"), poles("ld1"), poles("ld2")]
    nets = [net(f"b{k}", f"src.s{k}", f"ld1.n{k}", f"ld2.n{k}", bundle=Bundle("b", k)) for k in (1, 2)]
    (fan,) = flow_of(syms, nets).fans
    assert (fan.lanes, fan.nets) == (2, ("b1", "b2"))
    assert sorted({a.pole for a in (*fan.drivers, *fan.legs)}) == [0, 1]
