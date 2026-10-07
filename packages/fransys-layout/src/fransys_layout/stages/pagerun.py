"""Stages 3 to 5 over every page, then the work of one page: place, label, route.

Refs: foundations.md 3, labels.md 6.7, engine.md 7.

`plan_pages` partitions the columns into pages (S10). `place_pages` has `references` decide on
those planned pages as `place` stacks them, then runs `_place_page` over each page and settles
what the placed pages change: the box sides, and the column widths the engine re-plans on.
`finish_page` is the second half of a page, after
the links: reserve the cross-reference labels, route. Each function sees
one page's placed functions, so every box handed to a stage is that page's only (decision
layout-0024).
"""

from dataclasses import dataclass, field, replace
from functools import partial
from typing import TYPE_CHECKING, Any

lazy from fransys_layout.geometry import Box

from ._page_requests import _page_requests
from ._polelinks import pole_links
from .boxes import box_sides
from .content import content_box
from .images import reserved, rooms, unreserve
from .labels import SlotFrame, decided_runs, place_slot_labels
from .middle_fold import fold_page, middle_bands, shape_boxes
from .onepage import page_wiring
from .page_stacking import PageStacking
from .partition import ColumnTables, partition
from .place import page_stack, place
from .references import Wiring, side_reference_rooms
from .references.digits import FLOOR, Digits, set_digits
from .references.types import Seat, Seating
from .replicate import drop_attached_replicas, drop_replicas
from .route import PageRoom, route
from .sizing import label_boxes, placed_widths, with_rooms
from .slices import (
    FUNCTION,
    by_ends,
    by_page,
    connection_ends,
    page_columns,
    pages_of,
    rooms_by_page,
)
from .tags import TagTexts, one_module_tag
from .texts.power import drawn_shapes, with_power_rooms
from .texts.stand import joined_ports, page_texts
from .types import LabelKind

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_model.kernel import AuthoringKey, Finding

    from .middle import MiddleGroup
    from .middle_fold import GroupShape
    from .references.types import LocationPath, References
    from .stacking import JoinedRun, PageStack
    from .texts.stand import PageTexts
    from .types import (
        Column,
        ColumnWidth,
        Connection,
        DrawnFunction,
        FunctionSpec,
        GroupInfo,
        Handle,
        LabelRequest,
        LinkMarker,
        LocationInfo,
        NetGroup,
        PageHints,
        PagePlan,
        PlacedFunction,
        PlacedLabel,
        Profile,
        Route,
        SheetFormat,
        UnitInfo,
    )


@dataclass(frozen=True)
class PageInputs:
    """What the page steps read of the run: the model's records as stage values, and headroom."""

    functions: tuple[FunctionSpec, ...]
    connections: tuple[Connection, ...]
    net_groups: tuple[NetGroup, ...]
    groups: tuple[GroupInfo, ...]
    locations: tuple[LocationInfo, ...]
    units: tuple[UnitInfo, ...]
    hints: PageHints
    profile: Profile
    sheet: SheetFormat
    top_headroom_lanes: int
    bottom_headroom_lanes: int
    # HL12: each band column's middle group, folded on its page
    middle: Mapping[AuthoringKey, tuple[MiddleGroup, ...]] = field(default_factory=dict)
    # HL18 (layout-0158): each (function, port) a line's conductor lands on
    line_ends: frozenset[tuple[Handle, Handle]] = frozenset()


@dataclass(frozen=True)
class PageState:
    """One page as `finish_page` finds it; placed, labels, markers are `occupied` (S18)."""

    placed: tuple[PlacedFunction, ...]
    labels: tuple[PlacedLabel, ...]
    markers: tuple[LinkMarker, ...]


@dataclass(frozen=True)
class PageRun:
    """What placing every page reads besides the drawn functions, columns and widths."""

    texts: TagTexts
    inputs: PageInputs
    rank_of: dict[Handle, int]
    pin_requests: tuple[LabelRequest, ...]
    reserves: dict[tuple[AuthoringKey, Handle], Any]
    # S4: each drawing set's location path, read from the planned pages (known before `place`)
    paths_of: Callable[[tuple[PagePlan, ...]], Mapping[int, LocationPath]]
    # D5, V1: the power kinds and the item-box sides, by port (`boxes.power_maps`)
    power: tuple[dict[Handle, str], dict[Handle, str]] = ({}, {})


