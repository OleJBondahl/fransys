"""A refused link keeps its ROUTE_FAILED finding and gets no tag pair in its place (R424).

layout-0314 drew a fallback tag pair for a refused link; R421 kept it for a net with no other
join; R424 removes it: the ERROR is seen, and nothing hides it.
"""

from __future__ import annotations

import importlib
from dataclasses import replace

from options_fixtures import core_options

from fransys_layout.core import PinRef
from fransys_layout.core.outputs import Refused
from fransys_layout.core.solve import solve
from fransys_layout.core.values import Finding, RefKind

from .conftest import MARKER
from .solve_fixtures import ring_beside_a_tall_chain

ENDS = (PinRef("k00", "n"), PinRef("k02", "s"))
solve_stage = importlib.import_module("fransys_layout.core.solve")  # `solve` is also the function
FOUND = Finding("ROUTE_FAILED", "n3 has no free path: move a cell", 1, "n3")


def _refusing(monkeypatch, ends):
    real = solve_stage.widen

    def refuse(*args):
        cut, placement, routes, over = real(*args)
        routes = replace(routes, failed=(Refused("n3", ends),), findings=(FOUND,))
        return cut, placement, routes, over

    monkeypatch.setattr(solve_stage, "widen", refuse)


def _solved():
    return solve(
        ring_beside_a_tall_chain(),
        core_options(
            marker=MARKER,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            driver_first=True,
            arrow_sides=("E", "W"),
        ),
    )


def test_a_refused_link_keeps_its_finding_and_gets_no_tag_pair(monkeypatch) -> None:
    _refusing(monkeypatch, ENDS)
    layout = _solved()
    assert not [r for r in layout.references if r.net == "n3" and r.kind is RefKind.TAG]
    assert "n3" not in [m.net for m in layout.annotations.markers]
    assert [f for f in layout.findings if f.code == "ROUTE_FAILED"] == [FOUND]


def test_a_refusal_without_ends_draws_no_tag_and_keeps_its_finding(monkeypatch) -> None:
    _refusing(monkeypatch, None)
    layout = _solved()
    assert not [r for r in layout.references if r.net == "n3" and r.kind is RefKind.TAG]
    assert [f.code for f in layout.findings].count("ROUTE_FAILED") == 1
