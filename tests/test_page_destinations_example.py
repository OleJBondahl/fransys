"""Each drawing page of a cabinet example is a named destination that lands on that page (A8).

The canary design (several drawing sets) is built and written through the public API; the
destinations are read back from the written PDF with pypdfium2, and the landing page's own text
shows its title-block counter `n / N`, so the label lands on the page it names, not just a page.
"""

from collections import Counter
from typing import Any
lazy from pathlib import Path

import fransys as fr
import pypdfium2
import pytest
from pypdfium2 import raw
from test_reader_order import _design

from fransys_model.derive import page_destination
from fransys_model.layout import DrawingSet, Page, layout_of


def _pages_of(result: fr.BuildResult, location: Any) -> list[Page]:
    """The drawing pages of the sets drawn for `location`, in set then page order."""
    sets = layout_of(result.model, DrawingSet)
    found = [
        p
        for p in layout_of(result.model, Page).values()
        if sets[p.drawing_set].location == location
    ]
    return sorted(found, key=lambda p: (sets[p.drawing_set].number, p.number))


def _cabinet_node(result: fr.BuildResult) -> Any:
    """The location node of the cabinet `C1`: the one drawing set of the example's document."""
    sets = layout_of(result.model, DrawingSet)
    return next(s.location for s in sets.values() if s.key[-1] == "C1")


@pytest.fixture(scope="module")
def written(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, Path]:
    root = tmp_path_factory.mktemp("a8")
    d, cabinet = _design("a-")
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md")
    result = fr.build(d, doc)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    return result, root


def _landing(pdf: pypdfium2.PdfDocument, label: str) -> int | None:
    dest = raw.FPDF_GetNamedDestByName(pdf.raw, label.encode("utf-8"))
    return raw.FPDFDest_GetDestPageIndex(pdf.raw, dest) if dest else None


def test_every_drawing_page_of_the_example_is_a_destination_landing_on_that_page(
    written: tuple[fr.BuildResult, Path],
) -> None:
    result, root = written
    pages = _pages_of(result, _cabinet_node(result))
    assert len(pages) > 1
    (pdf_path,) = (root / "out").glob("*.pdf")
    pdf = pypdfium2.PdfDocument(pdf_path)
    try:
        totals = Counter(page.drawing_set for page in pages)
        for page in pages:
            index = _landing(pdf, page_destination(result.model, page))
            assert index is not None, page_destination(result.model, page)
            text = pdf[index].get_textpage().get_text_range()
            assert f"{page.number} / {totals[page.drawing_set]}" in text
    finally:
        pdf.close()
