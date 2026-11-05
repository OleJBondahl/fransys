"""Each drawing page of a cabinet example is a named destination that lands on that page (A8).

The canary design (several drawing sets) is built and written through the public API; the
destinations are read back from the written PDF with pypdfium2, and the landing page's own text
"""

from collections import Counter
from typing import Any
lazy from pathlib import Path

import fransys as fr
import pypdfium2
import pytest
from pypdfium2 import raw
from test_reader_order import _design_and_rest, _other_documents

from fransys_model.derive import page_destination
from fransys_model.layout import DrawingSet, Page, layout_of


def _pages_of(result: fr.BuildResult, location: Any) -> list[Page]:
    """The drawing pages of the sets drawn for `location`, in set then page order."""
    sets = layout_of(result.model, DrawingSet)
    found = [p for p in layout_of(result.model, Page).values() if sets[p.drawing_set].location == location]
    return sorted(found, key=lambda p: (sets[p.drawing_set].number, p.number))


def _cabinet_node(result: fr.BuildResult) -> Any:
    """The location node of the cabinet `C1`: the one drawing set of the example's document."""
    nodes = result.model.tables["aspect_node"].values()
    return next(n.id for n in nodes if n.key == ("location", "C1"))


def _canary(root: Path) -> tuple[fr.Design, list[fr.Draft]]:
    """The canary with six relay-coil loops more in C1, so the cabinet wraps onto two pages, and a document for each other set."""
    d, cabinet, rest = _design_and_rest("a-")
    for i in range(6):
        a = d.device(f"KA{i}", "DEMO-RLY-2CO-24", place="C1", name=f"xa{i}")
        b = d.device(f"KB{i}", "DEMO-RLY-2CO-24", place="C1", name=f"xb{i}")
        d.series(a.coil["A1"], b.coil["A1"], wire=("BK", 0.75))
        d.series(b.coil["A2"], a.coil["A2"], wire=("BK", 0.75))
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    documents = [fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=root / "c.md"), *_other_documents(rest, root / "c.md")]
    return d, documents


@pytest.fixture(scope="module")
def written(tmp_path_factory: pytest.TempPathFactory) -> tuple[fr.BuildResult, Path]:
    root = tmp_path_factory.mktemp("a8")
    d, documents = _canary(root)
    result = fr.build(d, *documents)
    fr.write(result, out_dir=root / "out", intermediates=root / "inter")
    return result, root


def _landing(pdf: pypdfium2.PdfDocument, label: str) -> int | None:
    dest = raw.FPDF_GetNamedDestByName(pdf.raw, label.encode("utf-8"))
    index: int | None = int(raw.FPDFDest_GetDestPageIndex(pdf.raw, dest)) if dest else None
    return index


def test_every_drawing_page_of_the_example_is_a_destination_landing_on_that_page(
    written: tuple[fr.BuildResult, Path],
) -> None:
    result, root = written
    pages = _pages_of(result, _cabinet_node(result))
    assert len(pages) > 1
    (pdf_path,) = (root / "out").glob("*-C1.pdf")
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
