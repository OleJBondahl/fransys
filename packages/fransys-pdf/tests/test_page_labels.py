"""Viewer page labels (NV4): every page's label is its physical page number.

Labels and frame text are read back from the compiled PDF with pypdfium2. The frame's page cell is the physical page alone.
"""

import ctypes

import fransys_render
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
from _build import compile_pdf as _compile
from _build import document, drawing_set, layout_page, location, model, unit

from electrical_symbols import LIBRARY
from fransys_model.derive import SheetKey, document_sheets_of
from fransys_model.vocab import DocumentPreset
from fransys_model.vocab import PageKind as K

_NOTES = "\n\n".join(f"Paragraph {i}. " + "A long note sentence. " * 60 for i in range(12))


def _fixture():
    """Cover, flowing notes, index, then sheets 1, 2, 2.1, 2.2."""
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="pump-cabinet")
    ds1 = drawing_set("ds1", location=c1, unit=u, number=1)
    ds2 = drawing_set("ds2", location=c1, unit=u, number=2)
    pages = (
        layout_page("a1", drawing_set=ds1, number=1),
        layout_page("a2", drawing_set=ds1, number=2),
        layout_page("b1", drawing_set=ds2, number=1),
        layout_page("b2", drawing_set=ds2, number=2),
    )
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=_NOTES,
    )
    return model(c1, u, ds1, ds2, *pages, doc), doc, pages


def _label(pdf: pdfium.PdfDocument, index: int) -> str:
    size = pdfium_raw.FPDF_GetPageLabel(pdf.raw, index, None, 0)
    buffer = (ctypes.c_ushort * (size // 2))()
    pdfium_raw.FPDF_GetPageLabel(pdf.raw, index, buffer, size)
    return bytes(buffer).decode("utf-16-le").rstrip("\0")


def test_every_page_is_labelled_with_its_physical_page_number():
    m, doc, pages = _fixture()
    pdf = pdfium.PdfDocument(_compile(m, doc, pages))
    assert [_label(pdf, index) for index in range(len(pdf))] == [str(index + 1) for index in range(len(pdf))]


def _page_cell_text(m, doc, pdf, index) -> str:
    """The text inside the title block's page cell of page `index`: its box is the sheet symbol's own."""
    key = SheetKey(doc.id, K.NOTES, 0)
    box = fransys_render.sheets(document_sheets_of(m, ()), LIBRARY)[key].counter_box
    assert box is not None
    x, y, width, height = (value * 72 / 25.4 for value in box)
    page_height = pdf[index].get_height()
    text = pdf[index].get_textpage().get_text_bounded(x, page_height - y - height, x + width, page_height - y)
    return str(text).strip()


def test_every_page_cell_reads_its_physical_page_of_the_total():
    m, doc, sheets = _fixture()
    pdf = pdfium.PdfDocument(_compile(m, doc, sheets))
    assert len(pdf) == 8  # the cover, the drawings, then the notes and the index
    assert [_page_cell_text(m, doc, pdf, index) for index in range(len(pdf))] == [f"{index + 1} of {len(pdf)}" for index in range(len(pdf))]


def test_the_same_model_gives_the_same_bytes_twice():
    m, doc, sheets = _fixture()
    assert _compile(m, doc, sheets) == _compile(m, doc, sheets)
