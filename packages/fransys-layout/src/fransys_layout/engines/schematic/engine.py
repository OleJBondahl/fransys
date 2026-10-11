"""Schematic engine: multi-page ladder-style circuit diagrams, as a pass."""

from dataclasses import replace
from functools import partial
from typing import TYPE_CHECKING, Any

from fransys_layout.stages import (
    Column,
    DrawnFunction,
    LabelKind,
    Layout,
    onepage,
)
from fransys_layout.stages.box_views import drawn_hidden, hidden_views
from fransys_layout.stages.boxes import port_ranks, potential_sides, power_maps
from fransys_layout.stages.connector_boxes import PlacedConnectorBox
from fransys_layout.stages.exempt import ExemptInputs, boundary_exempt, open_ends
from fransys_layout.stages.finish import FinishRun, finish_pages, ink_keepouts
from fransys_layout.stages.firstlabels import labelled_pages
from fransys_layout.stages.images import contact_images
from fransys_layout.stages.middle_tall import recut, tall_groups
from fransys_layout.stages.offstubs import OffEnd
from fransys_layout.stages.onepage import page_wiring
from fransys_layout.stages.pagerun import PageInputs, PageRun, Placement, place_pages, plan_pages
from fransys_layout.stages.references import (
    box_room_findings,
)
from fransys_layout.stages.stacking import JoinedRun
from fransys_layout.stages.tags import own_set_texts, row_labels
from fransys_layout.stages.texts.marker_room import MarkerRoom
from fransys_layout.stages.texts.marker_row import place_markers
from fransys_layout.stages.texts.markers import link_markers, placed_world
from fransys_layout.stages.texts.power import without_power_findings
from fransys_layout.stages.tidy import clear_of_stubs, shift_pages
from fransys_model.kernel import Finding, Id, value

from ._arrange_columns import (
    arranged,
)
from ._decide import decide
from ._finish import Laid, boxed, cross_references, outlined
from ._lines import DrawnPieces, LineScene, draw_lines, harness_ink, strip_lines
from ._lint import LintScene, Members, lint_findings
from ._middle import middle_inputs, moved_shapes, strip_middle
from ._sizing import sized
from .defaults import BOTTOM_HEADROOM_LANES, DEFAULT_RULES, TOP_HEADROOM_LANES
from .read import read_inputs
from .read.harness_lines import box_specs
from .read.labels import label_requests
from .read.line_texts import marker_keepouts
from .read.location_paths import location_paths
from .read.tag_texts import tag_texts
from .read.units import (
    boundary_edge_set,
    unit_nesting,
)
from .read.write_keys import write_keys
from .symbol_defaults import resolve_with_defaults
from .write import write_layout

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages import ColumnWidth
    from fransys_layout.stages.pagerun import Decide
    from fransys_layout.stages.references import References
    from fransys_model.kernel import Model

    from .read import StageInputs


@value
class StageResults:
    """What the stages produced: the `Layout`, the drawn functions and every column planned."""

    layout: Layout
    drawn: tuple[DrawnFunction, ...]
    columns: tuple[Column, ...]
    sheet_format: Id[Any] | None
    off_ends: tuple[OffEnd, ...] = ()
    joins: tuple[JoinedRun, ...] = ()
    boxes: tuple[PlacedConnectorBox, ...] = ()
    hidden: tuple[Id[Any], ...] = ()
    lines: DrawnPieces = DrawnPieces()


def run_stages(
    model: Model, inputs: StageInputs
) -> tuple[Layout, tuple[DrawnFunction, ...], tuple[Finding, ...]]:
    """Run stages 1 to 9 over `inputs`."""
    results, findings = stage_results(model, inputs)
    return results.layout, results.drawn, findings


