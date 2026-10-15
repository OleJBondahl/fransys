"""Stages 3 to 5 over every page, then the work of one page: place, label, route.

`plan_pages` partitions the columns into pages. `place_pages` has `references` decide on
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

from ._chain_beside import beside_cells, beside_links
from ._page_place import FirstCall, PageSlices, _page_stack, _place_page
from ._page_requests import _page_requests
from ._polelinks import pole_links
from .boxes import box_sides
from .content import content_box
from .extent import page_extras
from .images import reserved, rooms, unreserve
from .labels import SlotFrame, place_slot_labels
from .lookups import owner_of
from .middle_fold import middle_bands
from .onepage import page_wiring
from .partition import ColumnTables, partition
from .pin_landing import Power, column_landing, function_landing
from .references.digits import FLOOR, digits_by_set
from .references.types import Seat, Seating
from .replicate import planned_columns
from .route import PageRoom, route
from .sizing import placed_widths
from .slices import (
    FUNCTION,
    by_ends,
    by_page,
    connection_ends,
    page_columns,
    pages_of,
    rooms_by_page,
)
from .space import Blocks
from .texts.power import drawn_shapes
from .texts.stand import joined_ports, page_texts
from .types import LabelKind
from .wrap import WRAP_GAP
lazy from .tags import TagTexts

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from fransys_model.kernel import AuthoringKey, Finding

    from .middle import MiddleGroup
    from .references.types import LocationPath, References, UnitPath
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
    # layout-0153: each band column's middle group, folded on its page
    middle: Mapping[AuthoringKey, tuple[MiddleGroup, ...]] = field(default_factory=dict)
    # layout-0154 (layout-0158): each (function, port) a line's conductor lands on
    line_ends: frozenset[tuple[Handle, Handle]] = frozenset()
    heads: Mapping[tuple[Handle, Handle | None], str] = field(default_factory=dict)  # 0170, 0238
    aside: frozenset[tuple[Handle, Handle]] = frozenset()  # layout-0174: a beside wire's ports
    whole: frozenset[Handle] = frozenset()  # layout-0214: terminals that keep every copy


@dataclass(frozen=True)
class PageState:
    """One page as `finish_page` finds it; placed, labels, markers are `occupied`."""

    placed: tuple[PlacedFunction, ...]
    labels: tuple[PlacedLabel, ...]
    markers: tuple[LinkMarker, ...]
    blocks: Blocks = field(default_factory=Blocks)


@dataclass(frozen=True)
class PageRun:
    """What placing every page reads besides the drawn functions, columns and widths."""

    texts: TagTexts
    inputs: PageInputs
    # layout-0264: the port ranks and the power maps (`boxes.power_maps`), built once by the arrange
    landing: Power
    pin_requests: tuple[LabelRequest, ...]
    reserves: dict[tuple[AuthoringKey, Handle], Any]
    # Each drawing set's location path, read from the planned pages (known before `place`)
    paths_of: Callable[[tuple[PagePlan, ...]], Mapping[int, LocationPath]]
    unit_paths_of: Callable[[tuple[PagePlan, ...]], Mapping[int, UnitPath]]
    # layout-0182: the reserves and the row labels again, for the parts of a cut column
    recut_of: Callable[[tuple[Column, ...]], tuple[dict[Any, Any], tuple[LabelRequest, ...]]]


@dataclass(frozen=True)
class Planned:
    """The pages planned: `plans`, their `columns` (dropped replicas out), `findings`."""

    plans: tuple[PagePlan, ...]
    columns: tuple[Column, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class Placement:
    """The pages placed: each plan's `(placed, first call)`, reservations taken off."""

    plans: tuple[PagePlan, ...]
    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    pages: list[tuple[tuple[PlacedFunction, ...], FirstCall]]
    placed_all: tuple[PlacedFunction, ...]
    findings: tuple[Finding, ...]
    # layout-0182: each cell's image room
    rooms: Mapping[tuple[AuthoringKey, Handle], tuple[int, int]] = field(default_factory=dict)


# `references` over one attempt's planned and stacked pages, with its findings
type Decide = Callable[[Seating], tuple[References, tuple[Finding, ...]]]


