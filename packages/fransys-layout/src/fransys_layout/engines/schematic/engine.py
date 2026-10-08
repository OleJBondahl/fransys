"""Schematic engine: multi-page ladder-style circuit diagrams, as a pass.

Refs: foundations.md 3, engine.md 7.
"""

from dataclasses import dataclass, replace
from functools import partial
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping

from fransys_layout.lint import (
    HarnessInk,
    check_coherence,
    check_members,
    check_nowhere,
    lint_chains,
    lint_geometry,
)
from fransys_layout.lint.chains import StageRecords
from fransys_layout.stages import (
    Column,
    DrawnFunction,
    LabelKind,
    Layout,
    onepage,
)
from fransys_layout.stages.arrange import (
    inline_exits,
)
from fransys_layout.stages.box_reach import sized_columns
from fransys_layout.stages.box_views import drawn_hidden, face_plugs, hidden_views, placed_boxes
from fransys_layout.stages.boxes import port_ranks, potential_sides, power_maps
from fransys_layout.stages.connector_boxes import PlacedConnectorBox
from fransys_layout.stages.content import content_box
from fransys_layout.stages.exempt import ExemptInputs, boundary_exempt, open_ends
from fransys_layout.stages.finish import FinishRun, finish_pages, ink_keepouts
from fransys_layout.stages.firstlabels import labelled_pages
from fransys_layout.stages.images import contact_images, image_reserves, with_flipped_below
from fransys_layout.stages.middle_tall import recut, tall_groups
from fransys_layout.stages.offstubs import OffEnd
from fransys_layout.stages.onepage import page_wiring
from fransys_layout.stages.outlines import OutlineInputs, unit_outlines
from fransys_layout.stages.pagerun import PageInputs, PageRun, Placement, place_pages, plan_pages
from fransys_layout.stages.references import (
    ReferenceInputs,
    Wiring,
    black_box_sets,
    box_room_findings,
    references,
    side_reference_rooms,
)
from fransys_layout.stages.stacking import JoinedRun
from fransys_layout.stages.tags import own_set_texts, row_labels
from fransys_layout.stages.texts.echoes import echo_requests
from fransys_layout.stages.texts.marker_room import MarkerRoom
from fransys_layout.stages.texts.marker_row import place_markers
from fransys_layout.stages.texts.markers import link_markers, placed_world
from fransys_layout.stages.texts.power import without_power_findings
from fransys_layout.stages.tidy import clear_of_stubs, shift_pages
from fransys_model.kernel import Finding, Id, value

from ._arrange_columns import (
    chained_columns,
    discovered_columns,
    ordered_columns,
    replicated_columns,
)
from ._lines import DrawnPieces, LineScene, draw_lines, harness_ink, strip_lines
from ._middle import middle_inputs, moved_shapes, strip_middle, with_middle
from .defaults import BOTTOM_HEADROOM_LANES, DEFAULT_RULES, TOP_HEADROOM_LANES
from .read import read_inputs, reading
from .read.contact_marks import image_inputs
from .read.harness_lines import box_specs, plug_mates
from .read.labels import label_requests
from .read.line_texts import marker_keepouts
from .read.location_paths import location_paths
from .read.outline_texts import outline_titles
from .read.tag_texts import tag_texts
from .read.units import (
    black_box_reads,
    black_boxes,
    boundary_edge_set,
    unit_nesting,
)
from .read.write_keys import write_keys
from .symbol_defaults import resolve_with_defaults
from .write import write_layout

if TYPE_CHECKING:
    from fransys_layout.stages import ColumnWidth
    from fransys_layout.stages.exempt import UnitNesting
    from fransys_layout.stages.pagerun import Decide
    from fransys_layout.stages.references import References
    from fransys_layout.stages.references.types import Seating
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
    """Run stages 1 to 9 over `inputs` (WP13)."""
    results, findings = stage_results(model, inputs)
    return results.layout, results.drawn, findings


