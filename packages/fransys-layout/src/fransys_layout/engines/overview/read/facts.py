"""One view's rows to its `ViewFacts`: the measured diagram facts, the sheet cut turned off."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.overview.read.column import open_column
from fransys_layout.engines.overview.read.values import (
    BoxSpec,
    LaneHead,
    LanePlan,
    LineSpec,
    ViewFacts,
)
from fransys_layout.engines.overview.sheet_values import BoxFacts, DiagramFacts, LineFacts
from fransys_layout.engines.overview.sizes import TEXT_PAD
from fransys_layout.geometry import snap_up, text_width
from fransys_model.derive import text_room_g
from fransys_model.layout.tables import profile_of, sheet_format_of
lazy from fransys_model.kernel import Id, Model

if TYPE_CHECKING:
    from fransys_model.layout import OverviewMode, OverviewRef

NO_SHEET = 10_000_000  # grid units: wide and tall enough that the diagram placer cuts nothing


def _box(spec: BoxSpec, height: int) -> BoxFacts:
    """A box's measured text lines."""
    return BoxFacts(
        box=spec.box,
        text_widths=tuple(text_width(t, height=height) for t in spec.lines),
        dashed=spec.dashed,
    )


def _tab(text: str | None, height: int) -> int | None:
    """The text width of a tab, or `None` for no tab."""
    return None if text is None else text_width(text, height=height)


def _line(spec: LineSpec, height: int) -> LineFacts:
    """A line's measured label; an empty text measures as one space, as the diagram's does."""
    return LineFacts(
        cable=spec.carrier,
        a=spec.a,
        b=spec.b,
        label_width=text_width(spec.text or " ", height=height),
        tab_a=_tab(spec.tab_a, height),
        tab_b=_tab(spec.tab_b, height),
    )


def view_facts(
    model: Model,
    level: tuple[Id[Any] | None, OverviewRef | None, OverviewMode],
    open_: OverviewRef | None,
    specs: tuple[tuple[BoxSpec, ...], tuple[LineSpec, ...]],
    plan: LanePlan,
) -> ViewFacts:
    """The facts of one view: sizes from the profile, no sheet limit, the profile's penalties.

    `level` is the view's unit, opened level box and mode; `open_` its open strip's ref; `plan`
    each box's lane and the text of each lane (lanes mode only).
    """
    unit, opened, mode = level
    boxes, lines = specs
    column, left = open_column(model, unit, open_, specs)
    profile = profile_of(model)
    height = text_room_g(
        model, profile.text_height_mm, sheet_format_of(model, profile.sheet_format)
    )
    diagram = DiagramFacts(
        unit=unit,
        boxes=tuple(_box(b, height) for b in boxes),
        lines=tuple(_line(ln, height) for ln in lines),
        text_height=height,
        turn_penalty=profile.route_turn_penalty,
        crossing_penalty=profile.route_crossing_penalty,
        width=NO_SHEET,
        height=NO_SHEET,
        column=column,
        left=left,
        row_height=snap_up(height + 2 * TEXT_PAD),
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
        heads=tuple(
            LaneHead(owner=o, text=t, width=text_width(t, height=height))
            for o, t in zip(plan.head_owners, plan.head_texts, strict=True)
        ),
        west=plan.west,
        power=plan.power,
        join=plan.join,
        rank=plan.rank,
    )
