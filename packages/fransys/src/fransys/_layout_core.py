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
    unread_hint_findings,
)
from fransys_render import DrawError, svg

from fransys_model.kernel import Severity, render_id
from fransys_model.layout import DrawingSet, Page, layout_of, sheet_format_of
lazy from fransys_model.kernel import Finding

from .settings import settings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.drawing import Drawing
    from fransys_model.derive.page_nav import ReferenceLink
    from fransys_model.kernel import Id, Model


def draw_on_core(
    model: Model, drawings: Mapping[Id[Page], Drawing], library: Library
) -> dict[str, str]:
    """Page key to the SVG of each of the build's page `drawings` of `model` (SW5, F7)."""
    look = style(library)
    return {
        render_id(page): svg(drawing, library, look, sheet_mm=_sheet_mm(model, page))
        for page, drawing in drawings.items()
    }


def _sheet_mm(model: Model, page: Id[Page]) -> tuple[int, int, int, int]:
    """The paper of `page`: width, height and the content box corner, in mm (render-0027)."""
    sheet = sheet_format_of(model, layout_of(model, Page)[page].sheet_format)
    return sheet.width_mm, sheet.height_mm, sheet.content_x_mm, sheet.content_y_mm


NO_DRAWINGS: Mapping[Id[Page], Drawing] = cast("Mapping[Id[Page], Drawing]", {})
NO_LINKS: Mapping[Id[Page], tuple[ReferenceLink, ...]] = cast(
    "Mapping[Id[Page], tuple[ReferenceLink, ...]]", {}
)

type Laid = tuple[
    Model,
    tuple[Finding, ...],
    Mapping[Id[Page], Drawing],
    Mapping[Id[Page], tuple[ReferenceLink, ...]],
]


def lay_out_on_core(
    model: Model, library: Library, layout: Mapping[str, object] | None = None
) -> Laid:
    """The laid-out model, the findings, the page `Drawing`s and the reference links (F7).

    Solved once per location (PAGE-02); a `ProblemError` becomes one ERROR, the model unchanged.
    """
    try:
        kit = symbol_kit(model, library)
        conventions = house_conventions(settings().layout if layout is None else layout, library)
        problem, skipped = build(model, kit, conventions, library)
    except ProblemError as error:
        return model, (problem_finding(error, model),), NO_DRAWINGS, NO_LINKS
    laid, found, drawn, links = lay_out_drawn(model, kit, problem, conventions, library)
    findings = (
        *skipped_findings(model, skipped),
        *read_findings(model, skipped),
        *unread_hint_findings(model),
        *found,
        *unknown_symbol_key_findings(laid, unknown_symbols(model, library)),
        *draw_findings(laid, drawn, library),
    )
    return laid, findings, drawn, links


def draw_findings(
    model: Model, drawn: Mapping[Id[Page], Drawing], library: Library
) -> tuple[Finding, ...]:
    """One `DRAW_PROBLEM` ERROR per drawing set whose page `svg` raises `DrawError` on (R183)."""
    look = style(library)
    pages = layout_of(model, Page)
    failed: dict[Id[DrawingSet], DrawError] = {}
    for page, drawing in drawn.items():
        try:
            svg(drawing, library, look)
        except DrawError as error:
            failed.setdefault(pages[page].drawing_set, error)
    sets = layout_of(model, DrawingSet)
    return tuple(
        Finding(
            code="DRAW_PROBLEM",
            severity=Severity.ERROR,
            subjects=(set_id,),
            message=(
                f"drawing set {sets[set_id].number} could not be drawn, so it has no page: {error}"
            ),
            fix="A Fransys defect: send the smallest model that shows it.",
        )
        for set_id, error in failed.items()
    )