def stage_results(model: Model, inputs: StageInputs) -> tuple[StageResults, tuple[Finding, ...]]:
    """The engine loop: everything `write/` needs, and the findings of every stage."""
    drawn, resolve_findings = resolve_with_defaults(inputs.functions, DEFAULT_RULES, inputs.choices)
    rank_of = port_ranks(inputs.functions)
    power = power_maps(inputs.power, inputs.item_north, inputs.item_south)
    drawn = potential_sides(drawn, rank_of, *power, (inputs.feeds, inputs.profile))
    # HL6: a boxed connector's pin views draw no symbol and no label; its box stands over them
    boxes = box_specs(model, inputs.functions)
    hidden = hidden_views(boxes)
    slot_requests = tuple(
        request
        for request in label_requests(inputs.label_texts, drawn)
        if request.kind in (LabelKind.TAG, LabelKind.MARKING) and request.subject not in hidden
    )

    inputs, all_columns, columns, column_findings = _arranged(model, inputs, drawn, rank_of)
    # HL11: a middle unit's line views leave their columns; its lines' conductors are no routes
    inputs, columns, middle, reach = strip_middle(model, inputs, columns)
    inputs, lines = strip_lines(model, inputs)
    texts = tag_texts(model)
    slot_requests, pin_requests = row_labels(texts, inputs.functions, all_columns, slot_requests)
    # C8(b), S11: columns are sized with the keep-outs grown by the measured labels and by
    # Room's first call for a reference beside an E or W port
    own_set = own_set_texts(texts, boundary_edge_set(model), slot_requests, inputs.functions)
    sides = side_reference_rooms(
        columns,
        drawn,
        Wiring(inputs.connections, inputs.net_groups),
        sheet=inputs.sheet,
        profile=inputs.profile,
    )
    # V5: a box's pins stand a contact's width apart, from the keep-outs grown by the labels
    drawn, widths = sized_columns(columns, drawn, own_set, sides, inputs.profile)
    # I4 Q1: room for each contact image under its coil's lane, kept while placing
    img = image_inputs(model, inputs)
    every = (*inputs.functions, *inputs.spares)
    heights = {one.function: one.geometry.keepout.height for one in drawn}
    reserves = image_reserves(columns, every, inputs.profile, img.marks, img.owners)
    reserves = with_flipped_below(reserves, columns, heights)
    paths = partial(location_paths, model)
    run = PageRun(
        texts,
        middle_inputs(_page_inputs(inputs), middle, (columns, reach, widths)),
        rank_of,
        pin_requests,
        reserves,
        paths,
        power,
    )
    # layout-0080: the ports at a unit's boundary that draw nothing, in the markers and the check
    nesting = unit_nesting(model, {spec.unit for spec in inputs.functions})
    # S10: `references` decides on the planned pages, before each placing (`_decide`)
    decide = partial(_decide, model, inputs, nesting)
    placement, (decided, reference_findings) = _placed(run, drawn, columns, widths, decide)
    plans, columns, drawn = placement.plans, placement.columns, placement.drawn
    pages, placed_all = placement.pages, placement.placed_all
    findings = [*inputs.read_findings, *resolve_findings, *column_findings, *placement.findings]
    exempt = boundary_exempt(
        ExemptInputs(inputs.connections, inputs.net_groups, inputs.functions, plans, placed_all),
        nesting,
    )
    # layout-0071: the member check reads the membership before the stars are taken out
    members = (inputs.connections, inputs.net_groups, exempt)
    findings.extend(reference_findings)
    inputs = replace(inputs, connections=decided.connections, net_groups=decided.net_groups)
    # S9: `texts` builds every marker from its decision, on the placed pages
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
    # S20: the markers go through D3's placer first, then each page's tags and markings with
    # every marker's box and stub standing; R2 and C22b's shift after them
    markers, marker_findings = place_markers(
        built,
        placement.placed_all,
        placement.drawn,
        MarkerRoom(columns, inputs.connections, decided.joins, wired, inputs.sheet, inputs.profile),
    )
    pages, markers, first = labelled_pages(plans, pages, markers, inputs.power_slot, inputs.sheet)
    findings.extend((*without_power_findings(marker_findings, markers), *first))
    pages = clear_of_stubs(plans, pages, markers, inputs.sheet)
    # C22b: a page whose labels or keep-outs poke past the content box moves inward by whole
    # grids when its far side has the room (a strip tag left of the first column); its markers
    # move with it, but a marker box never causes the shift (D14 M2, layout-0068), and a box
    # the shift pushes out of the content box is reported by OUT_OF_CONTENT_BOX
    pages, placed_all, markers = shift_pages(plans, pages, markers, inputs.sheet)
    shapes = moved_shapes(placement.pages, placement.placed_all, placed_all)
    # C19: the contact image under each coil, and each contact's reference to its coil
    pages, contact_refs = contact_images(plans, pages, img, markers, location_paths(model, plans))
    # I2a: each black box's dash-dot outline and its title, before routing
    placed_box = placed_boxes(
        placed_all, boxes, inputs.profile.text_height, content_box(inputs.sheet)
    )
    placed_box = face_plugs(placed_box, plug_mates(lines))  # HL4, HL19
    pages, outlines = unit_outlines(
        plans,
        pages,
        markers,
        OutlineInputs(
            inputs.functions,
            columns,
            inputs.profile,
            outline_titles(model),
            placed_box,
            frozenset((one.unit, one.drawing_set, one.page) for one in shapes),
            black_boxes(model),
        ),
    )
    pages, outlines, placed_box = with_middle(plans, pages, outlines, placed_box, shapes)
    echoes = echo_requests(
        decided.echoes,
        placement.placed_all,
        placement.drawn,
        sheet=inputs.sheet,
        location_paths=location_paths(model, plans),
    )
    held = {(r.subject, r.slot) for r in echoes}
    cross_references = (*echoes, *(r for r in contact_refs if (r.subject, r.slot) not in held))

    routes, labels, page_findings = finish_pages(
        plans,
        pages,
        FinishRun(columns, drawn, _page_inputs(inputs), markers, cross_references, routed_on),
    )
    findings.extend(page_findings)
    routes = onepage.keep_chosen_edges(routes, inputs.net_groups, at_home)
    # HL15 to HL18: the lines over the finished page, clear of its symbols, boxes and texts
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
    lint = _lint_findings(LintScene(layout, columns, drawn, inputs, members, edges, ink))
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
    """S10: `plan_pages`, `references`, `place`; again on grown widths (C21); room check (0143).

    TALL-PAGE T5: the second pass also cuts the groups the first placing folded below the page.
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


def _decide(
    model: Model,
    inputs: StageInputs,
    nesting: UnitNesting,
    seating: Seating,
) -> tuple[References, tuple[Finding, ...]]:
    """D1 step 4 (S10): `references` on one placing attempt's planned and stacked pages."""
    exempt = boundary_exempt(
        ExemptInputs(
            inputs.connections, inputs.net_groups, inputs.functions, seating.plans, seating.seats
        ),
        nesting,
    )
    return references(_reference_inputs(model, inputs, seating, (exempt, nesting.nested)))


