"""The private core path of the schematic layout step: SWITCHES SW2, deleted at SCHEMATIC-FLIP."""

from typing import TYPE_CHECKING, cast

from fransys_el import (
    ProblemError,
    build,
    house_conventions,
    lay_out_drawn,
    problem_finding,
    read_findings,
    skipped_findings,
    style,
    symbol_kit,
    unknown_symbol_key_findings,
    unknown_symbols,
)
from fransys_render import DrawError, svg

from fransys_layout.symbols import text_room_on
from fransys_model.kernel import render_id
from fransys_model.layout import DrawingSet, Page, layout_of, sheet_format_of
lazy from fransys_model.kernel import Finding

from ._codes import finding
from .settings import settings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Id, Model


def _sheet_mm(model: Model, page: Id[Page]) -> tuple[int, int, int, int]:
    """The paper of `page`: width, height and the content box corner, in mm (render-0027)."""
    sheet = sheet_format_of(model, layout_of(model, Page)[page].sheet_format)
    return sheet.width_mm, sheet.height_mm, sheet.content_x_mm, sheet.content_y_mm


NO_DRAWINGS: Mapping[Id[Page], Drawing] = cast("Mapping[Id[Page], Drawing]", {})

type Laid = tuple[
    Model,
    tuple[Finding, ...],
    Mapping[Id[Page], Drawing],
    dict[str, str],
]


def lay_out_on_core(model: Model, library: Library, layout: Mapping[str, object] | None = None) -> Laid:
    """The laid-out model, the findings, the page `Drawing`s and page SVGs (F7).

    Solved once per location (PAGE-02); a `ProblemError` becomes one ERROR, the model unchanged.
    """
    try:
        kit = symbol_kit(model, library)
        conventions = house_conventions(
            settings().layout if layout is None else layout,
            library,
            text_height=text_room_on(model, sheet_format_of(model, None), library),
        )
        problem, skipped = build(model, kit, conventions, library)
    except ProblemError as error:
        return model, (problem_finding(error, model),), NO_DRAWINGS, {}
    laid, found, drawn = lay_out_drawn(model, kit, problem, conventions, library)
    svgs, failed = page_svgs(laid, drawn, library)
    findings = (
        *skipped_findings(model, skipped),
        *read_findings(model, skipped),
        *found,
        *unknown_symbol_key_findings(laid, unknown_symbols(model, library)),
        *draw_findings(laid, failed),
    )
    return laid, findings, drawn, svgs


def page_svgs(model: Model, drawn: Mapping[Id[Page], Drawing], library: Library) -> tuple[dict[str, str], dict[Id[DrawingSet], DrawError]]:
    """Page key to the one SVG of each page `drawn` on its sheet, and each set's first error."""
    look = style(library)
    pages = layout_of(model, Page)
    svgs: dict[str, str] = {}
    failed: dict[Id[DrawingSet], DrawError] = {}
    for page, drawing in drawn.items():
        try:
            svgs[render_id(page)] = svg(drawing, library, look, sheet_mm=_sheet_mm(model, page))
        except DrawError as error:
            failed.setdefault(pages[page].drawing_set, error)
    return svgs, failed


def draw_findings(model: Model, failed: Mapping[Id[DrawingSet], DrawError]) -> tuple[Finding, ...]:
    """One `DRAW_PROBLEM` ERROR per drawing set whose page `svg` raised `DrawError` (R183)."""
    sets = layout_of(model, DrawingSet)
    return tuple(
        finding(
            "DRAW_PROBLEM",
            (set_id,),
            f"drawing set {sets[set_id].number} could not be drawn, so it has no page: {error}",
        )
        for set_id, error in failed.items()
    )
