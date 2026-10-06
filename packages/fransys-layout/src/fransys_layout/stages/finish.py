"""The second half of a page, over every page: `finish_page` for each plan, handed its own slices.

`finish_pages` cuts what finishing reads of the run into pages once (D10, `slices`) and runs
`pagerun.finish_page` on each.
"""

from dataclasses import dataclass, replace
from operator import attrgetter
from typing import TYPE_CHECKING

from .pagerun import PageState, finish_page
from .slices import (
    FUNCTION,
    by_ends,
    by_page,
    by_plan,
    connection_ends,
    page_columns,
    page_of,
    pages_of,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Finding

    from .pagerun import PageInputs
    from .types import (
        Column,
        DrawnFunction,
        Handle,
        LabelRequest,
        LinkMarker,
        NetGroup,
        PagePlan,
        PlacedFunction,
        PlacedLabel,
        Route,
    )


_SUBJECT = attrgetter("subject")  # the key of a cross-reference request into `by_page`


@dataclass(frozen=True)
class FinishRun:
    """What finishing every page reads of the run, whole; `routed_on` maps a one-page conductor."""

    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    inputs: PageInputs
    markers: tuple[LinkMarker, ...]
    references: tuple[LabelRequest, ...]
    routed_on: dict[Handle, tuple[int, int]]


def finish_pages(
    plans: tuple[PagePlan, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    run: FinishRun,
) -> tuple[list[Route], list[PlacedLabel], list[Finding]]:
    """`finish_page` over every plan, each handed its own slices of the run (D10, `slices`)."""
    count, inputs = len(plans), run.inputs
    on_page = pages_of(page_columns(plans, run.columns))
    drawn_at = by_page(run.drawn, FUNCTION, on_page, count)
    connections_at = by_ends(inputs.connections, connection_ends, on_page, count=count, every=True)
    groups_at = by_ends(inputs.net_groups, _group_ends, on_page, count=count, every=False)
    markers_at = by_plan(run.markers, page_of, plans)
    references_at = by_page(run.references, _SUBJECT, on_page, count)
    routes: list[Route] = []
    labels: list[PlacedLabel] = []
    findings: list[Finding] = []
    for index, (plan, (placed, first)) in enumerate(zip(plans, pages, strict=True)):
        here = (plan.drawing_set, plan.number)
        page_inputs = replace(
            inputs,
            connections=tuple(
                c for c in connections_at[index] if run.routed_on.get(c.handle, here) == here
            ),
            net_groups=groups_at[index],
        )
        page_routes, page_labels, page_findings = finish_page(
            PageState(placed, first, markers_at[index]),
            drawn_at[index],
            page_inputs,
            references=references_at[index],
        )
        routes.extend(page_routes)
        labels.extend(page_labels)
        findings.extend(page_findings)
    return routes, labels, findings


def _group_ends(group: NetGroup) -> tuple[Handle, ...]:
    """The functions a net group has a port on."""
    return tuple(ref.function for ref in group.ports)