def stage_results(model: Model, inputs: StageInputs) -> tuple[StageResults, tuple[Finding, ...]]:
    """The engine loop: everything `write/` needs, and the findings of every stage."""
    drawn, resolve_findings = resolve_with_defaults(inputs.functions, DEFAULT_RULES, inputs.choices)
    rank_of = port_ranks(inputs.functions)
    power = power_maps(inputs.power, inputs.item_north, inputs.item_south)
    drawn = potential_sides(drawn, rank_of, *power, (inputs.feeds, inputs.profile))
    # a boxed connector's pin views draw no symbol and no label; its box stands over them
    boxes = box_specs(model, inputs.functions)
    hidden = hidden_views(boxes)
    slot_requests = tuple(
        request
        for request in label_requests(inputs.label_texts, drawn)
        if request.kind in (LabelKind.TAG, LabelKind.MARKING) and request.subject not in hidden
    )

    inputs, all_columns, columns, column_findings = arranged(model, inputs, drawn, rank_of)
    # a middle unit's line views leave their columns; its lines' conductors are no routes
    inputs, columns, middle, reach = strip_middle(model, inputs, columns)
    inputs, lines = strip_lines(model, inputs)
    texts = tag_texts(model)
    slot_requests, pin_requests = row_labels(texts, inputs.functions, all_columns, slot_requests)
    own_set = own_set_texts(texts, boundary_edge_set(model), slot_requests, inputs.functions)
    drawn, widths, img, reserves = sized(model, inputs, drawn, columns, own_set)
    run = PageRun(
        texts,
        middle_inputs(_page_inputs(inputs, img.heads), middle, (columns, reach, widths)),
        rank_of,
        pin_requests,
        reserves,
        partial(location_paths, model),
        power,
    )
    # layout-0080: the ports at a unit's boundary that draw nothing, in the markers and the check
    nesting = unit_nesting(model, {spec.unit for spec in inputs.functions})
    # `references` decides on the planned pages, before each placing (`decide`)
    placement, (decided, reference_findings) = _placed(
        run, drawn, columns, widths, partial(decide, model, inputs, nesting)
    )
    plans, columns, drawn = placement.plans, placement.columns, placement.drawn
    findings = [*inputs.read_findings, *resolve_findings, *column_findings, *placement.findings]
    # layout-0071: the member check reads the membership before the stars are taken out
    members = Members(
        inputs.connections,
        inputs.net_groups,
        boundary_exempt(
            ExemptInputs(
                inputs.connections, inputs.net_groups, inputs.functions, plans, placement.placed_all
            ),
            nesting,
        ),
    )
    findings.extend(reference_findings)
    inputs = replace(inputs, connections=decided.connections, net_groups=decided.net_groups)
    # `texts` builds every marker from its decision, on the placed pages
    at_home, routed_on, wired = page_wiring(
        inputs.connections, columns, placement.placed_all, inputs.net_groups
    )
    built = link_markers(
        decided.markers,
        placed_world(placement.placed_all, placement.drawn),
        wired=wired,
        sheet=inputs.sheet,
        profile=inputs.profile,
    )
    # The markers go through the placer first, then each page's tags and markings with
    # every marker's box and stub standing; the shift comes after them
    markers, marker_findings = place_markers(
        built,
        placement.placed_all,
        placement.drawn,
        MarkerRoom(columns, inputs.connections, decided.joins, wired, inputs.sheet, inputs.profile),
    )
    pages, markers, first = labelled_pages(
        plans, placement.pages, markers, inputs.power_slot, inputs.sheet
    )
    findings.extend((*without_power_findings(marker_findings, markers), *first))
    pages = clear_of_stubs(plans, pages, markers, inputs.sheet)
    # A page whose labels or keep-outs poke past the content box moves inward by whole
    # grids when its far side has the room (a strip tag left of the first column); its markers
    # move with it, but a marker box never causes the shift (layout-0068), and a box
    # the shift pushes out of the content box is reported by OUT_OF_CONTENT_BOX
    pages, placed_all, markers = shift_pages(plans, pages, markers, inputs.sheet)
    # The contact image under each coil, and each contact's reference to its coil
    pages, contact_refs = contact_images(plans, pages, img, markers, location_paths(model, plans))
    # model-0059: each black box's dash-dot outline and its title, before routing
    placed_box = boxed(inputs, placed_all, boxes, lines)
    laid = Laid(
        plans,
        pages,
        markers,
        placed_all,
        moved_shapes(placement.pages, placement.placed_all, placed_all),
    )
    pages, outlines, placed_box = outlined(model, inputs, columns, laid, placed_box)
    crossings = cross_references(model, inputs, placement, decided, contact_refs)

    routes, labels, page_findings = finish_pages(
        plans,
        pages,
        FinishRun(columns, drawn, _page_inputs(inputs, img.heads), markers, crossings, routed_on),
    )
    findings.extend(page_findings)
    routes = onepage.keep_chosen_edges(routes, inputs.net_groups, at_home)
    # layout-0154: the lines over the finished page, clear of its symbols, boxes and texts
    scene = LineScene(
        placed_all,
        drawn,
        placed_box,
        (*labels,),
        marker_keepouts(model, markers),
        inputs.profile,
        inputs.sheet,
        frozenset(hidden),
        {plan.drawing_set: plan.unit for plan in plans},
    )
    drawn_lines = draw_lines(model, lines, inputs.carried, middle, scene)

    layout = Layout(
        pages=plans,
        placed=ink_keepouts(placed_all, labels, drawn),
        routes=tuple(routes),
        decisions=decided.decisions,
        markers=markers,
        labels=tuple(labels),
        outlines=outlines,
    )
    # layout-0158: the lint reads the lines, the boxes, and the boxed pin views that draw nothing
    ink = harness_ink(drawn_lines, placed_box, drawn_hidden(placed_all, hidden, markers))
    edges = open_ends(inputs.functions, boundary_edge_set(model))
    lint = lint_findings(LintScene(layout, columns, drawn, inputs, members, edges, ink))
    findings.extend((*drawn_lines.findings, *lint))
    planned = {planned.column for plan in plans for planned in plan.columns}
    return StageResults(
        layout=layout,
        drawn=drawn,
        columns=tuple(column for column in columns if column.key in planned),
        sheet_format=inputs.sheet_format,
        off_ends=decided.off_ends,
        joins=decided.joins,
        boxes=placed_box,
        hidden=tuple(sorted(hidden)),
        lines=drawn_lines,
    ), tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))


