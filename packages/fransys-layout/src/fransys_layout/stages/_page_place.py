"""Stages 3 to 5, one page: place, label, route (pagerun.py)."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

lazy from fransys_layout.geometry import Box

from .labels import decided_runs
from .middle_fold import folded_page, shape_boxes
from .page_stacking import PageStacking
from .place import page_stack, place
from .references import Wiring, side_reference_rooms
from .references.digits import FLOOR, Digits
from .sizing import label_boxes, with_rooms
from .tags import one_module_tag
from .texts.power import with_power_rooms

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

    from .middle_fold import GroupShape
    from .pagerun import PageInputs
    from .stacking import JoinedRun, PageStack
    from .texts.stand import PageTexts
    from .types import (
        Column,
        DrawnFunction,
        Handle,
        LabelRequest,
        PagePlan,
        PlacedFunction,
        Profile,
    )


@dataclass(frozen=True)
class FirstCall:
    """A page's first slot call (tags, markings), run by `_first_labels` after markers."""

    requests: tuple[LabelRequest, ...]
    placed: tuple[PlacedFunction, ...]
    drawn: tuple[DrawnFunction, ...]
    occupied: tuple[Box, ...]
    profile: Profile
    shapes: tuple[GroupShape, ...] = ()  # layout-0153: the middle outlines folded on the page


@dataclass(frozen=True)
class PageSlices:
    """What `place` and `page_stack` read of one page: its plan, own slices and inputs."""

    plan: PagePlan
    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    requests: tuple[LabelRequest, ...]
    inputs: PageInputs
    digits: Digits = FLOOR  # Its set's digits, `refs` at the floor (known only after `place`)


def _place_page(
    page: PageSlices,
    *,
    joins: tuple[JoinedRun, ...] = (),
    texts: PageTexts | None = None,
) -> tuple[tuple[PlacedFunction, ...], FirstCall, tuple[Finding, ...]]:
    """Place `page.plan`'s columns; the first slot call is returned, run after the markers."""
    inputs, drawn = page.inputs, page.drawn
    placed, place_findings = place(page.plan, page.columns, drawn, _stacking(page, texts), joins)
    placed, shapes, place_findings = folded_page(placed, page.plan, inputs, place_findings)
    call = FirstCall(
        requests=one_module_tag(page.requests, placed, drawn),
        placed=placed,
        drawn=drawn,
        occupied=(*decided_runs(placed, drawn, inputs.connections, joins), *shape_boxes(shapes)),
        profile=inputs.profile,
        shapes=shapes,
    )
    return placed, call, place_findings


def _page_stack(page: PageSlices) -> PageStack:
    """The page as `_place_page`'s `place` stacks it, on the very inputs it hands `place`."""
    return page_stack(page.plan, page.columns, page.drawn, _stacking(page))


def _stacking(page: PageSlices, texts: PageTexts | None = None) -> PageStacking:
    """What `place` and `page_stack` stack `page` by: one value, so both read the same."""
    inputs = page.inputs
    return PageStacking(
        profile=inputs.profile,
        sheet=inputs.sheet,
        headroom_lanes=inputs.top_headroom_lanes,
        bottom_headroom_lanes=inputs.bottom_headroom_lanes,
        label_boxes=_page_boxes(page, texts),
        texts=texts,
        digits=page.digits,
        line_ends=inputs.line_ends,
    )


def _page_boxes(page: PageSlices, texts: PageTexts | None) -> dict[Handle, list[tuple[str, Box]]]:
    """The boxes `place` grows the page's keep-outs over: the labels', Room's, supplies'."""
    inputs, drawn = page.inputs, page.drawn
    sides = side_reference_rooms(
        page.columns,
        drawn,
        Wiring(inputs.connections, inputs.net_groups, page.digits),
        sheet=inputs.sheet,
        profile=inputs.profile,
    )
    labelled = with_rooms(label_boxes(drawn, page.requests, inputs.profile), sides)
    return with_power_rooms(labelled, texts, drawn, inputs.profile)
