"""The SHEET_INDEX page: every Page cell equals the PDF page its sheet is on (SI3, SI4)."""

import fransys_render
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
import typst
from _build import document, drawing_set, layout_page, location, model, unit
from fransys_pdf import font_dir, source

from fransys_model.derive import document_sheets_of, sheet_index_rows
from fransys_model.kernel import render_id
from fransys_model.vocab import DocumentPreset, PageKind

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    '<rect width="10" height="10"/></svg>'
)
_NOTES = "\n\n".join(f"Paragraph {i}. " + "A long note sentence. " * 60 for i in range(100))


def _fixture(notes: str | None):
    c1 = location("C1", "First cabinet")
    u = unit("u1", name="pump-cabinet")
    ds1 = drawing_set("ds1", location=c1, unit=u, number=1)
    pages = tuple(layout_page(f"a{i}", drawing_set=ds1, number=i) for i in range(1, 4))
    doc = document(
        "d1",
        preset=DocumentPreset.CABINET_SCHEMATIC,
        subject=u,
        cover="# Cover",
        notes=notes,
        remove=(PageKind.PLC_LIST, PageKind.TERMINAL_LIST, PageKind.BOM),
    )
    return model(c1, u, ds1, *pages, doc), doc, pages


def _compile(m, doc, pages) -> pdfium.PdfDocument:
    svgs = {render_id(page.id): _SVG for page in pages}
    compiler = typst.Compiler(font_paths=[font_dir()], ignore_system_fonts=True)
    compiled = compiler.compile(
        input=source(m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m))).encode("utf-8")
    )
    assert isinstance(compiled, bytes)
    return pdfium.PdfDocument(compiled)


def _destination_page(pdf: pdfium.PdfDocument, name: str) -> int:
    dest = pdfium_raw.FPDF_GetNamedDestByName(pdf.raw, name.encode("utf-8"))
    return pdfium_raw.FPDFDest_GetDestPageIndex(pdf.raw, dest) + 1


def _page_cells(pdf: pdfium.PdfDocument) -> list[int]:
    """The Page cell of each row, read from the index page's text after its `Sheet Title Page`."""
    for index in range(len(pdf)):
        text = pdf[index].get_textpage().get_text_bounded()
        if "Sheet Title Page\r\n" in text:
            rows = text.rsplit("Sheet Title Page\r\n", 1)[1].splitlines()
            return [int(row.split()[-1]) for row in rows]
    message = "no index page"
    raise AssertionError(message)


def test_every_page_cell_is_the_page_its_sheet_is_on_when_notes_overflow():
    m, doc, pages = _fixture(_NOTES)
    pdf = _compile(m, doc, pages)
    rows = sheet_index_rows(m, doc.id, (PageKind.SCHEMATIC,))
    expected = [_destination_page(pdf, row.destination) for row in rows]
    assert len(pdf) > 10  # the notes overflow pushes every later page
    assert _page_cells(pdf) == expected
    assert expected[0] > 10
    for page_number, cell in zip(expected, _page_cells(pdf), strict=True):
        frame = pdf[page_number - 1].get_textpage().get_text_bounded()
        assert f"{cell} of {len(pdf)}" in frame  # the frame's "Page m of M" at the sheet


def test_the_same_model_gives_the_same_bytes_twice():
    m, doc, pages = _fixture("Short notes.")
    svgs = {render_id(page.id): _SVG for page in pages}
    assert source(m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m))) == source(
        m, doc.id, svgs, fransys_render.sheets(document_sheets_of(m))
    )


def _index_page(pdf: pdfium.PdfDocument) -> int:
    for index in range(len(pdf)):
        if "Sheet Title Page\r\n" in pdf[index].get_textpage().get_text_bounded():
            return index
    message = "no index page"
    raise AssertionError(message)


def test_every_cell_of_a_row_links_to_its_sheets_page():
    m, doc, pages = _fixture(_NOTES)
    pdf = _compile(m, doc, pages)
    rows = sheet_index_rows(m, doc.id, (PageKind.SCHEMATIC,))
    page = pdf[_index_page(pdf)]
    targets = []
    for n in range(pdfium_raw.FPDFPage_GetAnnotCount(page.raw)):
        annot = pdfium_raw.FPDFPage_GetAnnot(page.raw, n)
        if pdfium_raw.FPDFAnnot_GetSubtype(annot) == pdfium_raw.FPDF_ANNOT_LINK:
            dest = pdfium_raw.FPDFLink_GetDest(pdf.raw, pdfium_raw.FPDFAnnot_GetLink(annot))
            targets.append(pdfium_raw.FPDFDest_GetDestPageIndex(pdf.raw, dest) + 1)
        pdfium_raw.FPDFPage_CloseAnnot(annot)
    expected = [_destination_page(pdf, row.destination) for row in rows]
    assert sorted(targets) == sorted(expected * 3)