def _placed(
    run: PageRun,
    drawn: tuple[DrawnFunction, ...],
    columns: tuple[Column, ...],
    widths: tuple[ColumnWidth, ...],
    decide: Decide,
) -> tuple[Placement, tuple[References, tuple[Finding, ...]]]:
    """`plan_pages`, `references`, `place`; again on grown widths; room check (0143).

    The second pass also cuts the groups the first placing folded below the page.
    """
    planned = plan_pages(run, drawn, columns, widths)
    first = planned.plans
    placement, grown, decided = place_pages(run, drawn, planned, widths, decide)
    tall = tall_groups(placement.pages, run.inputs.sheet.content_height, run.inputs.middle)
    if grown != widths or tall:
        run = recut(run, tall)
        planned = plan_pages(run, placement.drawn, columns, grown)
        placement, _, decided = place_pages(run, placement.drawn, planned, grown, decide)
    return placement, box_room_findings(decided, first)


def _page_inputs(inputs: StageInputs, heads: Mapping[Id[Any], str]) -> PageInputs:
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
    )


def lay_out_schematic(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Lay out every drawn function of `model` and return the laid-out model.

    Read, `stage_results` in stage order, then `write_layout`. Pure and deterministic:
    the same model digest gives the same `digests["layout"]`, whatever order the records were
    authored in, and `digests["core"]`/`digests["facet"]` are unchanged. A model that
    already holds derived layout records has them replaced. Findings are sorted by
    `(code, subjects, message)`. A half-finished design still lays out; only structural
    problems raise (`LayoutError`).
    """
    results, findings = stage_results(model, inputs := read_inputs(model))
    keys = write_keys(model, inputs.functions)
    return write_layout(model, results, keys), findings
