"""Schematic engine: what the stage steps read from the inputs (engine.py)."""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages import LabelKind
from fransys_layout.stages.box_views import hidden_views
from fransys_layout.stages.pagerun import PageInputs

from ._arrange_columns import kept_terminals
from .defaults import BOTTOM_HEADROOM_LANES, TOP_HEADROOM_LANES
from .read.harness_lines import box_specs
from .read.labels import label_requests

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages import DrawnFunction, LabelRequest
    from fransys_layout.stages.box_views import BoxSpec
    from fransys_layout.stages.stacking import JoinedRun
    from fransys_model.kernel import Id, Model

    from .read import StageInputs


def _boxed_views(
    model: Model, inputs: StageInputs, drawn: tuple[DrawnFunction, ...]
) -> tuple[tuple[BoxSpec, ...], frozenset[Id[Any]], tuple[LabelRequest, ...]]:
    """The boxes, the pin views they hide, and the tag and marking requests of the rest.

    A boxed connector's pin views draw no symbol and no label; its box stands over them.
    """
    boxes = box_specs(model, inputs.functions)
    hidden = hidden_views(boxes)
    requests = tuple(
        request
        for request in label_requests(inputs.label_texts, drawn)
        if request.kind in (LabelKind.TAG, LabelKind.MARKING) and request.subject not in hidden
    )
    return boxes, hidden, requests


def _pair(run: JoinedRun) -> tuple[Id[Any], Id[Any]]:
    """The two ports of a beside run, in port order as a `Connection` keeps them."""
    first, second = sorted(end.port for end in run.ends)
    return first, second


def _page_inputs(
    inputs: StageInputs,
    heads: Mapping[tuple[Id[Any], Id[Any] | None], str],
    joins: tuple[JoinedRun, ...] = (),
) -> PageInputs:
    """The fields of `inputs` the page steps read, with the house headroom (`defaults`)."""
    return PageInputs(
        functions=inputs.functions,
        connections=inputs.connections,
        net_groups=inputs.net_groups,
        groups=inputs.groups,
        locations=inputs.locations,
        units=inputs.units,
        hints=inputs.hints,
        profile=inputs.profile,
        sheet=inputs.sheet,
        top_headroom_lanes=TOP_HEADROOM_LANES,
        bottom_headroom_lanes=BOTTOM_HEADROOM_LANES,
        line_ends=frozenset((end.function, end.port) for c in inputs.carried for end in (c.a, c.b)),
        heads=heads,
        aside=frozenset(_pair(run) for run in joins if run.aside),
        whole=kept_terminals(inputs),
    )
