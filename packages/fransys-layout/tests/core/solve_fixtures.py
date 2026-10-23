"""Planted problems for the `solve` tests: a tag on a link's path, and a pipeline helper."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import Facts, Options, PinRef, PlacementProblem, Unit
from fransys_layout.core.values import PageSpec, Ref, RefEnd, RefKind

from . import pipeline_fixtures
from .conftest import MARKER
from .cut_fixtures import AREA, chain, elem, net, side
from .cycle_fixtures import ring_problem

if TYPE_CHECKING:
    from fransys_layout.core.outputs import Placement
    from fransys_layout.core.values import CutResult


def ring_beside_a_tall_chain() -> PlacementProblem:
    """The t01 ring, whose cross-link n3 runs along the top of the page, beside a 3-cell chain.

    The chain's cells are 620, 300 and 300 G tall, so the page holds them in two columns.
    """
    ids = ["k00", "k01", "k02"]
    syms = tuple(elem(i, 40, h) for i, h in zip(ids, (620, 300, 300), strict=True))
    ring = ring_problem()
    return replace(ring, symbols=ring.symbols + syms, nets=ring.nets + tuple(chain(ids)))


def tag_on_the_wire() -> tuple[PlacementProblem, CutResult, Placement, Options]:
    """The plant above with one more planned tag, standing on the top pin of k00.

    Routed with no obstacle, n3 runs along the top of the page through that tag's box.
    """
    prob = ring_beside_a_tall_chain()
    opts = core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    cut = pipeline_fixtures.cut_of(prob, opts)
    ends = (RefEnd(1, None, PinRef("k00", "n")), RefEnd(1, None, PinRef("k02", "s")))
    plan = (*cut.spec.reference_plan, Ref("x9", RefKind.TAG, ends))
    cut = replace(cut, spec=PageSpec(cut.spec.pages, plan, cut.spec.findings))
    return prob, cut, pipeline_fixtures.placed_from(cut, prob, opts), opts


def two_unit_crossing_nets() -> PlacementProblem:
    """Two nets, each across the units U1 and U2 with a boundary pin at each end: two stub sets.

    The nets stand on separate symbols, so the order of the stubs follows the order of the nets in
    the problem unless the cut sorts them (IS.1 reverses the nets).
    """
    syms = [side(name, 700, 500) for name in "xyzpqr"]
    facts = Facts(
        units=(
            Unit("U1", None, (PinRef("x", "e"), PinRef("p", "e"))),
            Unit("U2", None, (PinRef("z", "e"), PinRef("r", "e"))),
        ),
    )
    nets = (
        net("m", "x.e", "y.e", "z.e", crosses_unit=True),
        net("k", "p.e", "q.e", "r.e", crosses_unit=True),
    )
    return PlacementProblem(AREA, tuple(syms), nets, facts)
