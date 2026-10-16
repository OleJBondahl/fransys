"""Stage 5 plants: the dealt-lamp ring now places (layout-0285); the cut's row-group gap is xfail.

The ring raise stays as stage 5's guard, tested on a hand-built cyclic flow.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import (
    Fan,
    FlowGraph,
    Hints,
    Options,
    PlacementProblem,
    YCycleError,
    place_pages,
)

from .cut_fixtures import AREA, elem, net
from .pipeline_fixtures import cut_of


def lamp_ring() -> PlacementProblem:
    """The t01 ring: lamp, a, b, c and d in a loop, and a source s joining b and c in a fan."""
    syms = tuple(elem(i, 60) for i in ("lamp", "a", "b", "c", "d", "s"))
    nets = (
        net("n1", "lamp.s", "a.n"),
        net("n2", "a.s", "b.n"),
        net("n3", "b.s", "s.s", "c.n"),
        net("n4", "c.s", "d.n"),
        net("n5", "d.s", "lamp.n"),
    )
    return PlacementProblem(AREA, syms, nets)


def test_a_symbol_dealt_into_two_lanes_of_one_column_is_placed() -> None:
    """The lamp heads one lane and foots the other: stage 1 takes the ring's fan net out (0285)."""
    prob = lamp_ring()
    assert place_pages(cut_of(prob), prob, Options()).pages


def ring_fan(flow: FlowGraph) -> Fan:
    """The fan stage 1 took out of the ring, put back: its two drivers above its one leg."""
    (link,) = flow.cross_links
    *drivers, leg = link.ends
    return Fan("f:n3", (link.net,), tuple(drivers), (leg,), None, 1, "above")


def test_the_ring_raises_the_named_error_with_the_column_and_the_fix() -> None:
    """Stage 5 keeps the raise (designer 2026-10-16): a hand-built cyclic flow still names it."""
    prob = lamp_ring()
    cut = cut_of(prob)
    ring = replace(cut.flow, fans=(ring_fan(cut.flow),), cross_links=())
    with pytest.raises(
        YCycleError, match=r"page 1: cyclic y constraints \(columns .*split the ring"
    ):
        place_pages(replace(cut, flow=ring), prob, Options())


@pytest.mark.xfail(
    strict=True, reason="P6 is strict: the cut spreads a row group over two rows, then y drops it"
)
def test_a_row_group_the_cut_spread_over_two_rows_is_not_dropped() -> None:
    """The cut plant's circuit (a row group of three beside a wide column): R1 is ALIGN_DROPPED.

    Corpus w02 and w06 each drop a row group the same way (the findings name X1 and X6).
    """
    members = [replace(elem(f"r{i}", 300), row_group="R1") for i in (1, 2, 3)]
    syms = [elem("x0", 500, 32, "G0"), elem("x1", 500, 32, "G0"), *members]
    syms += [elem(f"s{i}", 300, 32, "G1") for i in (1, 2, 3)]
    nets = [net("x", "x0.s", "x1.n")]
    nets += [net(f"m{i}", f"r{i}.s", f"s{i}.n") for i in (1, 2, 3)]
    prob = PlacementProblem(AREA, tuple(syms), tuple(nets), hints=Hints(group_order=("G0", "G1")))
    found = place_pages(cut_of(prob), prob, Options()).findings
    assert [f for f in found if f.code == "ALIGN_DROPPED"] == []
