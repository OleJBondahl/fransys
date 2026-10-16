"""The stage registry: each case is a name, a problem factory and the stage runner."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core import build_flow
from fransys_layout.core.values import Bundle, Options, Rail

from .chain_fixtures import facing_chain
from .flow_builders import elem, net, poles, problem

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.core.values import PlacementProblem, Sym


def _mirrored(sym: Sym) -> Sym:
    """Poles in reverse x order, so the lane order depends on which shared symbol binds."""
    return replace(sym, pins=tuple(replace(p, dx=-p.dx) for p in sym.pins))


def _mixed_flow() -> PlacementProblem:
    """17 symbols and 18 nets: a chain, a seal-in pair, a hub with legs, a bundle and 3-pole chains.

    Ids mix prefixes and widths, so lexical and natural order differ at 10+.
    """
    chain = [elem("K1", stand_s="GROUND"), elem("K2", 24), elem("K9"), elem("K10", 8)]
    chain.append(elem("K11", stand_n="SUPPLY"))
    seal = [elem("A3"), elem("A10", 24)]
    fan = [elem("H2", 8), elem("T1"), elem("T2", 24), elem("T10")]
    bundle = [poles("M3"), poles("M9"), poles("M10")]
    series = [poles("J3"), poles("J9"), _mirrored(poles("J10"))]
    nets = [
        net("w2", "K1.n", "K2.s"),
        net("w9", "K2.n", "K9.s"),
        net("w10", "K9.n", "K10.s"),
        net("w11", "K10.n", "K11.s"),
        net("L+", "K11.n", rail=Rail(0, "SUPPLY")),
        net("L-", "K1.s", rail=Rail(1, "GROUND")),
        net("p2", "A3.n", "A10.n"),
        net("p10", "A3.s", "A10.s"),
        net("bus12", "H2.s", "T1.n", "T2.n", "T10.n"),
    ]
    nets += [
        net(f"bn{9 + k}", f"M3.s{k}", f"M9.n{k}", f"M10.n{k}", bundle=Bundle("bd1", k))
        for k in range(3)
    ]
    for k in range(3):
        nets += [net(f"jn{k}", f"J3.s{k}", f"J9.n{k}"), net(f"jm{k}", f"J9.s{k}", f"J10.n{k}")]
    return problem(chain + seal + fan + bundle + series, nets)


def _run_flow(prob: PlacementProblem) -> object:
    return build_flow(prob, Options())


def _chain_flow() -> PlacementProblem:
    """Twelve boxes: B2 sorts before B10 by natural key and after it by text."""
    return facing_chain(12)


STAGE_CASES: tuple[tuple[str, Callable[[], PlacementProblem], Callable[..., object]], ...] = (
    ("flow", _mixed_flow, _run_flow),
    ("chain", _chain_flow, _run_flow),
)
