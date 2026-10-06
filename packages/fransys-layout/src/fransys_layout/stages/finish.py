"""The second half of a page, over every page: `finish_page` for each plan, handed its own slices.

`finish_pages` cuts what finishing reads of the run into pages once (D10, `slices`) and runs
`pagerun.finish_page` on each. `ink_keepouts` cuts each keep-out to the ink (layout-0125).
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from operator import attrgetter
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, hull, translate

from .lookups import owner_of
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
    from collections.abc import Iterable, Sequence

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


def _clip(box: Box, within: Box) -> Box | None:
    """`box` cut to `within`, or None when they share no interior."""
    x0, y0 = max(box.x, within.x), max(box.y, within.y)
    x1 = min(box.x + box.width, within.x + within.width)
    y1 = min(box.y + box.height, within.y + within.height)
    return Box(x=x0, y=y0, width=x1 - x0, height=y1 - y0) if x0 < x1 and y0 < y1 else None


def ink_keepouts(
    placed: Iterable[PlacedFunction],
    labels: Iterable[PlacedLabel],
    drawn: Iterable[DrawnFunction],
) -> tuple[PlacedFunction, ...]:
    """The symbol and the labels it took, in place of the room of every slot (layout-0125).

    A keep-out grown beyond its symbol's body and slots stays as it is; a trimmed one never
    exceeds the old, so no overlap appears.
    """
    owner = owner_of(drawn)
    taken: dict[tuple[object, int, int], list[Box]] = defaultdict(list)
    for label in labels:
        if not label.unplaced:
            key = (owner.get(label.subject, label.subject), label.drawing_set, label.page)
            taken[key].append(label.box)
    found = []
    for one in placed:
        geometry = one.geometry
        if geometry.keepout != hull([geometry.body, *(s.box for s in geometry.slots)]):
            found.append(one)
            continue
        near = [
            translate(b, dx=-one.at.x, dy=-one.at.y)
            for b in taken[one.function, one.drawing_set, one.page]
        ]
        inside = [c for b in near if (c := _clip(b, geometry.keepout)) is not None]
        keepout = hull([geometry.body, *inside])
        found.append(replace(one, geometry=replace(geometry, keepout=keepout)))
    return tuple(found)