def _page_inputs(inputs: StageInputs) -> PageInputs:
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
    )


def _arranged(
    model: Model, inputs: StageInputs, drawn: tuple[DrawnFunction, ...], rank_of: Mapping[Any, int]
) -> tuple[
    StageInputs,
    tuple[Column, ...],
    tuple[Column, ...],
    tuple[Finding, ...],
]:
    """Stage 2: the columns of the run."""
    tie_key = reading.terminal_sort_keys(model, inputs.functions)
    discovered = discovered_columns(model, inputs, drawn, rank_of, tie_key)
    crossing = set(inputs.crossing)
    inputs = replace(inputs, connections=tuple(c for c in inputs.connections if c not in crossing))
    chained, column_findings = chained_columns(inputs, drawn, discovered)
    all_columns, chains = ordered_columns(inputs, drawn, chained + discovered, tie_key)
    inputs = replace(
        inputs,
        connections=inline_exits(inputs.connections, all_columns, inputs.functions, drawn),
        terminal_chains=chains,
    )
    columns = replicated_columns(model, inputs, drawn, all_columns)
    return inputs, all_columns, columns, column_findings


def _unit_maps(
    inputs: StageInputs, seating: Seating
) -> tuple[dict[Id[Any], Id[Any] | None], dict[int, Id[Any] | None]]:
    """Each function's unit, and each drawing set's own unit."""
    unit_of = {spec.function: spec.unit for spec in inputs.functions}
    set_unit = {plan.drawing_set: plan.unit for plan in seating.plans}
    return unit_of, set_unit


