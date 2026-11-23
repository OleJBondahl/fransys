"""Stages 6 to 8a as one loop (E11, R1222): route, then stand each loss as a reference the next round routes round.

A round has one plan (R2618): its wires and its markers are laid from the same references. After every round each required
conductor end is drawn or named by a reference end (R2650); the loss set only grows, so the loop ends.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

from .anchors import Stood, anchor_leads, anchor_pages, page_keeps
from .cut_loss import arrowed, restood, whole, withdrawn
from .fallback import fallback
from .outputs import Demand, Placement, Refused, Routes
from .route import route_pages
from .route_env import LostKey, lost_key
from .route_fixed import Laid, fixed_wires
from .text_markers import placed_marks

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .annex_values import AnnexBox
    from .flow_values import CutResult
    from .outputs import Marker
    from .route import RouteMemo
    from .values import Finding, Options, PinRef, PlacementProblem, Ref


class Plan(NamedTuple):
    """One round's plan: the cut with the fallback references added, those references alone, and the conductors withheld."""

    cut: CutResult
    refs: tuple[Ref, ...]
    lost: frozenset[LostKey]
    apart: tuple[Refused, ...] = ()


class Round(NamedTuple):
    """What the loop leaves: the markers with their MARKER_UNPLACED findings and room demands.

    Also the routes, and the references of the lost conductors.
    """

    markers: tuple[Marker, ...]
    missed: tuple[Finding, ...]
    routes: Routes
    refs: tuple[Ref, ...]
    lost: tuple[Refused, ...] = ()
    asks: tuple[Demand, ...] = ()
    memo: RouteMemo | None = None
    apart: tuple[Refused, ...] = ()
    legless: tuple[PinRef, ...] = ()


def plan_of(cut: CutResult, placement: Placement, problem: PlacementProblem, lost: Mapping[LostKey, Refused]) -> Plan:
    """The carriers after `lost`: each loss whole, as a fallback reference beside the cut's joins; each planned end at a withheld pin asked again."""
    gone = withdrawn(lost.values(), problem.facts.far_ends, cut.spec.drawn, cut.flow.fans)
    groups, down = whole(
        lost.values(), problem.facts.far_ends, cut.spec.drawn, (gone, {p.sym for pg in placement.pages for p in pg.placed}), cut.flow.fans
    )
    apart = tuple(Refused(n, pair) for n, pair in cut.spec.unjoined)
    refs = fallback(cut, placement, (*groups, *apart))
    plan = arrowed(cut.spec.reference_plan, cut.flow.fans, cut.spec.pages, down.keys())
    stood = restood(plan, down.keys(), groups, gone, cut.spec.drawn)
    lost_pins = {p for r in lost.values() for p in r.ends or ()}
    withheld = frozenset(lost) | {lost_key(net, (pin,)) for pin, net in down.items() if pin not in lost_pins}
    return Plan(replace(cut, spec=replace(cut.spec, reference_plan=(*stood, *refs))), refs, withheld, apart)


def routed(placement: Placement, cut: CutResult, problem: PlacementProblem, options: Options, laid: Laid) -> Routes:
    """Stage 6 once per page, each with that page's marker and anchor keeps as obstacles."""
    anchored, found = anchor_pages(placement, problem, options)
    leads = anchor_leads(anchored)
    parts = [
        route_pages(
            Placement((page,), outlines=placement.outlines),
            cut,
            problem,
            options,
            laid._replace(keeps=page_keeps(page, Stood(laid.markers, anchored), problem, options), leads=leads),
        )
        for page in placement.pages
    ]
    return Routes(
        tuple(p for r in parts for p in r.pages),
        tuple(n for r in parts for n in r.failed),
        (*found, *(f for r in parts for f in r.findings)),
    )


def _stand(plan: Plan, placement: Placement, problem: PlacementProblem, options: Options, held: tuple[Sequence[AnnexBox], RouteMemo | None]) -> Round:
    """One round from one plan: fixed wires, every reference as a marker, then labels and A* round their boxes (E11).

    `held` is what the rounds before left: the labels, which do not move, and the page routes already made.
    """
    labels, memo = held
    wires = fixed_wires(placement, plan.cut, problem, options, lost=plan.lost)
    fixed = {pg: f._replace(labels=tuple(a for a in labels if a.page == pg)) for pg, f in wires.items()}
    markers, missed, asks, legless = placed_marks(plan.cut, placement, problem, options, fixed)
    routes = routed(placement, plan.cut, problem, options, Laid((), fixed, plan.lost, markers, (), memo))
    return Round(markers, missed, routes, plan.refs, (), asks, memo, plan.apart, legless)


def route_round(cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options, memo: RouteMemo | None = None) -> Round:
    """Round k routes what no earlier round lost; round k's losses stand as references in round k+1.

    It stops after the first round that loses nothing (R1245), or at `route_fallback_rounds`, where the
    last round's losses still become references (R1244).
    """
    # KI-1120: the closing stand at the cap is unread (A6-CAP-STAND, after FALLBACK-PROPERTY)
    lost: dict[LostKey, Refused] = {}
    labels: Sequence[AnnexBox] = ()
    memo = {} if memo is None else memo
    left = options.route_fallback_rounds
    while True:
        rnd = _stand(plan_of(cut, placement, problem, lost), placement, problem, options, (labels, memo))._replace(lost=tuple(lost.values()))
        new = {k: r for r in rnd.routes.failed if r.ends and (k := lost_key(r.net, r.ends)) not in lost}
        lost |= new
        labels = rnd.routes.labels
        if not new or not left:
            return rnd
        left -= 1
