"""BUNDLE (layout-0363): a through element is a chain member, and a bundle's poles turn together."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core import build_flow
from fransys_layout.core.topology_split import BundleError
from fransys_layout.core.values import BoxSpec, Bundle

from .flow_builders import OPTIONS, elem, free, net, poles, problem

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core.sym_values import Sym
    from fransys_layout.core.values import FlowGraph, Net

POLES = 3
ON = replace(OPTIONS, bundle_direction=True)
Shape = "tuple[list[Sym], list[Net], str]"


def _box(sym: Sym, order: tuple[str, ...]) -> Sym:
    return replace(sym, box=BoxSpec(order, "S", 16, 16))


def _mounted_overload() -> tuple[list[Sym], list[Net], str]:
    """Pump Q21: a contactor, an overload mounted on it, a terminal per pole, a PSU on pole 1."""
    syms = [poles("F"), poles("Q"), poles("B"), _box(poles("P"), ("n0",))]
    syms += [free(f"T{k}") for k in range(POLES)]
    nets: list[Net] = []
    for k in range(POLES):
        feed = [f"F.s{k}", f"Q.n{k}", *(["P.n0"] if k == 0 else [])]
        nets.append(net(f"a{k}", *feed, bundle=Bundle("a", k)))
        out = [f"Q.s{k}", f"B.n{k}", f"B.s{k}", f"T{k}.n", f"T{k}.s"]
        nets.append(net(f"b{k}", *out, bundle=Bundle("b", k)))
    return syms, nets, "Q"


def _contactor() -> tuple[list[Sym], list[Net], str]:
    """A 3-pole contactor between a breaker and two loads, a PSU box on its first pole only."""
    syms = [poles("F"), poles("Q"), poles("L"), poles("M"), _box(poles("P"), ("n0",))]
    nets: list[Net] = []
    for k in range(POLES):
        feed = [f"F.s{k}", f"Q.n{k}", *(["P.n0"] if k == 0 else [])]
        nets.append(net(f"a{k}", *feed, bundle=Bundle("a", k)))
        nets.append(net(f"b{k}", f"Q.s{k}", f"L.n{k}", f"M.n{k}", bundle=Bundle("b", k)))
    return syms, nets, "Q"


def _two_pin_box() -> tuple[list[Sym], list[Net], str]:
    """Two lanes to a 2-pin box: pin 1 on its N side, pin 2 on its S side (a loom end)."""
    pins = tuple(
        replace(p, id=i, side=s)
        for p, i, s in zip(elem("X").pins, ("1", "2"), ("N", "S"), strict=True)
    )
    x = replace(_box(elem("X"), ("1", "2")), pins=pins, nodes=(("1",), ("2",)))
    syms = [poles("J", 2), poles("K", 2), x]
    nets = [
        net(f"w{k}", f"J.s{k}", f"K.n{k}", f"X.{k + 1}", bundle=Bundle("w", k)) for k in range(2)
    ]
    return syms, nets, "J"


def _orients(flow: FlowGraph, sym: str) -> set[str]:
    return {
        c.orient for col in flow.columns for lane in col.lanes for c in lane.cells if c.sym == sym
    }


@pytest.mark.rule("BUNDLE")
@pytest.mark.parametrize("shape", [_mounted_overload, _contactor, _two_pin_box])
def test_every_pole_of_a_device_takes_the_bundles_direction(
    shape: Callable[[], tuple[list[Sym], list[Net], str]],
) -> None:
    syms, nets, device = shape()
    flow = build_flow(problem(syms, nets), ON)
    assert flow.fans
    assert len(_orients(flow, device)) == 1
    for fan in flow.fans:
        boxes = {a.pin.sym for a in (*fan.drivers, *fan.legs) if a.column is None}
        legs = {a.pin.sym for a in fan.legs if a.column is None}
        drivers = {a.pin.sym for a in fan.drivers if a.column is None}
        assert not legs & drivers, boxes


@pytest.mark.rule("BUNDLE")
def test_bundle_direction_off_turns_each_chain_alone() -> None:
    """Per-chain turns split the contactor's poles, so a driver and a leg meet on one node."""
    syms, nets, _ = _contactor()
    with pytest.raises(BundleError):
        build_flow(problem(syms, nets), replace(OPTIONS, bundle_direction=False))
