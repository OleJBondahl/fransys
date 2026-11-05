"""A refused link is drawn as a tag pair through the loop, and the ERROR gives way to an INFO (ROUTE-FALLBACK-REFERENCE).

layout-0314 drew a fallback tag pair for a refused link; R424 removed it; the loss-as-value loop
puts it back: the router's loss becomes a reference and WIRE_AS_REFERENCE names it.
"""

from __future__ import annotations

import importlib
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

from options_fixtures import core_options

from fransys_layout.core import PinRef
from fransys_layout.core.flow_values import Attach, CrossLink
from fransys_layout.core.outputs import Refused
from fransys_layout.core.solve import solve
from fransys_layout.core.topology import _tagged
from fransys_layout.core.values import RefKind

from .conftest import MARKER
from .pipeline_fixtures import cut_of, placed_from
from .solve_fixtures import ring_beside_a_tall_chain

ENDS = (PinRef("b", "s"), PinRef("c", "n"))
widen_stage = importlib.import_module("fransys_layout.core.widen")


def _refusing(monkeypatch, ends):
    """The router loses n3 in the first round, while no conductor is yet lost; later rounds route as they do."""
    real = widen_stage.route_pages

    def refuse(placement, cut, problem, options, laid):
        routes = real(placement, cut, problem, options, laid)
        handed = any(n.id == "n3" and ends in n.tagged for n in problem.nets)  # the router loses n3 once; round 2 routes what the cut leaves in page
        return routes if laid.lost or handed else replace(routes, failed=(*routes.failed, Refused("n3", ends)))

    monkeypatch.setattr(widen_stage, "route_pages", refuse)


OPTIONS = core_options(marker=MARKER, flip_turn="R180", tag_stagger=True, label_gap=8, parallel_pitch=48, driver_first=True, arrow_sides=("E", "W"))


def _solved():
    return solve(ring_beside_a_tall_chain(), OPTIONS)


def test_a_refused_link_gets_a_tag_pair_and_a_wire_as_reference_info(monkeypatch) -> None:
    _refusing(monkeypatch, ENDS)
    layout = _solved()
    (tag,) = [r for r in layout.references if r.net == "n3" and r.kind is RefKind.TAG]
    assert [e.pin for e in tag.ends] == [*ENDS]
    assert not [f for f in layout.findings if f.code == "MARKER_UNPLACED"]  # the cut planned the pair, so placement reserved its room
    assert [f.code for f in layout.findings if f.subject == "n3"].count("WIRE_AS_REFERENCE") == 1


def test_a_refusal_without_ends_draws_no_tag_and_no_info(monkeypatch) -> None:
    _refusing(monkeypatch, None)
    layout = _solved()
    assert not [r for r in layout.references if r.net == "n3" and r.kind is RefKind.TAG]
    assert "WIRE_AS_REFERENCE" not in [f.code for f in layout.findings]


def _rounds(monkeypatch, *, lose_first: bool) -> int:
    """How many rounds the loop runs when the router loses n3 in round 1 only, or loses nothing."""
    if lose_first:
        _refusing(monkeypatch, ENDS)
    rounds: list[int] = []
    stand = widen_stage._stand

    def counting(*args):
        rounds.append(len(args[-1]))
        return stand(*args)

    monkeypatch.setattr(widen_stage, "_stand", counting)
    prob = ring_beside_a_tall_chain()
    cut = cut_of(prob, OPTIONS)
    widen_stage.route_round(cut, placed_from(cut, prob, OPTIONS), prob, OPTIONS)
    return len(rounds)


def test_the_loop_stops_after_the_first_round_that_loses_nothing(monkeypatch) -> None:
    """R1245: one round when nothing is lost, two when only round 1 loses; the bound is route_fallback_rounds, never reached."""
    assert _rounds(monkeypatch, lose_first=False) == 1
    assert _rounds(monkeypatch, lose_first=True) == 2


def test_a_lost_link_of_three_ends_gets_a_reference_at_each_end(monkeypatch) -> None:
    ends = (ENDS[0], PinRef("s", "s"), ENDS[1])
    _refusing(monkeypatch, ends)
    (tag,) = [r for r in _solved().references if r.net == "n3" and r.kind is RefKind.TAG]
    assert [e.pin for e in tag.ends] == list(ends)


def test_a_reference_made_for_a_wire_lost_in_round_one_is_placed_before_round_two(monkeypatch) -> None:
    """A21: round 2's markers are placed from a plan that holds round 1's loss; round 1's plan does not."""
    _refusing(monkeypatch, (PinRef("b", "s"), PinRef("c", "n")))
    plans: list[set[str]] = []
    real = widen_stage.placed_marks

    def spy(cut, *args):
        plans.append({r.net for r in cut.spec.reference_plan if r.kind is RefKind.TAG})
        return real(cut, *args)

    monkeypatch.setattr(widen_stage, "placed_marks", spy)
    prob = ring_beside_a_tall_chain()
    cut = cut_of(prob, OPTIONS)
    widen_stage.route_round(cut, placed_from(cut, prob, OPTIONS), prob, OPTIONS)
    assert "n3" not in plans[0]
    assert "n3" in plans[1]


def test_widen_hands_a_lost_link_to_the_cut_as_tagged_and_the_next_round_loses_nothing(monkeypatch) -> None:
    """layout-0508: Net.tagged holds the lost pins, the re-cut flags the link as a tag pair (R1727), the next loop's lost map is empty."""
    ends = (PinRef("b", "s"), PinRef("c", "n"))
    _refusing(monkeypatch, ends)
    prob = ring_beside_a_tall_chain()
    cut = cut_of(prob, OPTIONS)
    placement = placed_from(cut, prob, OPTIONS)
    first = widen_stage.route_round(cut, placement, prob, OPTIONS)
    assert [r.net for r in first.lost] == ["n3"]
    cut2, _, rnd2, prob2, _ = widen_stage.widen(cut, placement, first, prob, OPTIONS)
    assert [n.tagged for n in prob2.nets if n.id == "n3"] == [(ends,)]
    assert [ln.tagged for ln in cut2.flow.cross_links if ln.net == "n3" and {a.pin for a in ln.ends} >= set(ends)] == [True]
    assert rnd2.lost == ()


def test_a_lone_rest_end_of_a_split_net_keeps_its_wire_to_one_lost_end() -> None:
    """layout-0508 (R1506): the net a, b, c with (b, c) lost splits into the link b-c and the wire a-b, neither tagged (R1722); a is never dropped."""
    a, b, c = (PinRef(s, "p") for s in "abc")
    link = CrossLink("n", tuple(Attach(None, 0, 0, p, net="n") for p in (a, b, c)))
    problem: Any = SimpleNamespace(nets=(SimpleNamespace(id="n", tagged=((b, c),)),))
    out = _tagged((link,), problem)
    assert [(ln.tagged, [x.pin for x in ln.ends]) for ln in out] == [(False, [b, c]), (False, [a, b])]
