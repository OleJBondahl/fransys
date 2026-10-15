"""The finishing steps of the engine loop: the outlines and the cross-reference requests."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.stages.box_leads import lead_ends
from fransys_layout.stages.box_views import (
    cell_views,
    face_plugs,
    hidden_views,
    moved_markers,
    moved_views,
    placed_boxes,
    slot_rows,
)
from fransys_layout.stages.content import content_box
from fransys_layout.stages.external_outlines import ExternalInputs, external_outlines
from fransys_layout.stages.outlines import OutlineInputs, unit_outlines
from fransys_layout.stages.space import Blocks
from fransys_layout.stages.texts.echoes import echo_requests
from fransys_layout.stages.texts.power_moved import PowerFrame, PowerRedo, reset_power

from ._middle import with_middle
from .read.harness_lines import plug_mates
from .read.location_paths import location_paths
from .read.outline_texts import outline_titles
from .read.units import black_boxes, external_note_text, external_roots

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.stages import Column
    from fransys_layout.stages.box_views import BoxSpec
    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_layout.stages.middle_fold import GroupShape
    from fransys_layout.stages.pagerun import Placement
    from fransys_layout.stages.references import References
    from fransys_layout.stages.types import (
        DrawnFunction,
        LabelRequest,
        LinkMarker,
        PagePlan,
        PlacedExternalOutline,
        PlacedFunction,
        PlacedLabel,
        PlacedOutline,
    )
    from fransys_model.kernel import Model

    from .read import StageInputs
    from .read.harness_lines import LineReads

type Pages = Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]]


@dataclass(frozen=True, slots=True)
class Laid:
    """The pages as laid: plans, pages, markers, placed functions and the moved middle shapes."""

    plans: tuple[PagePlan, ...]
    pages: Pages
    markers: tuple[LinkMarker, ...]
    placed: Sequence[PlacedFunction]
    shapes: Sequence[GroupShape]


def boxed(
    inputs: StageInputs,
    placed: tuple[Sequence[PlacedFunction], Sequence[DrawnFunction]],
    specs: tuple[BoxSpec, ...],
    lines: LineReads,
) -> tuple[PlacedConnectorBox, ...]:
    """Each connector box over its pin views, its cells facing their leads (layout-0211).

    The plug it mates touches it on the other edge, where the line leaves.
    """
    placed_all, drawn = placed
    content = content_box(inputs.sheet)
    reach = lead_ends(inputs.connections, placed_all, drawn, hidden_views(specs))
    placed_box = placed_boxes(placed_all, specs, inputs.profile.text_height, content, reach)
    return face_plugs(placed_box, plug_mates(lines))


PageBlocks = dict[tuple[int, int], Blocks]


def cells_placed(
    pages: Pages,
    placed_all: Sequence[PlacedFunction],
    markers: tuple[LinkMarker, ...],
    placed_box: Sequence[PlacedConnectorBox],
) -> tuple[Pages, list[PlacedFunction], tuple[LinkMarker, ...], PageBlocks]:
    """HL19: each celled pin view and its marker move under its cell; the slot row is closed."""
    moves = cell_views(placed_all, placed_box)
    return (
        [(tuple(moved_views(on, moves)), labels) for on, labels in pages],
        moved_views(placed_all, moves),
        moved_markers(markers, moves),
        slot_rows(placed_box),
    )


def outlined(
    model: Model,
    inputs: StageInputs,
    columns: tuple[Column, ...],
    laid: Laid,
    placed_box: tuple[PlacedConnectorBox, ...],
) -> tuple[list[Any], tuple[PlacedOutline, ...], tuple[PlacedConnectorBox, ...]]:
    """The pages, outlines and boxes with each black box's dash-dot outline and its title."""
    moved = frozenset((one.unit, one.drawing_set, one.page) for one in laid.shapes)
    titled = OutlineInputs(
        inputs.functions,
        columns,
        inputs.profile,
        outline_titles(model),
        placed_box,
        moved,
        black_boxes(model),
        inputs.sheet.inset,
    )
    pages, outlines = unit_outlines(laid.plans, laid.pages, laid.markers, titled)
    return with_middle(laid.plans, pages, outlines, placed_box, laid.shapes)


def cross_references(
    model: Model,
    inputs: StageInputs,
    placement: Placement,
    echoes: References,
    contact_refs: tuple[LabelRequest, ...],
) -> tuple[LabelRequest, ...]:
    """The echoes: the cross-reference requests, an echo holding its (subject, slot)."""
    held = echo_requests(
        echoes.echoes,
        placement.placed_all,
        placement.drawn,
        sheet=inputs.sheet,
        location_paths=location_paths(model, placement.plans),
    )
    taken = {(r.subject, r.slot) for r in held}
    return (*held, *(r for r in contact_refs if (r.subject, r.slot) not in taken))


def outlined_cells(
    model: Model,
    inputs: StageInputs,
    columns: tuple[Column, ...],
    laid: Laid,
    placed_box: tuple[PlacedConnectorBox, ...],
) -> tuple[
    Pages,
    tuple[PlacedOutline, ...],
    tuple[PlacedExternalOutline, ...],
    tuple[PlacedConnectorBox, ...],
    list[PlacedFunction],
    tuple[LinkMarker, ...],
    PageBlocks,
    PowerRedo,
]:
    """`outlined`, then the pin views onto their cells (HL19), then the outlines by others.

    The cells move after the black boxes, so no group shifts; the outlines by others stand on the
    finished placements.
    """
    pages, outlines, placed_box = outlined(model, inputs, columns, laid, placed_box)
    pages, placed, markers, blocks = cells_placed(pages, laid.placed, laid.markers, placed_box)
    power = PowerFrame(inputs.sheet, inputs.profile, inputs.power_slot)
    pages, markers, redo = reset_power(laid.plans, pages, markers, laid.markers, power)
    by_others = ExternalInputs(
        {spec.function: spec for spec in inputs.functions},
        external_roots(model),
        inputs.profile.text_height,
        external_note_text(),
    )
    pages, external = external_outlines(laid.plans, pages, markers, by_others)
    return pages, outlines, external, placed_box, placed, markers, _along(blocks, external), redo


def _along(blocks: PageBlocks, external: Sequence[PlacedExternalOutline]) -> PageBlocks:
    """BO6-SHRINK: each page's blocks gain its outlines by others as boxes no wire runs along."""
    found = dict(blocks)
    for one in external:
        here = (one.drawing_set, one.page)
        before = found.get(here, Blocks())
        found[here] = replace(before, sides=(*before.sides, one.box))
    return found