def _reference_inputs(
    model: Model,
    inputs: StageInputs,
    seating: Seating,
    boundary: tuple[frozenset[tuple[Id[Any], int]], frozenset[Id[Any] | None]],
) -> ReferenceInputs:
    """D1 step 4's `ReferenceInputs`: `inputs`, the planned pages and what it reads of `model`."""
    exempt, nested = boundary
    unit_of, set_unit = _unit_maps(inputs, seating)
    outward = black_box_sets(
        inputs.functions, seating.seats, unit_of, set_unit, black_box_reads(model, nested)
    )
    return ReferenceInputs(
        sheet=inputs.sheet,
        profile=inputs.profile,
        connections=inputs.connections,
        net_groups=inputs.net_groups,
        functions=inputs.functions,
        seating=seating,
        location_paths=location_paths(model, seating.plans),
        exempt=exempt,
        crossing=inputs.crossing,
        off_texts=inputs.off_texts,
        off_ends=inputs.off_ends,
        outward=outward,
        chains=inputs.terminal_chains,
        power={one.port: one for one in inputs.power},
        rail_ends=inputs.rail_ends,
    )


@dataclass(frozen=True, slots=True)
class LintScene:
    """What stage 9 lints: the `layout` with its `columns` and `drawn` functions, the `inputs`."""

    layout: Layout
    columns: tuple[Column, ...]
    drawn: tuple[DrawnFunction, ...]
    inputs: StageInputs
    members: tuple[tuple[Any, ...], tuple[Any, ...], frozenset[tuple[Any, int]]]
    open_ends: frozenset[Any]
    ink: HarnessInk


def _lint_findings(scene: LintScene) -> list[Finding]:
    """Stage 9: the geometry, chain, coherence and member findings of `scene.layout`."""
    layout, columns, drawn, inputs = scene.layout, scene.columns, scene.drawn, scene.inputs
    members, open_ends = scene.members, scene.open_ends
    findings = list(lint_geometry(layout, sheet=inputs.sheet, ink=scene.ink))
    findings.extend(
        lint_chains(
            layout,
            # HL1: a pin a line carries a conductor to is wired
            StageRecords(
                columns,
                drawn,
                (*inputs.connections, *inputs.carried),
                inputs.net_groups,
                inputs.mates,
            ),
            open_ends=open_ends,
        )
    )
    # R7 B4: star markers answer no cut decision
    paired = replace(layout, markers=tuple(m for m in layout.markers if not m.star))
    function_units = {spec.function: spec.unit for spec in inputs.functions}
    findings.extend(
        check_coherence(
            paired, inputs.connections, inputs.net_groups, drawn, function_units=function_units
        )
    )
    connections, net_groups, exempt = members
    missing = check_members(layout, connections, net_groups, drawn, exempt)
    findings.extend(missing)
    # a stubbed (crossing) conductor is covered by its stubs: the guard reads it too (rule 7)
    findings.extend(
        check_nowhere(layout, (*connections, *inputs.crossing), net_groups, drawn, missing)
    )
    return findings


def lay_out_schematic(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Lay out every drawn function of `model` and return the laid-out model (WP13).

    Read, `stage_results` in foundations.md 3 order, then `write_layout`. Pure and deterministic:
    the same model digest gives the same `digests["layout"]`, whatever order the records were
    authored in, and `digests["core"]`/`digests["facet"]` are unchanged. A model that
    already holds derived layout records has them replaced. Findings are sorted by
    `(code, subjects, message)`. A half-finished design still lays out; only structural
    problems raise (`LayoutError`).
    """
    results, findings = stage_results(model, inputs := read_inputs(model))
    keys = write_keys(model, inputs.functions)
    return write_layout(model, results, keys), findings
