"""The steps `solve` chains that are not one stage call: marks, text and score (layout-0296)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .anchors import anchor_pages
from .annex import place_annexes
from .outputs import Annotations, CoreLayout, scene
from .score import score
from .score_wiring import bundles
from .text_wires import label_nets
from .widen import marks, routed

if TYPE_CHECKING:
    from .outputs import Marker, Placement, Routes
    from .values import CutResult, Finding, FlowGraph, Options, PlacementProblem


def route_round(
    cut: CutResult, placement: Placement, problem: PlacementProblem, options: Options
) -> tuple[tuple[Marker, ...], Routes]:
    """Stage 8a before stage 6: the markers, then the routes round their boxes (E11)."""
    markers = marks(cut, placement, problem, options)[0]
    return markers, routed(placement, cut, problem, options, markers)


def annotate(
    placement: Placement,
    routes: Routes,
    markers: tuple[Marker, ...],
    problem: PlacementProblem,
    options: Options,
) -> tuple[Annotations, tuple[Finding, ...]]:
    """The annexes, then wire labels, each round the markers and the annexes before it."""
    anchored = anchor_pages(placement, problem, options)
    seed = Annotations(markers=markers, anchored=anchored)
    annexes, label_found = place_annexes(placement, routes, seed, problem, options)
    notes = Annotations(annexes=annexes, markers=markers, anchored=anchored)
    wire_labels, wire_found = label_nets(placement, routes, notes, problem, options)
    return replace(notes, wire_labels=wire_labels), (*label_found, *wire_found)


def scored(layout: CoreLayout, problem: PlacementProblem, flow: FlowGraph) -> CoreLayout:
    """The layout with its score; the flow is the re-cut's, so the fans are the final ones."""
    return replace(layout, score=score(scene(layout, problem, flow), bundles(flow.fans)))
