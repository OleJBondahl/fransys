"""One view's rows to its `ViewFacts`: the measured diagram facts, the sheet cut turned off."""

from typing import TYPE_CHECKING, Any

from fransys_layout.core import grid_up
from fransys_layout.engines.overview.read.column import open_column
from fransys_layout.engines.overview.read.values import (
    BoxSpec,
    LaneHead,
    LanePlan,
    LineSpec,
    ViewFacts,
)
from fransys_layout.engines.overview.sheet_values import DiagramFacts
from fransys_layout.engines.overview.sizes import TEXT_PAD, measured_box, measured_line
from fransys_layout.geometry import WIRING_GRID, text_width_g
from fransys_layout.symbols import text_room_on
from fransys_model.layout.tables import sheet_format_of, tuning_of
lazy from fransys_model.kernel import Id, Model

if TYPE_CHECKING:
    from fransys_layout.symbols import SymbolLibrary
    from fransys_model.layout import OverviewMode, OverviewRef

NO_SHEET = 10_000_000  # grid units: wide and tall enough that the diagram placer cuts nothing


def view_facts(
    model: Model,
    level: tuple[Id[Any] | None, OverviewRef | None, OverviewMode, OverviewRef | None],
    specs: tuple[tuple[BoxSpec, ...], tuple[LineSpec, ...]],
    plan: LanePlan,
    library: SymbolLibrary,
) -> ViewFacts:
    """The facts of one view: sizes from the profile, no sheet limit, the profile's penalties.

    `level` is the view's unit, opened level box, mode and open strip's ref; `plan` each box's lane
    and the text of each lane (lanes mode only); `library` sets the text room.
    """
    unit, opened, mode, open_ = level
    boxes, lines = specs
    column, left = open_column(model, unit, open_, specs)
    tuning = tuning_of(model)
    height = text_room_on(model, sheet_format_of(model, None), library)
    diagram = DiagramFacts(
        unit=unit,
        boxes=tuple(measured_box(b.box, b.lines, height, dashed=b.dashed) for b in boxes),
        # an empty text measures as one space, as the diagram's does
        lines=tuple(measured_line((ln.carrier, ln.a, ln.b), ln.text or " ", (ln.tab_a, ln.tab_b), height) for ln in lines),
        text_height=height,
        turn_penalty=tuning.route_turn_penalty,
        crossing_penalty=tuning.route_crossing_penalty,
        width=NO_SHEET,
        height=NO_SHEET,
        column=column,
        left=left,
        row_height=grid_up(height + 2 * TEXT_PAD, WIRING_GRID),
        share_tracks=True,
    )
    return ViewFacts(
        unit=unit,
        level=opened,
        mode=mode,
        open=open_,
        boxes=boxes,
        lines=lines,
        diagram=diagram,
        lanes=plan.lanes,
        heads=tuple(LaneHead(owner=o, text=t, width=text_width_g(t, height=height)) for o, t in zip(plan.head_owners, plan.head_texts, strict=True)),
        west=plan.west,
        power=plan.power,
        join=plan.join,
        rank=plan.rank,
    )
