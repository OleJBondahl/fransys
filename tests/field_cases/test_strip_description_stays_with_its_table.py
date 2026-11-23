"""Field case: a long terminal strip, then a second strip with a multi-line description and a short table, near the foot of the left column.
The bug: the description paragraph sat between heading and table, so it could end the left column while its table began the right one.
Fixed by pdf-0026 (L7), a table's heading, description, header row and first data row never split across a column foot."""

from typing import Any
lazy from pathlib import Path

import fransys as fr
import pypdfium2
import pytest
from _field_designs import fc_design, written_pdf
from _model_build_cover import cabinet_document

_DESCRIPTION = "ZZDESC " + "long words " * 12


def _pdf(root: Path, filler: int) -> Path:
    """The terminal list of a `filler`-terminal strip and a described three-terminal strip."""
    d = fc_design("Cabinet", number="CAB-1", customer="Demo Co", author="d", date="2026-10-12")
    cabinet = d.location("C1", "Cabinet")
    d.terminal_strip("X1", "DEMO-TB-2.5", filler, place="C1")
    d.terminal_strip("X2", "DEMO-TB-2.5", 3, place="C1", description=_DESCRIPTION)
    document = cabinet_document(cabinet)
    return written_pdf(fr.build(d, document), root)


def _place(pdf: Path, key: str) -> tuple[int, Any]:
    """`(page, in the right column)` of the first `key` on a terminal list page."""
    document = pypdfium2.PdfDocument(pdf)
    try:
        for number, page in enumerate(document):
            text = page.get_textpage()
            found = text.get_text_range().find(key)
            if "Terminal list" in text.get_text_range() and found >= 0:
                return number, text.get_charbox(found)[0] > page.get_size()[0] / 2
        raise AssertionError(key)
    finally:
        document.close()


@pytest.mark.parametrize("filler", [36, 37, 38])
def test_the_description_stands_in_its_tables_column(tmp_path: Path, filler: int) -> None:
    """The description and the first data row share a page and a column at the left foot."""
    pdf = _pdf(tmp_path, filler)
    assert _place(pdf, "ZZDESC") == _place(pdf, "-X2:1 1")