@dataclass(frozen=True)
class Planned:
    """The pages planned (S10): `plans`, their `columns` (dropped replicas out), `findings`."""

    plans: tuple[PagePlan, ...]
    columns: tuple[Column, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class Placement:
    """The pages placed: each plan's `(placed, first call)` (S20), reservations taken off."""

    plans: tuple[PagePlan, ...]
    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    pages: list[tuple[tuple[PlacedFunction, ...], FirstCall]]
    placed_all: tuple[PlacedFunction, ...]
    findings: tuple[Finding, ...]


# S10: `references` over one attempt's planned and stacked pages, with its findings
type Decide = Callable[[Seating], tuple[References, tuple[Finding, ...]]]


def plan_pages(
    run: PageRun,
    drawn: tuple[DrawnFunction, ...],
    columns: tuple[Column, ...],
    widths: tuple[ColumnWidth, ...],
) -> Planned:
    """Stage 3 (S10): partition `columns` into pages at `widths`, then drop unneeded replicas."""
    inputs = run.inputs
    plans, findings = partition(
        columns,
        ColumnTables(
            widths=widths,
            groups=inputs.groups,
            locations=inputs.locations,
            units=inputs.units,
            pole_links=pole_links(columns, drawn, inputs.connections, inputs.net_groups),
            bands=middle_bands(inputs.middle, inputs.profile),
        ),
        hints=inputs.hints,
        profile=inputs.profile,
        sheet=inputs.sheet,
    )
    plans = drop_replicas(plans, columns)
    return Planned(plans, drop_attached_replicas(plans, columns), findings)


def _seated(plans: tuple[PagePlan, ...], columns: tuple[Column, ...]) -> tuple[Seat, ...]:
    """S10: every planned column's cells on its page, in plan order then handle, before `place`."""
    by_key = {column.key: column for column in columns}
    found: list[Seat] = []
    for plan in plans:
        found.extend(
            sorted(
                (
                    Seat(cell.function, plan.drawing_set, plan.number, planned.column)
                    for planned in plan.columns
                    for cell in by_key[planned.column].cells
                ),
                key=lambda one: one.function,
            )
        )
    return tuple(found)


def place_pages(
    run: PageRun,
    drawn: tuple[DrawnFunction, ...],
    planned: Planned,
    widths: tuple[ColumnWidth, ...],
    decide: Decide,
) -> tuple[Placement, tuple[ColumnWidth, ...], tuple[References, tuple[Finding, ...]]]:
    """Stages 4, 5: decide references (S10, S12), place, settle box sides (R7 C5), widths (C21)."""
    inputs = run.inputs
    for attempt in range(2):
        pages, page_found, page_rooms, decided = _place_each(
            run, planned.plans, planned.columns, drawn, decide
        )
        placed_all = tuple(one for placed, _ in pages for one in placed)
        turned = (
            box_sides(placed_all, drawn, inputs.connections, (run.rank_of, *run.power))
            if attempt == 0
            else drawn
        )
        if turned == drawn:
            break
        drawn = turned
    grown = placed_widths(widths, placed_all, inputs.profile.column_gap)
    pages = [(unreserve(placed, page_rooms), first) for placed, first in pages]
    placed_all = unreserve(placed_all, page_rooms)
    findings = (*planned.findings, *page_found)
    placement = Placement(planned.plans, planned.columns, drawn, pages, placed_all, findings)
    return placement, grown, decided


def _place_each(
    run: PageRun,
    plans: tuple[PagePlan, ...],
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    decide: Decide,
) -> tuple[list[Any], list[Any], dict[Any, Any], tuple[References, tuple[Finding, ...]]]:
    """Each plan's `_place_page`: placed, findings, rooms (D7), decisions; slices (D10, S12)."""
    pages, found = [], []
    page_rooms = rooms(run.reserves, drawn, plans, run.inputs)
    own = page_columns(plans, columns)
    on_page = pages_of(own)
    drawn_at = by_page(drawn, FUNCTION, on_page, len(plans))
    specs_at = by_page(run.inputs.functions, FUNCTION, on_page, len(plans))
    requests_at = by_page(
        run.pin_requests,
        partial(
            _function_of, owner={port.port: one.function for one in drawn for port in one.ports}
        ),
        on_page,
        len(plans),
    )
    connections_at = by_ends(
        run.inputs.connections, connection_ends, on_page, count=len(plans), every=True
    )
    rooms_at = rooms_by_page(page_rooms, plans)
    # S4, layout-0135: each set's box width, from the digits known before `place` (not `refs`)
    sized = {one.drawing_set: one.digits for one in set_digits((), plans, run.paths_of(plans))}
    work = [
        PageSlices(
            plan,
            cols,
            reserved(page_drawn, page_room),
            _page_requests(run.texts, plan, cols, specs, requests),
            replace(run.inputs, connections=connections),
            sized.get(plan.drawing_set, FLOOR),
        )
        for plan, cols, page_drawn, page_room, specs, requests, connections in zip(
            plans, own, drawn_at, rooms_at, specs_at, requests_at, connections_at, strict=True
        )
    ]
    # S10, S12: `references` decides on each page as `place` stacks it, before any is placed
    stacks = {(one.plan.drawing_set, one.plan.number): _page_stack(one) for one in work}
    seats = _seated(plans, columns)
    decided = decide(Seating(plans, columns, drawn, seats, stacks))
    # S16: Room's N or S call reads each page's texts as decided, and the wiring on the page
    _, _, wired = page_wiring(decided[0].connections, columns, seats, decided[0].net_groups)
    texts = page_texts(
        decided[0].markers,
        wired,
        sheet=run.inputs.sheet,
        profile=run.inputs.profile,
        joined=joined_ports(decided[0].connections, columns),
    )
    for one in work:
        page = (one.plan.drawing_set, one.plan.number)
        runs = tuple(run for run in decided[0].joins if (run.drawing_set, run.page) == page)
        placed, first, page_findings = _place_page(one, joins=runs, texts=texts.get(page))
        pages.append((placed, first))
        found.extend(page_findings)
    return pages, found, page_rooms, decided


@dataclass(frozen=True)
class FirstCall:
    """S20: a page's first slot call (tags, markings), run by `_first_labels` after markers."""

    requests: tuple[LabelRequest, ...]
    placed: tuple[PlacedFunction, ...]
    drawn: tuple[DrawnFunction, ...]
    occupied: tuple[Box, ...]
    profile: Profile
    shapes: tuple[GroupShape, ...] = ()  # HL20: the middle outlines folded on the page


@dataclass(frozen=True)
class PageSlices:
    """What `place` and `page_stack` read of one page (S12): its plan, own slices and inputs."""

    plan: PagePlan
    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    requests: tuple[LabelRequest, ...]
    inputs: PageInputs
    digits: Digits = FLOOR  # S4: its set's digits, `refs` at the floor (known only after `place`)


def _place_page(
    page: PageSlices,
    *,
    joins: tuple[JoinedRun, ...] = (),
    texts: PageTexts | None = None,
) -> tuple[tuple[PlacedFunction, ...], FirstCall, tuple[Finding, ...]]:
    """Place `page.plan`'s columns; S20: the first slot call is returned, run after the markers."""
    inputs, drawn = page.inputs, page.drawn
    placed, place_findings = place(page.plan, page.columns, drawn, _stacking(page, texts), joins)
    placed, shapes = fold_page(placed, page.plan, inputs.middle, inputs.profile)
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
    """S12: the page as `_place_page`'s `place` stacks it, on the very inputs it hands `place`."""
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
    """The boxes `place` grows the page's keep-outs over: the labels', Room's (S11), supplies'."""
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


def finish_page(
    page: PageState,
    drawn: tuple[DrawnFunction, ...],
    inputs: PageInputs,
    *,
    references: tuple[LabelRequest, ...],
) -> tuple[tuple[Route, ...], tuple[PlacedLabel, ...], tuple[Finding, ...]]:
    """Place cross-reference labels, then route the page (S18, layout-0038, D10)."""
    placed, labels, markers = page.placed, page.labels, page.markers
    second, second_findings = place_slot_labels(
        references,
        placed,
        drawn,
        occupied=(
            *(label.box for label in labels),
            *(one.box for one in drawn_shapes(markers)),
        ),
        frame=SlotFrame(content=content_box(inputs.sheet), profile=inputs.profile),
    )
    slot_labels = (*labels, *second)
    held = tuple(label.box for label in slot_labels if not label.unplaced)
    routes, route_findings = route(
        inputs.connections,
        inputs.net_groups,
        placed,
        drawn,
        PageRoom(reserved=held, profile=inputs.profile, sheet=inputs.sheet, markers=markers),
    )
    return routes, slot_labels, (*second_findings, *route_findings)


def _function_of(request: LabelRequest, owner: Mapping[Handle, Handle]) -> Handle:
    """The function a request is drawn on: a `MARKING` subject is a model port."""
    return owner[request.subject] if request.kind is LabelKind.MARKING else request.subject
