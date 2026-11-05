"""The steps `solve` chains that are not one stage call: marks, text and score (layout-0296)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .anchors import anchor_pages
from .outputs import Annotations, CoreLayout, scene
from .score import score
from .score_wiring import bundles

if TYPE_CHECKING:
    from .flow_values import FlowGraph
    from .outputs import Marker, Placement
    from .values import Options, PlacementProblem


def annotate(placement: Placement, markers: tuple[Marker, ...], problem: PlacementProblem, options: Options) -> Annotations:
    """The frames, the markers and the anchors; the annexes are the router's, placed before its A* round (TEXT-CANDIDATES)."""
    anchored, _ = anchor_pages(placement, problem, options, markers)
    return Annotations(markers=markers, anchored=anchored, outlines=placement.outlines)


def scored(layout: CoreLayout, problem: PlacementProblem, flow: FlowGraph) -> CoreLayout:
    """The layout with its score; the flow is the re-cut's, so the fans are the final ones."""
    return replace(layout, score=score(scene(layout, problem, flow), bundles(flow.fans)))