def plan_pages(
    run: PageRun,
    drawn: tuple[DrawnFunction, ...],
    columns: tuple[Column, ...],
    widths: tuple[ColumnWidth, ...],
) -> Planned:
    """Stage 3: partition `columns` into pages at `widths`, then drop unneeded replicas."""
    inputs = run.inputs
    plans, findings = partition(
        columns,
        ColumnTables(
            widths=widths,
            groups=inputs.groups,
            locations=inputs.locations,
            units=inputs.units,
            pole_links=tuple(
                sorted(
                    {
                        *pole_links(columns, drawn, inputs.connections, inputs.net_groups),
                        *beside_links(columns),
                    }
                )
            ),
            bands=middle_bands(inputs.middle, inputs.profile),
            functions=inputs.functions,
            landing=column_landing(
                columns, function_landing(drawn, inputs.connections, run.landing)
            ),
        ),
        hints=inputs.hints,
        profile=inputs.profile,
        sheet=inputs.sheet,
    )
    return Planned(*planned_columns(plans, columns, drawn, inputs), findings)


def _seated(plans: tuple[PagePlan, ...], columns: tuple[Column, ...]) -> tuple[Seat, ...]:
    """Every planned column's cells on its page, in plan order then handle, before `place`."""
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
    """Stages 4, 5: decide references, place, settle box sides, widths."""
    inputs = run.inputs
    for attempt in range(2):
        pages, page_found, page_rooms, decided = _place_each(
            run, planned.plans, planned.columns, drawn, decide
        )
        placed_all = tuple(one for placed, _ in pages for one in placed)
        turned = (
            box_sides(
                placed_all,
                drawn,
                inputs.connections,
                run.landing,
                beside_cells(planned.columns),
            )
            if attempt == 0
            else drawn
        )
        if turned == drawn:
            break
        drawn = turned
    grown = placed_widths(
        widths,
        placed_all,
        inputs.profile.column_gap,
        page_extras(inputs, planned.columns, drawn, pages, decided[0]),
    )
    pages = [(unreserve(placed, page_rooms), first) for placed, first in pages]
    placed_all = unreserve(placed_all, page_rooms)
    findings = (*planned.findings, *page_found)
    placement = Placement(
        planned.plans, planned.columns, drawn, pages, placed_all, findings, page_rooms
    )
    return placement, grown, decided


def _place_each(
    run: PageRun,
    plans: tuple[PagePlan, ...],
    columns: tuple[Column, ...],
    drawn: tuple[DrawnFunction, ...],
    decide: Decide,
) -> tuple[list[Any], list[Any], dict[Any, Any], tuple[References, tuple[Finding, ...]]]:
    """Each plan's `_place_page`: placed, findings, rooms, decisions; slices."""
    pages, found = [], []
    page_rooms = rooms(run.reserves, drawn, plans, run.inputs)
    own = page_columns(plans, columns)
    on_page = pages_of(own)
    drawn_at = by_page(drawn, FUNCTION, on_page, len(plans))
    specs_at = by_page(run.inputs.functions, FUNCTION, on_page, len(plans))
    requests_at = by_page(
        run.pin_requests,
        partial(_function_of, owner=owner_of(drawn)),
        on_page,
        len(plans),
    )
    connections_at = by_ends(
        run.inputs.connections, connection_ends, on_page, count=len(plans), every=True
    )
    rooms_at = rooms_by_page(page_rooms, plans)
    # layout-0135: each set's box width, from the digits known before `place` (not `refs`)
    sized = digits_by_set(plans, run.paths_of(plans), run.unit_paths_of(plans))
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
    # `references` decides on each page as `place` stacks it, before any is placed
    stacks = {(one.plan.drawing_set, one.plan.number): _page_stack(one) for one in work}
    seats = _seated(plans, columns)
    decided = decide(Seating(plans, columns, drawn, seats, stacks))
    # Room's N or S call reads each page's texts as decided, and the wiring on the page
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


def finish_page(
    page: PageState,
    drawn: tuple[DrawnFunction, ...],
    inputs: PageInputs,
    *,
    references: tuple[LabelRequest, ...],
) -> tuple[tuple[Route, ...], tuple[PlacedLabel, ...], tuple[Finding, ...]]:
    """Place cross-reference labels, then route the page (layout-0038)."""
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
        PageRoom(
            reserved=held,
            profile=inputs.profile,
            sheet=inputs.sheet,
            markers=markers,
            blocks=page.blocks,
            wrap_gap=WRAP_GAP,
            aside=frozenset(
                c.handle for c in inputs.connections if (c.a.port, c.b.port) in inputs.aside
            ),
        ),
    )
    return routes, slot_labels, (*second_findings, *route_findings)


def _function_of(request: LabelRequest, owner: Mapping[Handle, Handle]) -> Handle:
    """The function a request is drawn on: a `MARKING` subject is a model port."""
    marking = request.kind is LabelKind.MARKING
    return (request.function or owner[request.subject]) if marking else request.subject
