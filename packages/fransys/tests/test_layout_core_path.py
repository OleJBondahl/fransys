"""The private core path of the layout step (SWITCHES SW2): its records, its errors."""

from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import cabinet_document
from demo_designs import cabinet_design
from fransys._layout_core import draw_on_core, lay_out_on_core
from fransys_el import ProblemError, lay_out_core

from electrical_symbols import LIBRARY
from fransys_model.kernel import Severity
from fransys_model.layout import sheet_format_of

if TYPE_CHECKING:
    import pytest

    from fransys_model.kernel import Model


def _build() -> fr.BuildResult:
    parts = fransys_parts.load("demo_parts")
    document = cabinet_document(fransys_author.Design(parts).location("C1", "Demo cabinet"))
    return fr.build(parts, cabinet_design(parts).draft(), document)


def test_a_build_draws_its_pages() -> None:
    drawings = _build().drawings
    assert drawings
    assert all(d.symbols and d.wires for d in drawings.values())


def test_a_problem_error_is_one_error_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: object) -> None:
        subject = "function K1.coil"
        raise ProblemError(subject, "pick a symbol")

    monkeypatch.setattr("fransys._layout_core.symbol_kit", refuse)
    model = _build().model
    laid, findings, _, _ = lay_out_on_core(model, LIBRARY)
    assert laid is model
    assert [(f.code, f.severity) for f in findings] == [("PLACEMENT_PROBLEM", Severity.ERROR)]
    assert "function K1.coil: pick a symbol" in findings[0].message


def test_a_problem_error_keeps_its_detail_and_the_known_limit_fix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*_: object) -> None:
        subject = "function K1.coil"
        raise ProblemError(subject, "pick a symbol")

    monkeypatch.setattr("fransys._layout_core.symbol_kit", refuse)
    (finding,) = lay_out_on_core(_build().model, LIBRARY)[1]
    assert "pick a symbol" in finding.message
    assert finding.fix.startswith("No call clears this:")


def test_the_core_path_solves_the_top_level(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []
    real = lay_out_core.write_layout

    def spy(model: Model, unit: Any, *rest: Any, **named: Any) -> Any:
        seen.append(unit)
        return real(model, unit, *rest, **named)

    monkeypatch.setattr("fransys_el.lay_out_core.write_layout", spy)
    lay_out_on_core(_build().model, LIBRARY)
    assert seen == [None]


def test_a_core_page_svg_is_the_sheet_with_its_drawing_at_the_content_box() -> None:
    """render-0027: the pdf places the SVG at the sheet's (0, 0), where the frame also starts."""
    built = _build()
    model = built.model
    sheet = sheet_format_of(model, None)
    page = next(iter(draw_on_core(model, built.drawings, LIBRARY).values()))
    assert f'viewBox="0 0 {sheet.width_mm} {sheet.height_mm}"' in page
    assert f'<g transform="translate({sheet.content_x_mm} {sheet.content_y_mm})">' in page
