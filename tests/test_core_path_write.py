"""`fr.write` draws the schematic pages from the core's `Drawing` (SW5)."""

from typing import TYPE_CHECKING

import fransys as fr
from _card_case import card_case_drafts, lamps_drafts
from fransys import pipeline

from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from pathlib import Path


def test_a_core_path_build_writes_a_pdf_and_no_error(tmp_path: Path) -> None:
    result = fr.build(*lamps_drafts())
    written = fr.write(result, tmp_path / "out", intermediates=tmp_path / "mid")
    assert [p for p in written if p.suffix == ".pdf"]
    assert not [f for f in fr.check(result) if f.severity is Severity.ERROR]


def test_the_core_path_page_svg_is_the_drawing_of_the_records() -> None:
    result = fr.build(*lamps_drafts())
    (svg,) = pipeline._result_svgs(result).values()
    assert svg.startswith("<svg")
    # the content-box group, and the two coils (render-0027)
    assert svg.count("<g transform") == 3


def test_a_core_path_card_writes_a_pdf(tmp_path: Path) -> None:
    result = fr.build(*card_case_drafts(16))
    assert [p for p in fr.write(result, tmp_path / "out") if p.suffix == ".pdf"]


def test_the_lamps_build_shows_no_out_of_page() -> None:
    codes = {f.code for f in fr.build(*lamps_drafts()).findings}
    assert "OUT_OF_PAGE" not in codes
